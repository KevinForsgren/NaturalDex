#!/usr/bin/env python3
"""
Discovery lifecycle and inference orchestration.

A discovery starts as ``pending`` when created with an idempotency key. Photos
are attached to slots 1-3. The vision model runs only after all three photos
exist. On an accepted result, the backend — not the model — resolves the species,
atomically creates or increments the user's card, records the observation link,
awards XP, and advances daily-task progress; all inside one transaction. Failed
or rejected submissions preserve a retryable discovery and never create or
increment a card.
"""

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from config.settings import get_settings
from db.models import BaseService
from services import cards, rewards, tasks
from services.home_base import active_home_base
from services.storage import read_photo_bytes
from services.vision import (
    classify_rejection,
    VisionUnavailableError,
    VisionValidationError,
)

ALLOWED_DISCOVERY_CATEGORIES = {"flora", "fauna", "fungi"}

_REJECTION_MESSAGES = {
    "not_nature": (
        "UNSUPPORTED_CATEGORY",
        "This doesn't look like a natural specimen. Try a plant, animal, or fungus.",
    ),
    "unsupported_category": (
        "UNSUPPORTED_CATEGORY",
        "This category isn't supported yet. Try a plant, animal, or fungus.",
    ),
    "different_subjects": (
        "SUBJECTS_DO_NOT_MATCH",
        "These photos don't seem to show the same subject. Try three views of one plant or organism.",
    ),
    "image_quality_poor": (
        "IMAGE_QUALITY_INSUFFICIENT",
        "This subject is too blurry to identify. Move closer and try again.",
    ),
    "identification_uncertain": (
        "IDENTIFICATION_UNCERTAIN",
        "We couldn't confidently identify this. Try better lighting and a clearer detail photo.",
    ),
    "suspicious_evidence": (
        "SUSPICIOUS_IMAGE_EVIDENCE",
        "We couldn't verify these photos. Please capture three fresh views.",
    ),
}


class DiscoveryError(Exception):
    """A user-facing discovery failure carrying a stable error code."""

    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _utcnow():
    return datetime.now(timezone.utc)


def _owned_discovery(service, user_id: int, discovery_id: int) -> dict:
    row = service.fetchone(
        "SELECT * FROM discoveries WHERE id = :id AND user_id = :uid",
        {"id": discovery_id, "uid": user_id},
    )
    if row is None:
        raise DiscoveryError("NOT_FOUND", "Discovery not found.", 404)
    return dict(row._asdict())


def _photo_count(service, discovery_id: int) -> int:
    return service.scalar(
        "SELECT COUNT(*) FROM discovery_photos WHERE discovery_id = :did",
        {"did": discovery_id},
    )


def _photos(service, discovery_id: int) -> list:
    rows = service.fetchall(
        "SELECT photo_order, storage_key, content_type, byte_size "
        "FROM discovery_photos WHERE discovery_id = :did ORDER BY photo_order",
        {"did": discovery_id},
    )
    return [dict(r._asdict()) for r in rows]


def create_discovery(session, user_id: int, payload: dict) -> dict:
    """Create a pending discovery. Reuses an existing one for a retried key."""
    service = BaseService(session)
    now = _utcnow()
    idempotency_key = (payload.get("idempotency_key") or "").strip() or None

    if idempotency_key:
        existing = service.fetchone(
            "SELECT * FROM discoveries WHERE user_id = :uid AND idempotency_key = :k",
            {"uid": user_id, "k": idempotency_key},
        )
        if existing:
            return dict(existing._asdict())

    params = {
        "uid": user_id,
        "status": "pending",
        "captured_at": payload.get("captured_at"),
        "lat": payload.get("latitude"),
        "lng": payload.get("longitude"),
        "acc": payload.get("location_accuracy_m"),
        "display": (payload.get("display_location") or None),
        "category_hint": (payload.get("category_hint") or None),
        "idempotency_key": idempotency_key,
        "now": now,
    }
    service.execute(
        "INSERT INTO discoveries "
        "(user_id, status, captured_at, latitude, longitude, location_accuracy_m, "
        " display_location, category_hint, idempotency_key, created_at, updated_at) "
        "VALUES (:uid, :status, :captured_at, :lat, :lng, :acc, :display, "
        ":category_hint, :idempotency_key, :now, :now)",
        params,
    )
    service.commit()
    did = service.scalar("SELECT last_insert_rowid()")
    return dict(service.fetchone("SELECT * FROM discoveries WHERE id = :id", {"id": did})._asdict())


def attach_photo(session, user_id: int, discovery_id: int, order: int, storage_key: str, content_type: str, byte_size: int) -> dict:
    """Upsert a photo onto slot 1-3, replacing any prior photo on that slot."""
    service = BaseService(session)
    _owned_discovery(service, user_id, discovery_id)
    if not (1 <= order <= 3):
        raise DiscoveryError("INVALID_PHOTO_ORDER", "Photo order must be 1, 2 or 3.", 422)
    now = _utcnow()
    # Delete-and-insert is race-prone; use an upsert so a retake replaces the slot.
    exists = service.fetchone(
        "SELECT id FROM discovery_photos WHERE discovery_id = :did AND photo_order = :o",
        {"did": discovery_id, "o": order},
    )
    if exists:
        service.execute(
            "UPDATE discovery_photos SET storage_key = :key, content_type = :ct, "
            "byte_size = :size, updated_at = :now WHERE id = :id",
            {"key": storage_key, "ct": content_type, "size": byte_size, "now": now, "id": exists["id"]},
        )
    else:
        service.execute(
            "INSERT INTO discovery_photos "
            "(discovery_id, photo_order, storage_key, content_type, byte_size, created_at, updated_at) "
            "VALUES (:did, :o, :key, :ct, :size, :now, :now)",
            {"did": discovery_id, "o": order, "key": storage_key, "ct": content_type, "size": byte_size, "now": now},
        )
    session.commit()
    return {
        "discovery_id": discovery_id,
        "photo_order": order,
        "storage_key": storage_key,
        "content_type": content_type,
        "byte_size": byte_size,
    }


def discovery_dict(service, d: dict) -> dict:
    species = None
    if d.get("species_id"):
        sp = service.fetchone("SELECT * FROM species WHERE id = :id", {"id": d["species_id"]})
        if sp:
            spp = dict(sp._asdict())
            species = {
                "id": spp["id"],
                "common_name": spp["common_name"],
                "scientific_name": spp["scientific_name"],
                "category": spp["category"],
            }
    return {
        "id": d["id"],
        "status": d["status"],
        "category_hint": d["category_hint"],
        "identification_label": d["identification_label"],
        "identification_confidence": d["identification_confidence"],
        "genuineness_status": d["genuineness_status"],
        "rejection_reason_code": d["rejection_reason_code"],
        "summary": d["summary"],
        "interesting_fact": d["interesting_fact"],
        "species": species,
        "created_at": str(d["created_at"]) if d["created_at"] else None,
    }


def get_discovery(session, user_id: int, discovery_id: int) -> dict:
    service = BaseService(session)
    d = _owned_discovery(service, user_id, discovery_id)
    return {
        "id": d["id"],
        "photos_attached": _photo_count(service, d["id"]),
        **discovery_dict(service, d),
    }


def list_discoveries(session, user_id: int, limit: int = 20, cursor: int = None) -> dict:
    service = BaseService(session)
    limit = max(1, min(limit, 100))
    params = {"uid": user_id, "limit": limit + 1}
    where = " WHERE (1=1) "
    if cursor is not None:
        where += " AND id < :cursor "
        params["cursor"] = int(cursor)
    rows = service.fetchall(
        f"SELECT * FROM discoveries WHERE user_id = :uid {where} ORDER BY id DESC LIMIT :limit",
        params,
    )
    items = [discovery_dict(service, dict(r._asdict())) for r in rows]
    has_more = len(items) > limit
    return {
        "discoveries": items[:limit],
        "has_more": has_more,
        "next_cursor": items[-1]["id"] if has_more else None,
    }


def submit_discovery(session, user_id: int, discovery_id: int, provider) -> dict:
    """Run inference on a discovery with exactly three photos and resolve it."""
    service = BaseService(session)
    d = _owned_discovery(service, user_id, discovery_id)

    # An already-processed discovery is returned as-is (no re-run, no re-count).
    if d["status"] == "accepted":
        card = service.fetchone(
            "SELECT * FROM user_collection_cards "
            "WHERE user_id = :uid AND species_id = :sid",
            {"uid": user_id, "sid": d["species_id"]},
        )
        card = dict(card._asdict()) if card else None
        tz = _user_timezone(service, user_id)
        task_progress = tasks.get_or_create_daily_tasks(session, user_id, tz)
        return {
            "status": "accepted",
            "accepted": True,
            "discovery": discovery_dict(service, d),
            "cardPublicId": card["public_id"] if card else None,
            "cardUrl": cards.card_url(card["public_id"]) if card else None,
            "isFirstDiscovery": False,
            "count": card["count"] if card else 0,
            "taskProgress": task_progress,
        }

    photos = _photos(service, d["id"])
    if len(photos) != 3:
        raise DiscoveryError("THREE_PHOTOS_REQUIRED", "All three photos are required before running analysis.", 422)

    home_base = active_home_base(service, user_id)
    if home_base is None:
        raise DiscoveryError("HOME_BASE_NOT_PAIRED", "Pair a home base before running analysis.", 403)

    if d["status"] != "accepted":
        service.execute(
            "UPDATE discoveries SET status = 'processing', updated_at = :now WHERE id = :id",
            {"now": _utcnow(), "id": d["id"]},
        )
        session.commit()

    # Run the vision model only now that all three photos exist.
    try:
        # The mock provider is always ready; only a real home base can be offline.
        if provider.name != "mock" and not provider.is_available():
            raise DiscoveryError(
                "HOME_BASE_OFFLINE", "Your AI home base is offline.", 503
            )
        images = [read_photo_bytes(p["storage_key"]) for p in photos]
        result = provider.analyze(images, context={"category_hint": d.get("category_hint")})
    except DiscoveryError:
        raise
    except VisionUnavailableError as exc:
        service.execute(
            "UPDATE discoveries SET status = 'failed', updated_at = :now WHERE id = :id",
            {"now": _utcnow(), "id": d["id"]},
        )
        session.commit()
        raise DiscoveryError("OLLAMA_UNAVAILABLE", "AI home base unavailable. Please try again later.", 503) from exc
    except VisionValidationError as exc:
        service.execute(
            "UPDATE discoveries SET status = 'failed', updated_at = :now WHERE id = :id",
            {"now": _utcnow(), "id": d["id"]},
        )
        session.commit()
        raise DiscoveryError("VISION_MODEL_UNAVAILABLE", "The identification model returned an unusable result.", 422) from exc
    except FileNotFoundError:
        raise DiscoveryError("IMAGES_LOST", "One or more photos could not be read. Please retake them.", 422)

    accepted, category, reason, genuineness = classify_rejection(result)

    now = _utcnow()
    if accepted:
        species = cards.resolve_or_create_species(
            service, result["commonName"], result["scientificName"], category
        )
        # Atomic card create/increment + idempotent observation link.
        applied = cards.apply_accepted_discovery(session, service, d, species)
        card = applied["card"]

        # Link the representative photo to the card (bytes stay on disk).
        # Photo order 1 is the wide/first view; fall back to any photo present.
        primary = next((p for p in photos if p["photo_order"] == 1), photos[0] if photos else None)
        if primary:
            cards.set_card_photo(service, card["id"], primary["storage_key"], primary["content_type"], now)

        # XP is decided here by backend rules, never from the client/model.
        event = "first_discovery" if applied["is_first"] else "repeat_observation"
        rewards.award_xp(service, user_id, event, discovery_id=d["id"])

        service.execute(
            "UPDATE discoveries SET status = 'accepted', species_id = :sid, "
            "identification_label = :label, identification_confidence = :conf, "
            "genuineness_status = :gen, rejection_reason_code = NULL, "
            "summary = :summary, interesting_fact = :fact, updated_at = :now "
            "WHERE id = :id",
            {
                "sid": species["id"],
                "label": result["commonName"],
                "conf": result["confidence"],
                "gen": "passed_checks",
                "summary": result["summary"],
                "fact": result["interesting_fact"],
                "now": now,
                "id": d["id"],
            },
        )
        # Advance today's daily-task progress from this verified accepted event.
        tasks.record_discovery_progress(session, user_id, category)
        session.commit()

        tz = _user_timezone(service, user_id)
        task_progress = tasks.get_or_create_daily_tasks(session, user_id, tz)

        return {
            "status": "accepted",
            "accepted": True,
            "discovery": discovery_dict(service, _owned_discovery(service, user_id, d["id"])),
            "cardPublicId": card["public_id"],
            "cardUrl": cards.card_url(card["public_id"]),
            "isFirstDiscovery": applied["is_first"],
            "count": card["count"],
            "taskProgress": task_progress,
        }

    # Rejected: preserve a reviewable discovery; no card and no increment.
    error_code, message = _REJECTION_MESSAGES.get(reason, _REJECTION_MESSAGES["identification_uncertain"])
    service.execute(
        "UPDATE discoveries SET status = 'rejected', genuineness_status = :gen, "
        "rejection_reason_code = :reason, identification_label = :label, "
        "identification_confidence = :conf, updated_at = :now WHERE id = :id",
        {
            "gen": genuineness,
            "reason": reason,
            "label": result["commonName"],
            "conf": result["confidence"],
            "now": now,
            "id": d["id"],
        },
    )
    session.commit()
    return {
        "status": "rejected",
        "accepted": False,
        "errorCode": error_code,
        "message": message,
        "discovery": discovery_dict(service, _owned_discovery(service, user_id, d["id"])),
    }


def _user_timezone(service, user_id: int) -> str:
    row = service.fetchone("SELECT timezone FROM users WHERE id = :uid", {"uid": user_id})
    return dict(row._asdict())["timezone"] if row else get_settings().USER_DEFAULT_TIMEZONE