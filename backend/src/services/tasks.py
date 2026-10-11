#!/usr/bin/env python3
"""
Daily task assignment and progress.

Three tasks are assigned per user per calendar date (in the user's timezone).
Assignment is a get-or-create: once a set exists for a user/date it is returned
unchanged; a new logical date rolls over to a fresh set while previous sets stay
in the database for history. Progress is advanced only from backend-verified
accepted discoveries, never from a client-supplied completion flag.
"""

import random
import zoneinfo
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from config.settings import get_settings
from db.models import BaseService

SLOTS = 3


def _utcnow():
    return datetime.now(timezone.utc)


def validate_timezone(value: str) -> str:
    """Return a validated IANA timezone key or raise ValueError."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Timezone must be a valid IANA identifier.")
    zoneinfo.ZoneInfo(value)  # raises ZoneInfoNotFoundError if invalid
    return value.strip()


def user_zone(user_timezone: str) -> ZoneInfo:
    settings = get_settings()
    try:
        return ZoneInfo(user_timezone or "")
    except Exception:
        return ZoneInfo(settings.USER_DEFAULT_TIMEZONE)


def local_date(user_timezone: str) -> date:
    """The current calendar date in the user's timezone."""
    return datetime.now(user_zone(user_timezone)).date()


def _serialize_task(row, colmap=None) -> dict:
    d = dict(row._asdict()) if hasattr(row, "_asdict") else dict(row)
    return {
        "id": d["id"],
        "task_set_id": d["task_set_id"],
        "slot_number": d["slot_number"],
        "status": d["status"],
        "progress_value": d["progress_value"],
        "target_value": d["target_value"],
        "xp_value": d["xp_value"],
        "completed_at": str(d["completed_at"]) if d["completed_at"] else None,
        "task": _catalog_row(d),
    }


def _catalog_row(d) -> dict:
    return {
        "slug": d["slug"],
        "title": d["title"],
        "category": d["category"],
        "target_value": d["target_value"],
        "xp_value": d["xp_value"],
        "icon": d["icon"],
    }


def _recent_slugs(service, user_id: int, days: int = 7) -> set:
    # Task slugs from the user's task sets in the trailing window.
    rows = service.fetchall(
        """
        SELECT tc.slug FROM user_daily_tasks udt
        JOIN user_daily_task_sets udts ON udts.id = udt.task_set_id
        JOIN task_catalog tc ON tc.id = udt.task_id
        WHERE udts.user_id = :uid AND udts.task_date >= :since
        """,
        {"uid": user_id, "since": date.today() - timedelta(days=days)},
    )
    return {dict(r._asdict())["slug"] for r in rows} if rows else set()


def _select_tasks(service, user_id: int) -> list:
    """Pick three active pool tasks, avoiding recent repeats when possible."""
    rows = service.fetchall(
        "SELECT id, slug, category FROM task_catalog WHERE active = 1",
    )
    catalog = [dict(r._asdict()) for r in rows]
    recent = _recent_slugs(service, user_id)

    pool = [t for t in catalog if t["slug"] not in recent]
    if len(pool) < SLOTS:
        pool = list(catalog)
    # Category-balance: bucket, then round-robin pick one per category.
    by_cat: dict = {}
    for t in pool:
        by_cat.setdefault(t["category"], []).append(t)
    for bucket in by_cat.values():
        random.shuffle(bucket)
    chosen = []
    categories = list(by_cat.keys())
    random.shuffle(categories)
    while len(chosen) < SLOTS and categories:
        for cat in list(categories):
            bucket = by_cat[cat]
            if bucket:
                chosen.append(bucket.pop(0))
            else:
                categories.remove(cat)
    # Top up from the flat pool if balancing ran dry.
    if len(chosen) < SLOTS:
        for t in pool:
            if t not in chosen:
                chosen.append(t)
            if len(chosen) >= SLOTS:
                break
    return chosen[:SLOTS]


def _set_exists(service, user_id: int, task_date: date):
    row = service.fetchone(
        "SELECT id FROM user_daily_task_sets WHERE user_id = :uid AND task_date = :d",
        {"uid": user_id, "d": task_date},
    )
    return dict(row._asdict()) if row else None


def _task_rows(service, task_set_id: int) -> list:
    rows = service.fetchall(
        """
        SELECT udt.id, udt.task_set_id, udt.slot_number, udt.status,
               udt.progress_value, udt.target_value, udt.xp_value, udt.completed_at,
               tc.slug, tc.title, tc.category, tc.target_value AS cat_target,
               tc.xp_value AS cat_xp, tc.icon
        FROM user_daily_tasks udt
        JOIN task_catalog tc ON tc.id = udt.task_id
        WHERE udt.task_set_id = :sid
        ORDER BY udt.slot_number
        """,
        {"sid": task_set_id},
    )
    return rows


def _set_dict(service, set_id: int, task_date: date) -> dict:
    return {
        "id": set_id,
        "date": task_date.isoformat(),
        "tasks": [_serialize_task(r) for r in _task_rows(service, set_id)],
    }


def get_or_create_daily_tasks(session, user_id: int, user_timezone: str) -> dict:
    """Return today's persistent task set for the user, creating it once."""
    service = BaseService(session)
    day = local_date(user_timezone)

    existing = _set_exists(service, user_id, day)
    if existing:
        return _set_dict(service, existing["id"], day)

    # Get-or-create under a transaction. On a race the unique(user_id, task_date)
    # constraint fails for the loser, who then rolls back and reads the winner.
    now = _utcnow()
    try:
        service.execute(
            "INSERT INTO user_daily_task_sets "
            "(user_id, task_date, created_at, updated_at) VALUES (:uid, :d, :now, :now)",
            {"uid": user_id, "d": day, "now": now},
        )
        set_id = session.execute(text("SELECT last_insert_rowid()")).scalar()
        for idx, task in enumerate(_select_tasks(service, user_id), start=1):
            catalog_row = service.fetchone(
                "SELECT id, title, category, target_value, xp_value, icon "
                "FROM task_catalog WHERE id = :id",
                {"id": task["id"]},
            )
            cr = dict(catalog_row._asdict())
            service.execute(
                "INSERT INTO user_daily_tasks "
                "(task_set_id, task_id, slot_number, status, progress_value, "
                " target_value, xp_value, created_at, updated_at) "
                "VALUES (:set_id, :task_id, :slot, 'assigned', 0, :target, :xp, :now, :now)",
                {
                    "set_id": set_id,
                    "task_id": cr["id"],
                    "slot": idx,
                    "target": cr["target_value"],
                    "xp": cr["xp_value"],
                    "now": now,
                },
            )
        session.commit()
    except IntegrityError:
        session.rollback()
        # Another request won the race; return its assignment.
        existing = _set_exists(BaseService(session), user_id, day)
        if existing:
            return _set_dict(BaseService(session), existing["id"], day)
        raise

    return _set_dict(BaseService(session), set_id, day)


def list_history(session, user_id: int, limit: int = 30, cursor: int = None) -> dict:
    """Return the user's daily task sets, most recent first."""
    service = BaseService(session)
    limit = max(1, min(limit, 100))
    params = {"uid": user_id, "limit": limit + 1}
    where = " WHERE udts.user_id = :uid "
    if cursor is not None:
        where += " AND udts.id < :cursor "
        params["cursor"] = int(cursor)
    sets = service.fetchall(
        f"SELECT id, task_date FROM user_daily_task_sets {where} "
        "ORDER BY udts.task_date DESC, udts.id DESC LIMIT :limit",
        params,
    )
    items = []
    for s in sets:
        d = dict(s._asdict())
        items.append(_set_dict(service, d["id"], d["task_date"]))
    has_more = len(items) > limit
    return {"sets": items[:limit], "has_more": has_more, "next_cursor": items[-1]["id"] if has_more else None}


def record_discovery_progress(session, user_id: int, species_category: str):
    """Advance today's matching in-progress daily tasks from an accepted discovery.

    Only backend-verified accepted discoveries advance progress. A task completes
    when its progress reaches its target.
    """
    service = BaseService(session)
    # Determine the user's local date via stored timezone.
    user_row = service.fetchone("SELECT timezone FROM users WHERE id = :uid", {"uid": user_id})
    tz = dict(user_row._asdict())["timezone"] if user_row else None
    day = local_date(tz)
    set_row = _set_exists(service, user_id, day)
    if not set_row:
        return
    set_id = set_row["id"]
    now = _utcnow()
    rows = service.fetchall(
        """
        SELECT udt.id, udt.task_id, udt.target_value, udt.status, udt.progress_value,
               tc.category AS cat
        FROM user_daily_tasks udt JOIN task_catalog tc ON tc.id = udt.task_id
        WHERE udt.task_set_id = :sid AND udt.status != 'completed'
        """,
        {"sid": set_id},
    )
    for r in rows:
        d = dict(r._asdict())
        if d["cat"] not in (species_category, "all"):
            continue
        new_progress = d["progress_value"] + 1
        new_status = "completed" if new_progress >= d["target_value"] else "in_progress"
        service.execute(
            "UPDATE user_daily_tasks SET progress_value = :p, status = :st, "
            "completed_at = :done, updated_at = :now "
            "WHERE id = :id",
            {
                "p": new_progress,
                "st": new_status,
                "done": now if new_status == "completed" else None,
                "now": now,
                "id": d["id"],
            },
        )
    session.commit()