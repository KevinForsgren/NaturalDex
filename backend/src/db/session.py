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
from db.migrations import run_migrations

# Backend directory (backend/src/db -> ../.. = backend). Relative sqlite paths
# are anchored here so the database always lives at <backend>/Database/naturedex.db
# regardless of the current working directory.
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _resolve_db_url(url: str) -> str:
    if url.startswith("sqlite:///./"):
        rel = url[len("sqlite:///./"):]
        return f"sqlite:///{BACKEND_DIR / rel}"
    return url


def _ensure_sqlite_dir(db_url: str) -> None:
    """Create the parent directory of a file-backed SQLite database.

    SQLAlchemy's sqlite driver creates the database *file* but not its parent
    directory, so a missing ``Database/`` folder fails at startup with
    ``unable to open database file``. In-memory databases need no directory.
    """
    if not db_url.startswith("sqlite:///") or ":memory:" in db_url:
        return
    raw = db_url[len("sqlite:///"):]
    if not raw:
        return
    parent = Path(raw).expanduser().parent
    if str(parent) in (".", ""):
        return
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"Cannot create the database directory {parent}: {exc}. "
            "Check the DATABASE_URL path and that the directory is writable."
        ) from exc


class Database:
    """Database connection and management."""
    
    def __init__(self):
        settings = get_settings()
        db_url = _resolve_db_url(settings.DATABASE_URL)
        _ensure_sqlite_dir(db_url)
        self.engine = create_engine(
            db_url,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables if they don't exist (fresh databases get the full schema).
        Base.metadata.create_all(bind=self.engine)

        # Apply versioned migrations for changes create_all cannot make on an
        # existing database (column additions, dropped tables).
        run_migrations(self.engine)
    
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


def get_db():
    """FastAPI dependency yielding a request-scoped session.

    Commits on success, rolls back on error, and always closes the session so
    state is not reused across requests.
    """
    session = db.get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()