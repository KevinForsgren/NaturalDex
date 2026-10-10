#!/usr/bin/env python3
"""
Backend-awarded XP ledger.

XP deltas are fixed constants decided here and are never accepted from the
client or copied from the vision model. The ledger uses a unique constraint on
``(discovery_id, event_type)`` so a retried submission cannot award XP twice.
"""

from datetime import datetime, timezone

FIRST_DISCOVERY_XP = 30
REPEAT_OBSERVATION_XP = 15

_EVENT_LABELS = {
    "first_discovery": FIRST_DISCOVERY_XP,
    "repeat_observation": REPEAT_OBSERVATION_XP,
}


def _utcnow():
    return datetime.now(timezone.utc)


def award_xp(service, user_id: int, event_type: str, discovery_id=None, task_id=None) -> bool:
    """Award XP for ``event_type``, returning True if a new event was created.

    Returns False when the same discovery already produced this event (so a
    retried request cannot double-award). The insert runs in a savepoint so a
    duplicate cannot abort the surrounding transaction.
    """
    xp_delta = _EVENT_LABELS.get(event_type, 0)
    if xp_delta <= 0:
        return False
    from sqlalchemy.exc import IntegrityError

    now = _utcnow()
    try:
        with service.db.begin_nested():
            service.execute(
                "INSERT INTO xp_events "
                "(user_id, discovery_id, task_id, event_type, xp_delta, created_at, updated_at) "
                "VALUES (:uid, :discovery_id, :task_id, :event_type, :xp, :now, :now)",
                {
                    "uid": user_id,
                    "discovery_id": discovery_id,
                    "task_id": task_id,
                    "event_type": event_type,
                    "xp": xp_delta,
                    "now": now,
                },
            )
    except IntegrityError:
        return False
    return True


def xp_total(service, user_id: int) -> int:
    row = service.fetchone(
        "SELECT COALESCE(SUM(xp_delta), 0) AS total FROM xp_events WHERE user_id = :uid",
        {"uid": user_id},
    )
    return int(dict(row._asdict())["total"]) if row else 0