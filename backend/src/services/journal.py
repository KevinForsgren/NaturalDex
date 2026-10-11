#!/usr/bin/env python3
"""
User journal / activity timeline.

Entries are created by the backend when a verified activity occurs (e.g. a card
is approved). They are always user-owned and read back in reverse chronological
order. No fabricated historical entries are ever inserted for a new user.
"""

from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc)


def create_entry(
    service,
    user_id: int,
    entry_type: str,
    title: str,
    body=None,
    species_id=None,
    card_id=None,
    location_label=None,
    xp_earned=None,
) -> dict:
    """Insert a journal entry for the authenticated user. Returns the row dict."""
    now = _utcnow()
    service.execute(
        "INSERT INTO journal_entries "
        "(user_id, entry_type, species_id, card_id, title, body, location_label, "
        " xp_earned, created_at, updated_at) "
        "VALUES (:uid, :type, :sid, :cid, :title, :body, :loc, :xp, :now, :now)",
        {
            "uid": user_id,
            "type": entry_type,
            "sid": species_id,
            "cid": card_id,
            "title": title,
            "body": body,
            "loc": location_label,
            "xp": xp_earned,
            "now": now,
        },
    )
    return {"id": service.scalar("SELECT last_insert_rowid()")}


def list_entries(service, user_id: int, limit: int = 50) -> list:
    """Return the user's journal entries, newest first, with species metadata."""
    limit = max(1, min(limit, 100))
    rows = service.fetchall(
        """
        SELECT je.id, je.entry_type, je.title, je.body, je.location_label,
               je.xp_earned, je.created_at,
               s.common_name, s.scientific_name, s.category, s.rarity,
               ucc.public_id AS card_public_id
        FROM journal_entries je
        LEFT JOIN species s ON s.id = je.species_id
        LEFT JOIN user_collection_cards ucc ON ucc.id = je.card_id
        WHERE je.user_id = :uid
        ORDER BY je.created_at DESC, je.id DESC
        LIMIT :limit
        """,
        {"uid": user_id, "limit": limit},
    )
    out = []
    for r in rows:
        d = dict(r._asdict())
        out.append(
            {
                "id": d["id"],
                "entry_type": d["entry_type"],
                "title": d["title"],
                "body": d["body"],
                "location_label": d["location_label"],
                "xp_earned": d["xp_earned"],
                "created_at": str(d["created_at"]) if d["created_at"] else None,
                "card_url": f"/collection/card-{d['card_public_id']}" if d.get("card_public_id") else None,
                "species": (
                    {
                        "common_name": d["common_name"],
                        "scientific_name": d["scientific_name"],
                        "category": d["category"],
                        "rarity": d["rarity"],
                    }
                    if d.get("common_name")
                    else None
                ),
            }
        )
    return out