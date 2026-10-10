#!/usr/bin/env python3
"""
Performance calculation logic.

All objective performance numbers (completion percentage, daily consistency,
totals) are computed by the backend so the AI never invents them.
"""

from datetime import date, timedelta
from typing import List


def consistency_level(percent: float) -> int:
    """Map a completion percentage to the GitHub-style intensity level.

    0% -> 0, 1-25% -> 25, 26-50% -> 50, 51-75% -> 75, 76-100% -> 100.
    """
    if percent <= 0:
        return 0
    if percent <= 25:
        return 25
    if percent <= 50:
        return 50
    if percent <= 75:
        return 75
    return 100


def date_range(start: date, end: date) -> List[date]:
    """Return every date from ``start`` to ``end`` inclusive."""
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def compute_period_stats(
    rows: List[dict],
    start: date,
    end: date,
) -> dict:
    """Compute aggregate + daily performance stats for the given task rows.

    ``rows`` must be the authenticated user's tasks within ``[start, end]``,
    each as a dict with keys: date, completed, estimated_duration.
    """
    assigned = len(rows)
    completed = sum(1 for r in rows if r["completed"])
    incomplete = assigned - completed
    completion = round(completed / assigned * 100, 2) if assigned else 0.0
    total_planned = sum(r["estimated_duration"] or 0 for r in rows)
    total_completed = sum(
        (r["estimated_duration"] or 0) for r in rows if r["completed"]
    )

    by_date: dict = {}
    for r in rows:
        # Raw text() rows expose ``date`` as a string; normalise to a real
        # ``date`` so lookups against ``date_range`` (date objects) match.
        d = r["date"]
        if not isinstance(d, date):
            d = date.fromisoformat(str(d))
        by_date.setdefault(d, []).append(r)

    daily = []
    for day in date_range(start, end):
        day_tasks = by_date.get(day, [])
        a = len(day_tasks)
        c = sum(1 for t in day_tasks if t["completed"])
        pct = round(c / a * 100, 2) if a else 0.0
        daily.append(
            {
                "date": day.isoformat(),
                "assigned": a,
                "completed": c,
                "percent": pct,
                "level": consistency_level(pct),
                "no_activity": a == 0,
            }
        )

    return {
        "total_assigned": assigned,
        "completed": completed,
        "incomplete": incomplete,
        "completion_percentage": completion,
        "total_planned_minutes": total_planned,
        "total_completed_minutes": total_completed,
        "daily": daily,
    }


def performance_status(current: float, previous: float) -> str:
    """Classify whether performance improved, declined, or stayed stable."""
    if current > previous + 0.5:
        return "improved"
    if current < previous - 0.5:
        return "declined"
    return "stable"


def fallback_summary(stats: dict) -> str:
    """Build a short objective summary when the AI is unavailable."""
    if stats["total_assigned"] == 0:
        return (
            "No tasks were planned during this period, so there is nothing to "
            "report yet. Plan a few tasks to start building a consistency track record."
        )
    return (
        f"{stats['completed']} of {stats['total_assigned']} assigned tasks were "
        f"completed ({stats['completion_percentage']}%). "
    ) + (
        "Keep the momentum going."
        if stats["completion_percentage"] >= 50
        else "A little more consistency will build strong progress."
    )