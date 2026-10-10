#!/usr/bin/env python3
"""
Database models for NaturalDex.

Every table carries creation/update timestamps following the project
convention. Models are the schema source for ``Base.metadata.create_all`` on a
fresh database; evolutionary changes to already-created tables (and the removal
of the previous StudyLoop tables) are applied by ``db.migrations``.
"""

import sys
from datetime import datetime, timezone

from pathlib import Path
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    Float,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Add src directory to Python path for module imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

Base = declarative_base()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """User model for authentication and account management."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    # IANA timezone identifier used to determine the user's calendar date for
    # daily-task rollover. Validated by the backend before being stored.
    timezone = Column(String, nullable=False, default="UTC")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class TaskCatalog(Base):
    """Reusable daily-task definition drawn from the seeded task pool."""

    __tablename__ = "task_catalog"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    # Category the task pushes the user to observe: flora | fauna | fungi | all.
    category = Column(String, nullable=False, default="all")
    target_value = Column(Integer, nullable=False, default=1)
    xp_value = Column(Integer, nullable=False, default=30)
    icon = Column(String, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self):
        return f"<TaskCatalog(id={self.id}, slug={self.slug}, category={self.category})>"


class UserDailyTaskSet(Base):
    """The three tasks assigned to a user for a single calendar date."""

    __tablename__ = "user_daily_task_sets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # The calendar date in the user's timezone on which this set is active.
    task_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "task_date", name="uq_user_task_date"),
    )

    def __repr__(self):
        return (
            f"<UserDailyTaskSet(id={self.id}, user_id={self.user_id}, "
            f"task_date={self.task_date})>"
        )


class UserDailyTask(Base):
    """A single task within a user's daily task set."""

    __tablename__ = "user_daily_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_set_id = Column(
        Integer, ForeignKey("user_daily_task_sets.id"), nullable=False, index=True
    )
    task_id = Column(Integer, ForeignKey("task_catalog.id"), nullable=False)
    slot_number = Column(Integer, nullable=False)  # 1, 2, 3
    status = Column(String, nullable=False, default="assigned")  # assigned|in_progress|completed
    progress_value = Column(Integer, nullable=False, default=0)
    target_value = Column(Integer, nullable=False, default=1)
    xp_value = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("task_set_id", "slot_number", name="uq_task_set_slot"),
        UniqueConstraint("task_set_id", "task_id", name="uq_task_set_task"),
    )

    def __repr__(self):
        return (
            f"<UserDailyTask(id={self.id}, set={self.task_set_id}, "
            f"slot={self.slot_number}, status={self.status})>"
        )


class Species(Base):
    """Canonical species catalogue record; the unit of a collection card."""

    __tablename__ = "species"

    id = Column(Integer, primary_key=True, index=True)
    # Normalized, stable key used to de-duplicate model suggestions.
    canonical_key = Column(String, unique=True, index=True, nullable=False)
    common_name = Column(String, nullable=False)
    scientific_name = Column(String, nullable=True)
    category = Column(String, nullable=False)  # flora | fauna | fungi
    rarity = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    card_image_key = Column(String, nullable=True)
    hint = Column(String, nullable=True)  # guide text shown on undiscovered slots
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self):
        return f"<Species(id={self.id}, canonical_key={self.canonical_key})>"


class HomeBase(Base):
    """A paired laptop/Ollama endpoint belonging to a user."""

    __tablename__ = "home_bases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=True)
    # pending_pairing | paired | offline | revoked
    status = Column(String, nullable=False, default="pending_pairing")
    token_hash = Column(String, nullable=True)
    paired_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self):
        return f"<HomeBase(id={self.id}, user_id={self.user_id}, status={self.status})>"


class PairingChallenge(Base):
    """Short-lived, single-use credential for pairing a home base to a user."""

    __tablename__ = "pairing_challenges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    challenge_token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self):
        return f"<PairingChallenge(id={self.id}, user_id={self.user_id})>"


class Discovery(Base):
    """A single observation attempt/event driven by three submitted photos."""

    __tablename__ = "discoveries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    species_id = Column(Integer, ForeignKey("species.id"), nullable=True)
    # pending | processing | accepted | rejected | failed
    status = Column(String, nullable=False, default="pending")
    captured_at = Column(DateTime, nullable=True)  # client metadata (untrusted)
    latitude = Column(Float, nullable=True)  # private
    longitude = Column(Float, nullable=True)  # private
    location_accuracy_m = Column(Float, nullable=True)
    display_location = Column(String, nullable=True)
    category_hint = Column(String, nullable=True)
    identification_label = Column(String, nullable=True)
    identification_confidence = Column(Float, nullable=True)
    # not_checked | passed_checks | flagged | inconclusive
    genuineness_status = Column(String, nullable=False, default="not_checked")
    rejection_reason_code = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    interesting_fact = Column(Text, nullable=True)
    home_base_id = Column(Integer, ForeignKey("home_bases.id"), nullable=True)
    idempotency_key = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_user_idempotency"),
    )

    def __repr__(self):
        return f"<Discovery(id={self.id}, user_id={self.user_id}, status={self.status})>"


class DiscoveryPhoto(Base):
    """One of the three photos belonging to a discovery."""

    __tablename__ = "discovery_photos"

    id = Column(Integer, primary_key=True, index=True)
    discovery_id = Column(Integer, ForeignKey("discoveries.id"), nullable=False, index=True)
    photo_order = Column(Integer, nullable=False)  # 1, 2, 3
    storage_key = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    byte_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("discovery_id", "photo_order", name="uq_discovery_photo_order"),
    )

    def __repr__(self):
        return (
            f"<DiscoveryPhoto(id={self.id}, discovery_id={self.discovery_id}, "
            f"order={self.photo_order})>"
        )


class UserCollectionCard(Base):
    """Per-user collection entry for a species (the unit of a card URL)."""

    __tablename__ = "user_collection_cards"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    species_id = Column(Integer, ForeignKey("species.id"), nullable=False)
    first_discovery_id = Column(Integer, ForeignKey("discoveries.id"), nullable=True)
    count = Column(Integer, nullable=False, default=1)
    first_discovered_at = Column(DateTime, nullable=True)
    last_discovered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "species_id", name="uq_user_species_card"),
    )

    def __repr__(self):
        return f"<UserCollectionCard(id={self.id}, public_id={self.public_id})>"


class CollectionCardObservation(Base):
    """Link every accepted discovery to the user's card (dedupes counts)."""

    __tablename__ = "collection_card_observations"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(
        Integer, ForeignKey("user_collection_cards.id"), nullable=False, index=True
    )
    discovery_id = Column(
        Integer, ForeignKey("discoveries.id"), nullable=False, unique=True
    )
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self):
        return (
            f"<CollectionCardObservation(id={self.id}, card_id={self.card_id}, "
            f"discovery_id={self.discovery_id})>"
        )


class XpEvent(Base):
    """Backend-awarded XP ledger. XP deltas are never client-supplied."""

    __tablename__ = "xp_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    discovery_id = Column(Integer, ForeignKey("discoveries.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("user_daily_tasks.id"), nullable=True)
    event_type = Column(String, nullable=False)
    xp_delta = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # A single discovery can only award a given XP event once.
    __table_args__ = (
        UniqueConstraint("discovery_id", "event_type", name="uq_discovery_xp_event"),
    )

    def __repr__(self):
        return (
            f"<XpEvent(id={self.id}, user_id={self.user_id}, "
            f"event_type={self.event_type}, xp_delta={self.xp_delta})>"
        )


class BaseService:
    """Base service class for common database operations."""

    def __init__(self, db):
        self.db = db

    def commit(self):
        """Commit database transaction."""
        self.db.commit()

    def rollback(self):
        """Rollback database transaction."""
        self.db.rollback()

    def refresh(self, obj):
        """Refresh object from database."""
        self.db.refresh(obj)

    def add(self, obj):
        """Add object to database."""
        self.db.add(obj)

    def add_all(self, objs):
        """Add multiple objects to database."""
        self.db.add_all(objs)

    def delete(self, obj):
        """Delete object from database."""
        self.db.delete(obj)

    def execute(self, statement, params=None):
        """Execute SQL statement."""
        from sqlalchemy import text

        if isinstance(statement, str):
            statement = text(statement)
        return self.db.execute(statement, params)

    def scalar(self, statement, params=None):
        """Execute statement and return the first column of the first row."""
        if isinstance(statement, str):
            from sqlalchemy import text

            statement = text(statement)
        return self.db.execute(statement, params).scalar()

    def fetchall(self, statement, params=None):
        """Execute statement and return all results."""
        if isinstance(statement, str):
            from sqlalchemy import text

            statement = text(statement)
        return self.db.execute(statement, params).fetchall()

    def fetchone(self, statement, params=None):
        """Execute statement and return the first result."""
        if isinstance(statement, str):
            from sqlalchemy import text

            statement = text(statement)
        return self.db.execute(statement, params).fetchone()