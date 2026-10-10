#!/usr/bin/env python3
"""
Performance API endpoints.

The backend computes all objective statistics (completion %, consistency graph,
totals). A performance *report* is a weekly artifact: a user may have at most
one report per calendar week (Monday-Sunday). Requests always target the
previous completed calendar week, so repeated generation requests for the same
week return the existing report instead of duplicating it.
"""

import sys
from datetime import date, timedelta
from typing import Optional

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from api.auth import get_current_user
from db.models import BaseService
from db.session import db
from services import ai
from services.performance import (
    compute_period_stats,
    fallback_summary,
    performance_status,
)

router = APIRouter(dependencies=[Depends(get_current_user)])
service = BaseService(db.get_session())


def _to_dict(row):
    return dict(row._asdict()) if hasattr(row, "_asdict") else dict(row)


def _period(days: int):
    """Return (start, end) for the trailing ``days`` including today."""
    end = date.today()
    return end - timedelta(days=days - 1), end


def _previous_week(today=None):
    """Return (monday, sunday) of the previous completed calendar week."""
    today = today or date.today()
    this_monday = today - timedelta(days=today.weekday())
    prev_monday = this_monday - timedelta(days=7)
    return prev_monday, prev_monday + timedelta(days=6)


def _user_tasks(user_id: int, start: date, end: date) -> list:
    rows = service.fetchall(
        "SELECT date, completed, estimated_duration FROM tasks "
        "WHERE user_id = :uid AND date >= :start AND date <= :end ORDER BY date",
        {"uid": user_id, "start": start, "end": end},
    )
    return [_to_dict(r) for r in rows]


def _report_dict(row) -> dict:
    d = _to_dict(row)
    return {
        "id": d["id"],
        "period_start": str(d["period_start"]),
        "period_end": str(d["period_end"]),
        "performance_percentage": float(d["performance_percentage"]),
        "performance_status": d["performance_status"],
        "content": d["content"],
    }


def _find_week_report(user_id: int, monday: date):
    return service.fetchone(
        "SELECT * FROM reports WHERE user_id = :uid AND period_start = :ps "
        "ORDER BY id DESC LIMIT 1",
        {"uid": user_id, "ps": monday},
    )


@router.get("/")
def get_performance(
    days: int = 7,
    start: Optional[date] = None,
    end: Optional[date] = None,
    user=Depends(get_current_user),
):
    """Return the user's performance stats + consistency graph for a period."""
    user_id = _to_dict(user)["id"]
    if start and end:
        period_start, period_end = start, end
    else:
        period_start, period_end = _period(days)

    stats = compute_period_stats(
        _user_tasks(user_id, period_start, period_end), period_start, period_end
    )

    # Compare against the previous period to derive a trend for the UI.
    width = (period_end - period_start).days + 1
    prev_start = period_start - timedelta(days=width)
    prev_end = period_start - timedelta(days=1)
    prev_stats = compute_period_stats(
        _user_tasks(user_id, prev_start, prev_end), prev_start, prev_end
    )
    status = performance_status(
        stats["completion_percentage"], prev_stats["completion_percentage"]
    )

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "performance_status": status,
        **stats,
    }


@router.get("/report")
def get_report(user=Depends(get_current_user)):
    """Return the existing report for the previous completed week, if any."""
    user_id = _to_dict(user)["id"]
    monday, sunday = _previous_week()
    row = _find_week_report(user_id, monday)
    return {
        "report": _report_dict(row) if row else None,
        "period_start": monday.isoformat(),
        "period_end": sunday.isoformat(),
    }


@router.post("/report")
def generate_report(user=Depends(get_current_user)):
    """Return the previous week's report, generating it if it does not exist.

    A user may have at most one report per calendar week: if one already exists
    it is returned instead of creating a duplicate. Nothing is persisted unless
    report content was successfully produced.
    """
    user_id = _to_dict(user)["id"]
    monday, sunday = _previous_week()

    existing = _find_week_report(user_id, monday)
    if existing:
        return {"report": _report_dict(existing), "created": False}

    stats = compute_period_stats(_user_tasks(user_id, monday, sunday), monday, sunday)

    # status: compare the target week against the week before it.
    before_start, before_end = monday - timedelta(days=7), monday - timedelta(days=1)
    before_stats = compute_period_stats(
        _user_tasks(user_id, before_start, before_end), before_start, before_end
    )
    status = performance_status(
        stats["completion_percentage"], before_stats["completion_percentage"]
    )

    # AI interpretation with a graceful fallback when the model is unavailable.
    try:
        summary = ai.generate_report_summary(stats, status).strip()
    except (ai.AIUnavailableError, ai.AIValidationError):
        summary = fallback_summary(stats)

    if not summary:
        raise HTTPException(status_code=502, detail="Failed to generate report content.")

    service.execute(
        "INSERT INTO reports "
        "(user_id, date, period_start, period_end, performance_percentage, "
        " performance_status, content) "
        "VALUES (:uid, :day, :start, :end, :pct, :status, :content)",
        {
            "uid": user_id,
            "day": date.today(),
            "start": monday,
            "end": sunday,
            "pct": stats["completion_percentage"],
            "status": status,
            "content": summary,
        },
    )
    service.commit()
    report_id = service.scalar(text("SELECT last_insert_rowid()"))
    row = service.fetchone("SELECT * FROM reports WHERE id = :id", {"id": report_id})
    return {"report": _report_dict(row), "stats": stats, "created": True}