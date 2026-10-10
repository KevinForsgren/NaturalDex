#!/usr/bin/env python3
"""
Planner enforcement rules.

* A plan (task) can only be created for today or a future date.
* A single day's total planned work cannot exceed the maximum (10 hours).
  There is no minimum — users may add small plans of any size.
"""

from datetime import date
from typing import List

# Backend-enforced daily maximum (in minutes).
MAX_WORKLOAD_MINUTES = 600    # 10 hours per day


def ensure_future_or_today(task_date: date) -> None:
    """Reject dates in the past (plans are only for today or future days)."""
    if task_date < date.today():
        raise ValueError(
            f"Cannot schedule a plan for a past date ({task_date.isoformat()}). "
            "Plans can only be created for today or future days."
        )


def check_within_limits(current_total: int, additional: int = 0) -> int:
    """Return the new daily total after adding ``additional`` minutes.

    Raises ``ValueError`` when the resulting daily workload exceeds the
    guaranteed maximum (10 hours).
    """
    new_total = current_total + additional
    if new_total > MAX_WORKLOAD_MINUTES:
        raise ValueError(
            f"Daily workload would be {new_total} minutes, exceeding the "
            f"maximum of {MAX_WORKLOAD_MINUTES} minutes (10 hours)."
        )
    return new_total


def _parse_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def validate_tasks(data) -> List[dict]:
    """Validate a proposed (AI) list of tasks.

    Accepts either a bare list of task dicts or an object of the shape
    ``{"tasks": [...]}``. Every task must have a name, a valid date that is not
    in the past, and a positive estimated duration, and no single day's total
    planned work may exceed the enforced maximum.

    Returns a list of validated/normalized task dicts (durations as int, dates
    as real ``date`` objects). Raises ``ValueError`` otherwise.
    """
    if isinstance(data, dict):
        tasks = data.get("tasks", [])
    else:
        tasks = data
    if not isinstance(tasks, list):
        raise ValueError("Expected a list of tasks.")

    normalized: List[dict] = []
    day_totals: dict = {}

    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"Task #{idx + 1} must be an object.")
        task_name = task.get("task_name") or task.get("name")
        if not task_name or not str(task_name).strip():
            raise ValueError(f"Task #{idx + 1} is missing a name.")

        raw_date = task.get("date")
        if not raw_date:
            raise ValueError(f"Task '{task_name}' is missing a date.")
        try:
            task_date = _parse_date(raw_date)
        except (TypeError, ValueError):
            raise ValueError(f"Task '{task_name}' has an invalid date '{raw_date}'.")
        ensure_future_or_today(task_date)

        raw_duration = task.get("estimated_duration") or task.get("duration")
        try:
            duration = int(raw_duration)
        except (TypeError, ValueError):
            raise ValueError(f"Task '{task_name}' has an invalid duration.")
        if duration <= 0:
            raise ValueError(
                f"Task '{task_name}' duration must be a positive number of minutes."
            )

        day_totals.setdefault(task_date, 0)
        day_totals[task_date] = check_within_limits(day_totals[task_date], duration)

        normalized.append(
            {
                "task_name": str(task_name).strip(),
                "date": task_date,
                "estimated_duration": duration,
            }
        )

    return normalized