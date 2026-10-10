#!/usr/bin/env python3
"""
Application configuration settings.
"""

import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import SettingsConfigDict, BaseSettings

# Add src directory to Python path for module imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Single shared .env lives at the repository root (one level above backend/).
ROOT_ENV = str(Path(__file__).resolve().parents[3] / ".env")
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", validation_alias="HOST")
    PORT: int = Field(default=8000, validation_alias="PORT")
    DEBUG: bool = Field(default=True, validation_alias="DEBUG")
    
    # Database
    # Relative sqlite:/// paths are resolved against the backend directory by
    # db/session.py, so the file always lands in <backend>/Database/naturedex.db.
    DATABASE_URL: str = Field(default="sqlite:///./Database/naturedex.db", validation_alias="DATABASE_URL")
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-here-change-this-in-production", validation_alias="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", validation_alias="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    # Cookie names/policies for HttpOnly session cookies. Secure=True is only
    # correct behind HTTPS; local dev uses HTTP so it stays False by default.
    AUTH_COOKIE_NAME: str = Field(default="naturaldex_token", validation_alias="AUTH_COOKIE_NAME")
    COOKIE_SECURE: bool = Field(default=False, validation_alias="COOKIE_SECURE")
    
    # CORS
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000", validation_alias="ALLOWED_ORIGINS")

    # NatureDex user profile / timezone
    # IANA timezone used to determine the user's calendar date when no explicit
    # timezone is stored on the account.
    USER_DEFAULT_TIMEZONE: str = Field(default="UTC", validation_alias="USER_DEFAULT_TIMEZONE")

    # NatureDex vision pipeline
    # Provider name: "ollama" (local home base) or "mock" (deterministic,
    # for local dev/tests when Ollama is not running). Never a cloud fallback.
    VISION_PROVIDER: str = Field(default="ollama", validation_alias="VISION_PROVIDER")
    # Local private storage for uploaded discovery photos.
    UPLOAD_DIR: str = Field(default="./Database/uploads", validation_alias="UPLOAD_DIR")
    MAX_PHOTO_BYTES: int = Field(default=10 * 1024 * 1024, validation_alias="MAX_PHOTO_BYTES")

    # AI Integration (local Ollama)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    OLLAMA_MODEL: str = Field(default="llama2", validation_alias="OLLAMA_MODEL")

    # Home-base pairing
    PAIRING_CHALLENGE_TTL_MINUTES: int = Field(default=10, validation_alias="PAIRING_CHALLENGE_TTL_MINUTES")
    
    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    model_config = SettingsConfigDict(env_file=ROOT_ENV, env_file_encoding="utf-8", case_sensitive=True, extra="ignore")
def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()