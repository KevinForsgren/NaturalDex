#!/usr/bin/env python3
"""
Tasks API endpoints.

A task is the single planner entity. Every task belongs to a user and carries
its own date, duration and completion state. The backend enforces the planner
rules:

* Plans (tasks) can only be created for today or a future date.
* Completion status can only be changed on a task scheduled for today.
* A single day's total planned work cannot exceed the daily maximum.
"""

import sys
import datetime as dt
from datetime import date, datetime, timezone
from typing import List, Optional

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from api.auth import get_current_user
from db.models import BaseService
from db.session import db
from services import ai
from services.workload import (
    check_within_limits,
    ensure_future_or_today,
    validate_tasks,
)

router = APIRouter(dependencies=[Depends(get_current_user)])
service = BaseService(db.get_session())


def _to_dict(row):
    return dict(row._asdict()) if hasattr(row, "_asdict") else dict(row)


def _task_to_dict(row):
    """Serialise a task row, exposing booleans as real JSON booleans."""
    data = _to_dict(row)
    if "completed" in data:
        data["completed"] = bool(data["completed"])
    # Raw text() queries return the date column as a string; normalise it to a
    # real ``date`` so comparisons like ``task["date"] == date.today()`` work.
    raw_date = data.get("date")
    if raw_date and not isinstance(raw_date, date):
        data["date"] = date.fromisoformat(str(raw_date))
    return data


class TaskCreate(BaseModel):
    task_name: str
    # Module-qualified type: pydantic 2.13.x on Python 3.14 mis-resolves a
    # field named ``date`` when annotated with the bare ``date`` class + None
    # default (``Optional[date]`` collapses to ``None``-only).
    date: dt.date
    estimated_duration: Optional[int] = None


class TaskUpdate(BaseModel):
    task_name: Optional[str] = None
    date: Optional[dt.date] = None
    estimated_duration: Optional[int] = None
    completed: Optional[bool] = None


class TaskGenerate(BaseModel):
    goal: str


def _get_owned_task(user_id: int, task_id: int) -> dict:
    row = service.fetchone(
        "SELECT * FROM tasks WHERE id = :id AND user_id = :uid",
        {"id": task_id, "uid": user_id},
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_dict(row)


def _day_total_minutes(
    user_id: int, day: date, exclude_task_id: Optional[int] = None
) -> int:
    rows = service.fetchall(
        "SELECT id, estimated_duration FROM tasks "
        "WHERE user_id = :uid AND date = :day",
        {"uid": user_id, "day": day},
    )
    total = 0
    for r in rows:
        task = _to_dict(r)
        if exclude_task_id is not None and task["id"] == exclude_task_id:
            continue
        total += task["estimated_duration"] or 0
    return total


def _last_insert_id() -> int:
    return service.scalar(text("SELECT last_insert_rowid()"))


@router.get("/")
def get_tasks(user=Depends(get_current_user)):
    """List the authenticated user's tasks."""
    user_id = _to_dict(user)["id"]
    rows = service.fetchall(
        "SELECT * FROM tasks WHERE user_id = :uid ORDER BY date, id",
        {"uid": user_id},
    )
    return {"tasks": [_task_to_dict(r) for r in rows]}


@router.post("/")
def create_task(payload: TaskCreate, user=Depends(get_current_user)):
    """Create a task for today/a future day, enforcing workload limits."""
    user_id = _to_dict(user)["id"]

    try:
        ensure_future_or_today(payload.date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    duration = payload.estimated_duration or 0
    try:
        check_within_limits(_day_total_minutes(user_id, payload.date), duration)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    service.execute(
        "INSERT INTO tasks (user_id, task_name, date, estimated_duration, completed) "
        "VALUES (:user_id, :task_name, :date, :estimated_duration, 0)",
        {
            "user_id": user_id,
            "task_name": payload.task_name,
            "date": payload.date,
            "estimated_duration": payload.estimated_duration,
        },
    )
    service.commit()
    task = _get_owned_task(user_id, _last_insert_id())
    return {"task": task}


@router.post("/generate")
def generate_tasks(payload: TaskGenerate, user=Depends(get_current_user)):
    """Ask the AI to propose tasks for a goal.

    The returned list is validated (today/future dates, per-day limit) but NOT
    stored — the frontend shows it to the user, who confirms by creating the
    tasks.
    """
    try:
        proposal = ai.generate_tasks(payload.goal)
        validated = validate_tasks(proposal)
    except ai.AIUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except (ai.AIValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    proposed = [
        {
            "task_name": t["task_name"],
            "date": t["date"].isoformat(),
            "estimated_duration": t["estimated_duration"],
        }
        for t in validated
    ]
    return {"tasks": proposed}


@router.get("/{task_id}")
def get_task(task_id: int, user=Depends(get_current_user)):
    """Get a single task owned by the user."""
    user_id = _to_dict(user)["id"]
    return {"task": _get_owned_task(user_id, task_id)}


@router.patch("/{task_id}")
def update_task(task_id: int, payload: TaskUpdate, user=Depends(get_current_user)):
    """Update task fields, re-enforcing planner date/completion rules."""
    user_id = _to_dict(user)["id"]
    task = _get_owned_task(user_id, task_id)

    fields = payload.dict(exclude_unset=True)
    if not fields:
        return {"task": task}

    new_date = fields.get("date", task["date"])

    try:
        ensure_future_or_today(new_date)
        # Completion can only change on the task's scheduled day (today).
        if "completed" in fields and new_date != date.today():
            raise ValueError(
                "You can only change completion status for a task scheduled today."
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    new_duration = fields.get("estimated_duration", task["estimated_duration"]) or 0
    try:
        check_within_limits(
            _day_total_minutes(user_id, new_date, exclude_task_id=task_id),
            new_duration,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    set_clause = ", ".join(f"{col} = :{col}" for col in fields)
    params = {**fields, "id": task_id, "uid": user_id}
    service.execute(
        f"UPDATE tasks SET {set_clause} WHERE id = :id AND user_id = :uid",
        params,
    )
    service.commit()
    return {"task": _get_owned_task(user_id, task_id)}


@router.delete("/{task_id}")
def delete_task(task_id: int, user=Depends(get_current_user)):
    """Delete a task owned by the user."""
    user_id = _to_dict(user)["id"]
    _get_owned_task(user_id, task_id)  # raises 404 when not owned
    service.execute(
        "DELETE FROM tasks WHERE id = :id AND user_id = :uid",
        {"id": task_id, "uid": user_id},
    )
    service.commit()
    return {"message": "Task deleted"}


@router.post("/{task_id}/complete")
def complete_task(task_id: int, user=Depends(get_current_user)):
    """Mark a task complete, but only if it is scheduled for today."""
    user_id = _to_dict(user)["id"]
    task = _get_owned_task(user_id, task_id)
    if task["date"] != date.today():
        raise HTTPException(
            status_code=400,
            detail="You can only mark a task complete on the day it is scheduled (today).",
        )
    if not task["completed"]:
        service.execute(
            "UPDATE tasks SET completed = 1, completed_at = :ts "
            "WHERE id = :id AND user_id = :uid",
            {"ts": datetime.now(timezone.utc), "id": task_id, "uid": user_id},
        )
        service.commit()
    return {"task": _get_owned_task(user_id, task_id)}