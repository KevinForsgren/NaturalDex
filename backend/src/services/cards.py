#!/usr/bin/env python3
"""
Collection card helpers.

The collection card is a per-user instance of a species; ``count`` is how many
accepted observations the user has made of that species. Cards carry a random,
unguessable ``public_id`` used in the stable React Router URL
``/collection/card-<public_id>``. Ownership is always enforced on read.
"""

import re
import secrets
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError


def _utcnow():
    return datetime.now(timezone.utc)


def normalize_canonical_key(common_name: str) -> str:
    """Build a stable de-duplication key from a common name."""
    key = (common_name or "").strip().lower()
    key = re.sub(r"[^a-z0-9]+", "-", key)
    return key.strip("-")[:80]


def new_public_id() -> str:
    return secrets.token_urlsafe(9)


def resolve_or_create_species(service, common_name, scientific_name, category) -> dict:
    """Return the canonical species row for a validated observation.

    Looks up by canonical_key first (so model suggestions merge into guide and
    prior discoveries); otherwise creates a new reviewable candidate record.
    """
    key = normalize_canonical_key(common_name)
    if not key:
        raise ValueError("A common name is required to resolve a species.")
    row = service.fetchone(
        "SELECT * FROM species WHERE canonical_key = :key",
        {"key": key},
    )
    if row:
        return dict(row._asdict())
    now = _utcnow()
    try:
        service.execute(
            "INSERT INTO species "
            "(canonical_key, common_name, scientific_name, category, created_at, updated_at) "
            "VALUES (:key, :name, :sci, :cat, :now, :now)",
            {
                "key": key,
                "name": (common_name or "").strip()[:200] or key,
                "sci": scientific_name,
                "cat": category,
                "now": now,
            },
        )
        service.commit()
        return dict(service.fetchone("SELECT * FROM species WHERE canonical_key = :key", {"key": key})._asdict())
    except IntegrityError:
        service.rollback()
        return dict(service.fetchone("SELECT * FROM species WHERE canonical_key = :key", {"key": key})._asdict())


def find_card(service, user_id: int, species_id: int):
    return service.fetchone(
        "SELECT * FROM user_collection_cards WHERE user_id = :uid AND species_id = :sid",
        {"uid": user_id, "sid": species_id},
    )


def observation_exists(service, discovery_id: int):
    return service.fetchone(
        "SELECT * FROM collection_card_observations WHERE discovery_id = :did",
        {"did": discovery_id},
    )


def apply_accepted_discovery(session, service, discovery, species_row) -> dict:
    """Atomically create or increment the user's card for an accepted discovery.

    Returns a dict with the card plus ``is_first`` and ``incremented`` flags.
    This is idempotent: if this discovery already produced an observation, the
    card is returned unchanged and no increment happens.
    """
    user_id = discovery["user_id"]
    species_id = species_row["id"]
    now = _utcnow()

    already = observation_exists(service, discovery["id"])
    if already:
        card = dict(
            service.fetchone(
                "SELECT * FROM user_collection_cards WHERE id = :id", {"id": already["card_id"]}
            )._asdict()
        )
        return {"card": card, "is_first": False, "incremented": False}

    card = find_card(service, user_id, species_id)
    is_first = card is None
    incremented = False

    if card is None:
        _insert_card(service, user_id, species_id, discovery["id"], now)
        card = find_card(service, user_id, species_id)
        incremented = True
    else:
        # Atomic increment; safe against concurrent repeat observations.
        service.execute(
            "UPDATE user_collection_cards SET count = count + 1, "
            "last_discovered_at = :now, updated_at = :now WHERE id = :id",
            {"now": now, "id": card["id"]},
        )
        card = dict(
            service.fetchone(
                "SELECT * FROM user_collection_cards WHERE id = :id", {"id": card["id"]}
            )._asdict()
        )
        incremented = True

    # The unique(discovery_id) link dedupes retries: if two requests race, the
    # loser's insert fails and we roll back to return the card unchanged.
    try:
        service.execute(
            "INSERT INTO collection_card_observations "
            "(card_id, discovery_id, created_at, updated_at) VALUES (:cid, :did, :now, :now)",
            {"cid": card["id"], "did": discovery["id"], "now": now},
        )
    except IntegrityError:
        service.rollback()
        card = dict(
            service.fetchone(
                "SELECT * FROM user_collection_cards WHERE id = :id", {"id": card["id"]}
            )._asdict()
        )
        is_first, incremented = False, False

    session.commit()
    return {"card": card, "is_first": is_first, "incremented": incremented}


def _insert_card(service, user_id, species_id, first_discovery_id, now):
    from sqlalchemy.exc import IntegrityError

    try:
        service.execute(
            "INSERT INTO user_collection_cards "
            "(public_id, user_id, species_id, first_discovery_id, count, "
            " first_discovered_at, last_discovered_at, created_at, updated_at) "
            "VALUES (:pub, :uid, :sid, :fid, 1, :now, :now, :now, :now)",
            {
                "pub": new_public_id(),
                "uid": user_id,
                "sid": species_id,
                "fid": first_discovery_id,
                "now": now,
            },
        )
        service.commit()
    except IntegrityError:
        service.rollback()


def get_card_by_public_id(service, public_id: str):
    return service.fetchone(
        "SELECT * FROM user_collection_cards WHERE public_id = :pid",
        {"pid": public_id},
    )


def card_detail(service, card) -> dict:
    d = dict(card._asdict())
    species = dict(
        service.fetchone("SELECT * FROM species WHERE id = :id", {"id": d["species_id"]})._asdict()
    )
    return {
        "public_id": d["public_id"],
        "count": d["count"],
        "first_discovered_at": str(d["first_discovered_at"]) if d["first_discovered_at"] else None,
        "last_discovered_at": str(d["last_discovered_at"]) if d["last_discovered_at"] else None,
        "species": {
            "id": species["id"],
            "canonical_key": species["canonical_key"],
            "common_name": species["common_name"],
            "scientific_name": species["scientific_name"],
            "category": species["category"],
            "rarity": species["rarity"],
            "description": species["description"],
            "card_image_key": species["card_image_key"],
            "hint": species["hint"],
        },
    }


def card_url(public_id: str) -> str:
    return f"/collection/card-{public_id}"