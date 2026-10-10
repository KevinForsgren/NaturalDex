#!/usr/bin/env python3
"""
Database session management.
"""

import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Add src directory to Python path for module imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from db.models import Base

# Backend directory (backend/src/db -> ../.. = backend). Relative sqlite paths
# are anchored here so the database always lives at <backend>/Database/studyloop.db
# regardless of the current working directory.
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _resolve_db_url(url: str) -> str:
    if url.startswith("sqlite:///./"):
        rel = url[len("sqlite:///./"):]
        return f"sqlite:///{BACKEND_DIR / rel}"
    return url


class Database:
    """Database connection and management."""
    
    def __init__(self):
        settings = get_settings()
        db_url = _resolve_db_url(settings.DATABASE_URL)
        self.engine = create_engine(
            db_url,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def get_session_context(self) -> Generator[Session, None, None]:
        """Get a database session with context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()
# Global database instance
db = Database()