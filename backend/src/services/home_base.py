#!/usr/bin/env python3
"""
Home-base pairing service.

A pairing challenge is a short-lived, single-use credential. Only its hash is
stored at rest; the plaintext token is returned once (encoded in the QR code so
the paired device / relay can redeem it). Redeeming a challenge activates a home
base for the user who created it. Any user may later revoke their own pairings.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from config.settings import get_settings
from services.vision import get_vision_provider


def _utcnow():
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def challenge_ttl() -> timedelta:
    return timedelta(minutes=get_settings().PAIRING_CHALLENGE_TTL_MINUTES)


def create_pairing_challenge(service, user_id: int) -> dict:
    """Create a QR bearing challenge and return the plaintext token once."""
    token = generate_token()
    now = _utcnow()
    service.execute(
        "INSERT INTO pairing_challenges "
        "(user_id, challenge_token_hash, expires_at, created_at, updated_at) "
        "VALUES (:uid, :hash, :expires, :now, :now)",
        {
            "uid": user_id,
            "hash": _hash_token(token),
            "expires": now + challenge_ttl(),
            "now": now,
        },
    )
    service.commit()
    return {
        "token": token,
        "expires_at": (now + challenge_ttl()).isoformat(),
        "expires_in_seconds": int(challenge_ttl().total_seconds()),
    }


def redeem_pairing(service, token: str, name: str = None) -> dict:
    """Redeem a challenge, activating a home base for the challenge's user.

    The challenge is marked used atomically; a token can only be redeemed once
    and only before it expires.
    """
    token_hash = _hash_token(token)
    now = _utcnow()
    row = service.fetchone(
        "SELECT id, user_id, challenge_token_hash, expires_at, used_at "
        "FROM pairing_challenges WHERE challenge_token_hash = :hash",
        {"hash": token_hash},
    )
    if row is None:
        raise ValueError("This pairing code is not recognized.")
    ch = dict(row._asdict())
    if ch["used_at"] is not None:
        raise ValueError("This pairing code has already been used.")
    if ch["expires_at"] and _parse_dt(ch["expires_at"]) < now:
        raise ValueError("This pairing code has expired. Create a new one.")

    user_id = ch["user_id"]
    # Deactivate any previously paired home bases so only one is active.
    service.execute(
        "UPDATE home_bases SET status = 'offline', updated_at = :now "
        "WHERE user_id = :uid AND status = 'paired'",
        {"now": now, "uid": user_id},
    )
    service.execute(
        "INSERT INTO home_bases "
        "(user_id, name, status, token_hash, paired_at, last_seen_at, created_at, updated_at) "
        "VALUES (:uid, :name, 'paired', :hash, :now, :now, :now, :now)",
        {"uid": user_id, "name": (name or "My Laptop").strip() or "My Laptop", "hash": token_hash, "now": now},
    )
    hb_id = service.scalar("SELECT last_insert_rowid()")
    service.execute(
        "UPDATE pairing_challenges SET used_at = :now, updated_at = :now WHERE id = :id",
        {"now": now, "id": ch["id"]},
    )
    service.commit()
    return _home_base_dict(service.fetchone("SELECT * FROM home_bases WHERE id = :id", {"id": hb_id}))


def active_home_base(service, user_id: int):
    return service.fetchone(
        "SELECT * FROM home_bases WHERE user_id = :uid AND status = 'paired' "
        "ORDER BY id DESC LIMIT 1",
        {"uid": user_id},
    )


def get_status(service, user_id: int) -> dict:
    """Return pairing status plus live model readiness for the active home base."""
    row = active_home_base(service, user_id)
    provider = get_vision_provider()
    model_ready = provider.is_available()
    if row is None:
        return {
            "paired": False,
            "status": "pending_pairing",
            "model_ready": model_ready,
            "home_base": None,
        }
    hb = dict(row._asdict())
    return {
        "paired": hb["status"] == "paired" and model_ready,
        "status": hb["status"],
        "model_ready": model_ready,
        "home_base": _home_base_dict(row),
    }


def revoke_home_base(service, user_id: int, home_base_id: int) -> None:
    """Revoke a home base owned by the user."""
    row = service.fetchone(
        "SELECT * FROM home_bases WHERE id = :id AND user_id = :uid",
        {"id": home_base_id, "uid": user_id},
    )
    if row is None:
        raise ValueError("Home base not found.")
    service.execute(
        "UPDATE home_bases SET status = 'revoked', updated_at = :now WHERE id = :id",
        {"now": _utcnow(), "id": home_base_id},
    )
    service.commit()


def _home_base_dict(row) -> dict:
    d = dict(row._asdict())
    return {
        "id": d["id"],
        "name": d["name"],
        "status": d["status"],
        "paired_at": str(d["paired_at"]) if d["paired_at"] else None,
        "last_seen_at": str(d["last_seen_at"]) if d["last_seen_at"] else None,
    }


def _parse_dt(value):
    from datetime import datetime

    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value