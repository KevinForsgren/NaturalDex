#!/usr/bin/env python3
"""
Journal API.

Returns the authenticated user's activity timeline (newest first). Entries are
created server-side when verified actions occur; the client never writes to the
journal directly.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.auth import get_current_user
from db.models import BaseService
from db.session import get_db
from services import journal as journal_service

router = APIRouter(prefix="/api/journal", tags=["Journal"])


def _user_id(user):
    data = dict(user._asdict()) if hasattr(user, "_asdict") else dict(user)
    return data["id"]


@router.get("")
def get_journal(
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    uid = _user_id(user)
    service = BaseService(db)
    return {"entries": journal_service.list_entries(service, uid, limit=limit)}