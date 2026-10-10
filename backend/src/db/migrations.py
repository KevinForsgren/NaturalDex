#!/usr/bin/env python3
"""
Minimal, dependency-free schema migration runner.

The project previously relied solely on ``Base.metadata.create_all`` (which
creates missing tables but cannot alter or drop existing ones). This module adds
a small versioned runner: each migration is a callable that receives a SQLAlchemy
connection and mutates the schema inside a transaction. Applied migration ids are
recorded in a ``schema_migrations`` table so migrations run exactly once. All
operations are written to be idempotent (guarded by existence checks) so the
runner is safe against partial application.
"""

from sqlalchemy import text


def _tables(conn):
    rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    return {r[0] for r in rows}


def _columns(conn, table):
    if table not in _tables(conn):
        return set()
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}


def _migration_0001_users_timestamps(conn):
    """Add created_at/updated_at/timezone to users, backfilling existing rows."""
    cols = _columns(conn, "users")
    if "created_at" not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME"))
    if "updated_at" not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN updated_at DATETIME"))
    # Backfill existing rows before any future NOT NULL enforcement.
    conn.execute(
        text(
            "UPDATE users SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP), "
            "updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)"
        )
    )
    if "timezone" not in cols:
        conn.execute(
            text("ALTER TABLE users ADD COLUMN timezone VARCHAR DEFAULT 'UTC'")
        )


def _migration_0002_drop_studyloop_tables(conn):
    """Remove the previous StudyLoop app's tables (planner tasks, reports, chats)."""
    tables = _tables(conn)
    for table in ("tasks", "reports", "chats"):
        if table in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))


def _migration_0003_card_photo(conn):
    """Link each collection card to the representative photo for card display."""
    cols = _columns(conn, "user_collection_cards")
    if "card_photo_key" not in cols:
        conn.execute(text("ALTER TABLE user_collection_cards ADD COLUMN card_photo_key VARCHAR"))
    if "card_photo_content_type" not in cols:
        conn.execute(text("ALTER TABLE user_collection_cards ADD COLUMN card_photo_content_type VARCHAR"))


MIGRATIONS = [
    ("0001_users_timestamps_and_timezone", _migration_0001_users_timestamps),
    ("0002_drop_studyloop_tables", _migration_0002_drop_studyloop_tables),
    ("0003_card_photo", _migration_0003_card_photo),
]


def run_migrations(engine):
    """Apply any pending migrations. Safe to call repeatedly."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "id TEXT PRIMARY KEY, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        applied = {
            row[0]
            for row in conn.execute(text("SELECT id FROM schema_migrations")).fetchall()
        }
        for migration_id, fn in MIGRATIONS:
            if migration_id in applied:
                continue
            fn(conn)
            conn.execute(
                text("INSERT INTO schema_migrations (id) VALUES (:id)"),
                {"id": migration_id},
            )