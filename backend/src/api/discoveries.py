#!/usr/bin/env python3
"""
Discovery API: create a pending observation, upload its three photos, run the
local vision model, and read back personal history. Photos are validated and
stored privately; the model runs only after all three photos exist.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth import get_current_user
from config.settings import get_settings
from db.session import get_db
from services import storage
from services.discovery import (
    ALLOWED_DISCOVERY_CATEGORIES,
    DiscoveryError,
    attach_photo,
    create_discovery,
    get_discovery,
    list_discoveries,
    submit_discovery,
)
from services.rate_limit import RateLimitedError, limiter
from services.vision import get_vision_provider

router = APIRouter(prefix="/api/discoveries", tags=["Discoveries"])


def _user_id(user):
    data = dict(user._asdict()) if hasattr(user, "_asdict") else dict(user)
    return data["id"]


class DiscoveryCreate(BaseModel):
    idempotency_key: str | None = None
    captured_at: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy_m: float | None = None
    display_location: str | None = None
    category_hint: str | None = None


def _validate_coords(payload: DiscoveryCreate) -> None:
    for name in ("latitude", "longitude"):
        val = getattr(payload, name)
        if val is not None and not (-180.0 <= float(val) <= 180.0):
            raise HTTPException(status_code=422, detail="Invalid coordinates.")
    acc = payload.location_accuracy_m
    if acc is not None and acc < 0:
        raise HTTPException(status_code=422, detail="Invalid location accuracy.")
    if payload.category_hint and payload.category_hint not in ALLOWED_DISCOVERY_CATEGORIES:
        raise HTTPException(status_code=422, detail="Invalid category hint.")


@router.post("")
def create_new_discovery(
    payload: DiscoveryCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    uid = _user_id(user)
    try:
        limiter.check(f"discovery-create:{uid}", limit=30, window_seconds=60)
    except RateLimitedError as exc:
        raise HTTPException(status_code=429, detail={"code": "RATE_LIMITED", "message": str(exc)})
    _validate_coords(payload)
    d = create_discovery(
        db,
        uid,
        {
            "idempotency_key": payload.idempotency_key,
            "captured_at": payload.captured_at,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "location_accuracy_m": payload.location_accuracy_m,
            "display_location": payload.display_location,
            "category_hint": payload.category_hint,
        },
    )
    from services.discovery import discovery_dict

    service = __make_service(db)
    return {"discovery": {"id": d["id"], "photos_attached": 0, **discovery_dict(service, d)}}


@router.post("/{discovery_id}/photos")
async def upload_photo(
    discovery_id: int,
    file: UploadFile = File(...),
    order: int = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    uid = _user_id(user)
    if order is None:
        raise HTTPException(status_code=422, detail={"code": "INVALID_PHOTO_ORDER", "message": "Provide a photo order (1, 2 or 3)."})

    data = await file.read()
    settings = get_settings()
    if len(data) > settings.MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail={"code": "IMAGE_TOO_LARGE", "message": "Photo exceeds the allowed size."})
    content_type = (file.content_type or "").lower()
    if not storage.content_type_allowed(content_type):
        # Reject by declared content type; do not trust arbitrary bytes.
        raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_MEDIA", "message": "Unsupported image type."})

    key = storage.save_photo_bytes(data, content_type)
    try:
        photo = attach_photo(db, uid, discovery_id, order, key, content_type, len(data))
    except DiscoveryError as exc:
        _remove_stored(key)
        raise _http(exc)
    return {"photo": photo}


def _remove_stored(key: str) -> None:
    try:
        storage.remove_photo(key)
    except OSError:
        pass


@router.post("/{discovery_id}/submit")
def run_discovery(
    discovery_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    uid = _user_id(user)
    try:
        limiter.check(f"discovery-submit:{uid}", limit=10, window_seconds=60)
    except RateLimitedError as exc:
        raise HTTPException(status_code=429, detail={"code": "RATE_LIMITED", "message": str(exc)})
    provider = get_vision_provider()
    try:
        result = submit_discovery(db, uid, discovery_id, provider)
    except DiscoveryError as exc:
        raise _http(exc)
    return result


@router.get("/{discovery_id}")
def get_one(discovery_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = _user_id(user)
    try:
        return get_discovery(db, uid, discovery_id)
    except DiscoveryError as exc:
        raise _http(exc)


@router.get("")
def get_all(
    limit: int = 20,
    cursor: int = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    uid = _user_id(user)
    try:
        return list_discoveries(db, uid, limit=limit, cursor=cursor)
    except DiscoveryError as exc:
        raise _http(exc)


def __make_service(db):
    from db.models import BaseService

    return BaseService(db)


def _http(exc: DiscoveryError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})