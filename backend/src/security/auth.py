#!/usr/bin/env python3
"""
Authentication and security utilities using argon2 for password hashing.
"""

import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

# Import from src directory using absolute imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt

class SecurityUtils:
    """Security utility functions using argon2."""
    
    def __init__(self):
        self.settings = get_settings()
        self.hasher = PasswordHasher()
    
    def hash_password(self, password: str) -> str:
        """Hash a password using argon2."""
        return self.hasher.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its argon2 hash."""
        try:
            self.hasher.verify(hashed_password, plain_password)
            return True
        except VerifyMismatchError:
            return False
        except Exception:
            return False
    
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token.

        The token embeds the supplied claims plus an expiration timestamp and
        is signed with the application's secret key.
        """
        to_encode = data.copy()
        if expires_delta is not None:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode,
            self.settings.SECRET_KEY,
            algorithm=self.settings.ALGORITHM,
        )

    def verify_token(self, token: str) -> Optional[dict]:
        """Decode and verify a JWT access token, returning its payload.

        Returns ``None`` if the token is malformed, expired, or fails
        signature verification.
        """
        try:
            return jwt.decode(
                token,
                self.settings.SECRET_KEY,
                algorithms=[self.settings.ALGORITHM],
            )
        except Exception:
            return None

    def create_session_token(self, user_id: int) -> str:
        """Create a session token (simple token for testing)."""
        token_data = f"user_{user_id}_{int(time.time())}"
        return token_data
    
    def verify_session_token(self, token: str) -> Optional[int]:
        """Verify and decode a session token."""
        try:
            if token.startswith("user_") and "_" in token:
                parts = token.split("_")
                if len(parts) >= 3:
                    user_id = int(parts[1])
                    return user_id
        except (ValueError, IndexError):
            pass
        return None
# Global security utilities instance
security = SecurityUtils()