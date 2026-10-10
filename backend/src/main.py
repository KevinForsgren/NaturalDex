#!/usr/bin/env python3
"""
Main FastAPI application entry point.
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src directory to Python path to enable absolute imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from api.auth import router as auth_router
from api.tasks import router as tasks_router
from api.performance import router as performance_router
from api.chat import router as chat_router
from config.settings import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    print(f"Starting {app.title} v{app.version}")
    print(f"Database URL: {settings.DATABASE_URL}")
    
    yield
    
    # Shutdown
    print("Shutting down application")

app = FastAPI(
    title="StudyLoop API",
    description="Backend for StudyLoop - helping users maintain consistency with work and goals",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(performance_router, prefix="/api/performance", tags=["Performance"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])

@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "StudyLoop API",
        "version": app.version,
        "status": "running",
    }