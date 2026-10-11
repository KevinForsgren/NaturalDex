#!/usr/bin/env python3
"""
Authentication API endpoints.

Session handling uses a request-scoped database session (via the `get_db`
dependency), never a shared module-global session. A single shared SQLite
connection reused across concurrent requests causes "database is locked" errors
and blocked reads, which previously made auth endpoints fail or hang.
"""

import sys
from datetime import datetime, timedelta, timezone

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from db.models import BaseService
from db.session import get_db
from security.auth import security

router = APIRouter()
_settings = get_settings()


# Pydantic models for request validation
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def _to_dict(row):
    return dict(row._asdict()) if hasattr(row, "_asdict") else dict(row)


def _service(session: Session) -> BaseService:
    return BaseService(session)


@router.post("/register")
def register(request: RegisterRequest, session: Session = Depends(get_db)):
    """Register a new user account. Passwords are argon2-hashed before storage."""
    service = _service(session)

    existing = service.fetchone(
        "SELECT id FROM users WHERE username = :username OR email = :email",
        {"username": request.username, "email": request.email},
    )
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    password_hash = security.hash_password(request.password)
    now = datetime.now(timezone.utc)
    service.execute(
        "INSERT INTO users (username, email, password_hash, timezone, created_at, updated_at) "
        "VALUES (:username, :email, :password_hash, 'UTC', :now, :now)",
        {
            "username": request.username,
            "email": request.email,
            "password_hash": password_hash,
            "now": now,
        },
    )
    session.commit()

    user = service.fetchone(
        "SELECT * FROM users WHERE username = :username", {"username": request.username}
    )
    user_dict = _to_dict(user)
    user_dict.pop("password_hash", None)
    return {"message": "User registered successfully", "user": user_dict}


@router.post("/login")
def login(request: LoginRequest, response: Response, session: Session = Depends(get_db)):
    """Login a user, return a token, and set a persistent HttpOnly cookie."""
    service = _service(session)
    user = service.fetchone(
        "SELECT * FROM users WHERE username = :username", {"username": request.username}
    )

    if not user or not security.verify_password(
        request.password, _to_dict(user)["password_hash"]
    ):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(_to_dict(user)["id"])},
        expires_delta=access_token_expires,
    )

    # Persistent HttpOnly session cookie so the browser restores the session
    # across refreshes and reopens without exposing the token to JS.
    cookie_kwargs = {
        "key": _settings.AUTH_COOKIE_NAME,
        "value": access_token,
        "httponly": True,
        "samesite": "lax",
        "secure": _settings.COOKIE_SECURE,
        "max_age": int(access_token_expires.total_seconds()),
        "path": "/",
    }
    if _settings.AUTH_COOKIE_DOMAIN:
        cookie_kwargs["domain"] = _settings.AUTH_COOKIE_DOMAIN
    response.set_cookie(**cookie_kwargs)

    user_dict = _to_dict(user)
    user_dict.pop("password_hash", None)
    return {"access_token": access_token, "token_type": "bearer", "user": user_dict}


def _extract_token(request: Request) -> str:
    """Read the JWT from the session cookie, falling back to the Authorization
    header (used by API clients and tests)."""
    token = request.cookies.get(_settings.AUTH_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    return token or ""


def get_current_user(request: Request, session: Session = Depends(get_db)):
    """Resolve the authenticated user from the session cookie or bearer token.

    Used as a FastAPI dependency on user-specific routes. Raises 401 when the
    token is missing, invalid, expired, or references a non-existent user.
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = security.verify_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = _service(session).fetchone(
        "SELECT * FROM users WHERE id = :id", {"id": user_id}
    )
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/logout")
def logout(response: Response):
    """Clear the session cookie so the user is logged out."""
    cookie_kwargs = {
        "key": _settings.AUTH_COOKIE_NAME,
        "path": "/",
    }
    if _settings.AUTH_COOKIE_DOMAIN:
        cookie_kwargs["domain"] = _settings.AUTH_COOKIE_DOMAIN
    response.delete_cookie(**cookie_kwargs)
    return {"message": "Logged out"}


@router.get("/me")
def me(user=Depends(get_current_user)):
    """Return the authenticated user (used by the frontend to restore a session)."""
    data = _to_dict(user)
    data.pop("password_hash", None)
    return {"user": data}


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    user=Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Change the authenticated user's password after verifying the current one."""
    service = _service(session)
    user_id = _to_dict(user)["id"]
    user_row = service.fetchone("SELECT * FROM users WHERE id = :id", {"id": user_id})
    user_map = _to_dict(user_row)

    if not security.verify_password(request.current_password, user_map["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    new_hash = security.hash_password(request.new_password)
    service.execute(
        "UPDATE users SET password_hash = :hash, updated_at = :now WHERE id = :id",
        {"hash": new_hash, "now": datetime.now(timezone.utc), "id": user_id},
    )
    session.commit()
    return {"message": "Password changed successfully"}