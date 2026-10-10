#!/usr/bin/env python3
"""
Authentication API endpoints.
"""

import sys
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

# Import from src directory using absolute imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from db.session import db
from db.models import User, BaseService
from security.auth import security

router = APIRouter()
auth_service = BaseService(db.get_session())
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
    return dict(row._asdict()) if hasattr(row, '_asdict') else dict(row)

@router.post("/register")
async def register(request: RegisterRequest):
    """Register a new user account."""
    
    # Check if user already exists
    existing_user = auth_service.fetchone(
        "SELECT * FROM users WHERE username = :username OR email = :email",
        {"username": request.username, "email": request.email}
    )
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already registered"
        )
    
    # Hash password and create user
    password_hash = security.hash_password(request.password)
    
    auth_service.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (:username, :email, :password_hash)",
        {
            "username": request.username,
            "email": request.email,
            "password_hash": password_hash
        }
    )
    auth_service.commit()
    
    # Get the created user
    user = auth_service.fetchone(
        "SELECT * FROM users WHERE username = :username",
        {"username": request.username}
    )
    
    # Remove password hash from response
    user_dict = dict(user._asdict()) if hasattr(user, '_asdict') else dict(user)
    user_dict.pop("password_hash", None)
    
    return {"message": "User registered successfully", "user": user_dict}
@router.post("/login")
async def login(request: LoginRequest, response: Response):
    """Login a user, return a token, and set a persistent HttpOnly cookie."""
    user = auth_service.fetchone(
        "SELECT * FROM users WHERE username = :username",
        {"username": request.username},
    )

    if not user or not security.verify_password(
        request.password,
        dict(user._asdict())["password_hash"] if hasattr(user, '_asdict') else user["password_hash"],
    ):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(dict(user._asdict())["id"] if hasattr(user, '_asdict') else user["id"])},
        expires_delta=access_token_expires,
    )

    # Persistent HttpOnly session cookie so the browser restores the session
    # across refreshes and reopens without exposing the token to JS.
    response.set_cookie(
        _settings.AUTH_COOKIE_NAME,
        access_token,
        httponly=True,
        samesite="lax",
        secure=_settings.COOKIE_SECURE,
        max_age=int(access_token_expires.total_seconds()),
        path="/",
    )

    user_dict = dict(user._asdict()) if hasattr(user, '_asdict') else dict(user)
    user_dict.pop("password_hash", None)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_dict,
    }


def _extract_token(request: Request) -> str:
    """Read the JWT from the session cookie, falling back to the Authorization
    header (used by API clients and tests)."""
    token = request.cookies.get(_settings.AUTH_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    return token or ""


def get_current_user(request: Request):
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

    user = auth_service.fetchone(
        "SELECT * FROM users WHERE id = :id", {"id": user_id}
    )
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/logout")
def logout(response: Response):
    """Clear the session cookie so the user is logged out."""
    response.delete_cookie(_settings.AUTH_COOKIE_NAME, path="/")
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
):
    """Change the authenticated user's password after verifying the current one."""
    user_id = _to_dict(user)["id"]
    user_row = auth_service.fetchone(
        "SELECT * FROM users WHERE id = :id", {"id": user_id}
    )
    user_map = _to_dict(user_row)

    if not security.verify_password(request.current_password, user_map["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    new_hash = security.hash_password(request.new_password)
    auth_service.execute(
        "UPDATE users SET password_hash = :hash WHERE id = :id",
        {"hash": new_hash, "id": user_id},
    )
    auth_service.commit()

    return {"message": "Password changed successfully"}