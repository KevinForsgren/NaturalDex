#!/usr/bin/env python3
"""
Chat API endpoints.

Lets the authenticated user have a conversation with the local AI. Each
exchange is persisted in the Chats table. When the AI is unavailable a clear
503 is returned so the frontend can let the user retry.
"""

import sys
from datetime import date, datetime, timezone

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import get_current_user
from db.models import BaseService
from db.session import db
from services import ai

router = APIRouter(dependencies=[Depends(get_current_user)])
service = BaseService(db.get_session())


def _to_dict(row):
    return dict(row._asdict()) if hasattr(row, "_asdict") else dict(row)


class ChatRequest(BaseModel):
    message: str


def _build_system_prompt() -> str:
    today = date.today().isoformat()
    return (
        "You are StudyLoop's planning assistant and motivator. Keep your tone calm, "
        "direct, constructive and encouraging. Never ask for sensitive account data.\n"
        f"Today's date is {today}. Use this exact date whenever you refer to 'today' "
        "or plan task dates.\n\n"
        "PLANNER OUTPUT RULE:\n"
        "When the user asks you to CREATE a plan, schedule, or add tasks, your reply "
        "must END with a machine-readable JSON code block (no other JSON, no prose "
        "inside the block) exactly like:\n"
        '```json\n{"tasks": [{"task_name": "Short task name", "date": "YYYY-MM-DD", '
        '"estimated_duration": 40}]}\n```\n'
        "JSON rules: task_name must be non-empty; date is YYYY-MM-DD and must be "
        "today or a FUTURE date (never a past date); estimated_duration is an integer "
        "number of minutes between 1 and 600; you may include multiple tasks.\n"
        "If the user is NOT asking to create tasks or a plan, reply with plain text "
        "only and do NOT include any JSON block."
    )


@router.get("/history")
def chat_history(user=Depends(get_current_user)):
    """Return the user's recent chat exchanges (newest first)."""
    user_id = _to_dict(user)["id"]
    rows = service.fetchall(
        "SELECT * FROM chats WHERE user_id = :uid ORDER BY id DESC LIMIT 50",
        {"uid": user_id},
    )
    chats = []
    for r in rows:
        d = _to_dict(r)
        chats.append(
            {
                "id": d["id"],
                "message": d["message"],
                "response": d["response"],
                "date": str(d["date"]),
                "time": d["time"],
            }
        )
    return {"chats": chats}


@router.post("/")
def chat(payload: ChatRequest, user=Depends(get_current_user)):
    """Send a message to the AI and store the exchange for the user."""
    user_id = _to_dict(user)["id"]
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        ai_reply = ai.chat(
            [
                {"role": "system", "content": _build_system_prompt()},
                {"role": "user", "content": message},
            ]
        )
    except (ai.AIUnavailableError, ai.AIValidationError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    service.execute(
        "INSERT INTO chats (user_id, message, response, date, time) "
        "VALUES (:uid, :message, :response, :day, :time)",
        {
            "uid": user_id,
            "message": message,
            "response": ai_reply,
            "day": date.today(),
            "time": datetime.now(timezone.utc).strftime("%H:%M"),
        },
    )
    service.commit()

    return {"response": ai_reply, "message": message}