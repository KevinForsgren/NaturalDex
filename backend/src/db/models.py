#!/usr/bin/env python3
"""
Database models for StudyLoop.
"""

import sys
from datetime import datetime, date
from typing import Optional, List, Any

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import text

# Add src directory to Python path for module imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

Base = declarative_base()
class User(Base):
    """User model for authentication and account management."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    
    # Relationships
    tasks = relationship("Task", back_populates="user")
    reports = relationship("Report", back_populates="user")
    chats = relationship("Chat", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
class Task(Base):
    """Task/To-do model for a single planned work item."""
    
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_name = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    estimated_duration = Column(Integer, nullable=True)  # in minutes
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    
    def __repr__(self):
        return f"<Task(id={self.id}, user_id={self.user_id}, task_name={self.task_name}, date={self.date}, completed={self.completed})>"
class Report(Base):
    """Report model for storing performance summaries."""
    
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=date.today)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    performance_percentage = Column(Numeric(5, 2), nullable=False)  # Calculated by backend
    performance_status = Column(String, nullable=False)  # e.g., "improved", "declined", "stable"
    content = Column(Text, nullable=False)  # AI-generated summary
    
    # Relationships
    user = relationship("User", back_populates="reports")
    
    def __repr__(self):
        return f"<Report(id={self.id}, user_id={self.user_id}, performance={self.performance_percentage}%, status={self.performance_status})>"
class Chat(Base):
    """Chat model for storing conversation history."""
    
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    date = Column(Date, default=date.today)
    time = Column(String, default="00:00")  # Store time as HH:MM string
    
    # Relationships
    user = relationship("User", back_populates="chats")
    
    def __repr__(self):
        return f"<Chat(id={self.id}, user_id={self.user_id}, date={self.date})>"
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
    
    def execute(self, statement, params: Optional[dict] = None):
        """Execute SQL statement."""
        if params:
            if isinstance(statement, str):
                statement = text(statement)
            return self.db.execute(statement, params)
        return self.db.execute(text(statement))
    
    def scalar(self, statement, params: Optional[dict] = None):
        """Execute statement and return scalar result."""
        if params:
            if isinstance(statement, str):
                statement = text(statement)
            result = self.db.execute(statement, params)
        else:
            result = self.db.execute(statement)
        return result.scalar()
    
    def fetchall(self, statement, params: Optional[dict] = None):
        """Execute statement and return all results."""
        if params:
            if isinstance(statement, str):
                statement = text(statement)
            result = self.db.execute(statement, params)
        else:
            result = self.db.execute(statement)
        return result.fetchall()
    
    def fetchone(self, statement, params: Optional[dict] = None):
        """Execute statement and return single result."""
        if params:
            if isinstance(statement, str):
                statement = text(statement)
            result = self.db.execute(statement, params)
        else:
            result = self.db.execute(statement)
        return result.fetchone()
    
    def bulk_update_mappings(self, mapper, mappings):
        """Bulk update mappings."""
        self.db.bulk_update_mappings(mapper, mappings)