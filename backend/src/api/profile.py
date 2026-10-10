#!/usr/bin/env python3
"""
Profile API: statistics and the user's timezone used for daily-task rollover.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth import get_current_user
from db.models import BaseService
from db.session import get_db
from services import tasks as task_service
from services.rewards import xp_total

router = APIRouter(prefix="/api/profile", tags=["Profile"])


def _user_id(user):
    data = dict(user._asdict()) if hasattr(user, "_asdict") else dict(user)
    return data["id"]


class TimezoneUpdate(BaseModel):
    timezone: str


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = _user_id(user)
    service = BaseService(db)

    unique_species = service.scalar(
        "SELECT COUNT(*) FROM user_collection_cards WHERE user_id = :uid", {"uid": uid}
    ) or 0
    observations = service.scalar(
        "SELECT COUNT(*) FROM discoveries WHERE user_id = :uid AND status = 'accepted'",
        {"uid": uid},
    ) or 0
    category_totals = {}
    for row in service.fetchall(
        """
        SELECT s.category, COUNT(*) AS n FROM user_collection_cards ucc
        JOIN species s ON s.id = ucc.species_id
        WHERE ucc.user_id = :uid GROUP BY s.category
        """,
        {"uid": uid},
    ):
        r = dict(row._asdict())
        category_totals[r["category"]] = int(r["n"])

    return {
        "unique_species": int(unique_species),
        "observations": int(observations),
        "category_totals": category_totals,
        "xp_total": xp_total(service, uid),
        "streak_days": _streak(service, uid),
    }


@router.put("/timezone")
def update_timezone(
    payload: TimezoneUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    uid = _user_id(user)
    try:
        tz = task_service.validate_timezone(payload.timezone)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid IANA timezone identifier.")
    service = BaseService(db)
    now = datetime.now(timezone.utc)
    service.execute(
        "UPDATE users SET timezone = :tz, updated_at = :now WHERE id = :uid",
        {"tz": tz, "now": now, "uid": uid},
    )
    db.commit()
    return {"timezone": tz}


def _streak(service, user_id: int) -> int:
    """Consecutive calendar days (UTC baseline) with an accepted discovery."""
    rows = service.fetchall(
        "SELECT created_at FROM discoveries WHERE user_id = :uid AND status = 'accepted' "
        "ORDER BY created_at DESC",
        {"uid": user_id},
    )
    days = set()
    today = datetime.now(timezone.utc).date()
    for r in rows:
        d = dict(r._asdict())
        dt = d["created_at"]
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        if dt is not None:
            days.add(dt.date() if not hasattr(dt, "date") else dt.date())
    if not days:
        return 0
    streak = 0
    cur = today
    while cur in days:
        streak += 1
        cur -= timedelta(days=1)
    return streak