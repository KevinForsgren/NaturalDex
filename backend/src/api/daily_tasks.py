#!/usr/bin/env python3
"""
Daily tasks API.

Returns the user's persisted three-task set for the current calendar date in
their timezone, plus optional history. Assignment and rollover are handled by
the service layer with get-or-create semantics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.auth import get_current_user
from db.session import get_db
from services import tasks as task_service

router = APIRouter(prefix="/api/daily-tasks", tags=["Daily Tasks"])


def _user_id(user, fallback_tz: str = "UTC"):
    data = dict(user._asdict()) if hasattr(user, "_asdict") else dict(user)
    return data["id"], data.get("timezone") or fallback_tz


@router.get("")
def get_daily_tasks(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Get-or-create today's persisted three-task set for the user."""
    uid, tz = _user_id(user)
    return task_service.get_or_create_daily_tasks(db, uid, tz)


@router.get("/history")
def get_task_history(
    limit: int = 30,
    cursor: int = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return past daily task sets, most recent first."""
    uid, _tz = _user_id(user)
    return task_service.list_history(db, uid, limit=limit, cursor=cursor)