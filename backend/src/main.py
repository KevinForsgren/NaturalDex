#!/usr/bin/env python3
"""
Main FastAPI application entry point.
"""

import sys
from contextlib import asynccontextmanager

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request

from api.auth import router as auth_router
from api.daily_tasks import router as daily_tasks_router
from api.discoveries import router as discoveries_router
from api.collection import router as collection_router
from api.home_base import router as home_base_router
from api.journal import router as journal_router
from api.profile import router as profile_router
from config.settings import get_settings
from db.models import BaseService
from db.session import db
from services.discovery import DiscoveryError
from services.seed import seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    print(f"Starting {app.title} v{app.version}")
    print(f"Database URL: {settings.DATABASE_URL}")

    # Idempotent seed: ensures the task pool and guide species exist on startup.
    seeded = seed_all(BaseService(db.get_session()))
    print(f"Seeded task catalog: {seeded['tasks']}, guide species: {seeded['guide_species']}")

    yield

    print("Shutting down application")


app = FastAPI(
    title="NatureDex API",
    description="Backend for NatureDex - a field journal and outdoor collection game",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DiscoveryError)
async def discovery_error_handler(request: Request, exc: DiscoveryError):
    """Return stable machine-readable error codes for discovery failures."""
    return JSONResponse(
        status_code=exc.status,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


# Include API routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(daily_tasks_router, tags=["Daily Tasks"])
app.include_router(discoveries_router, tags=["Discoveries"])
app.include_router(collection_router, tags=["Collection"])
app.include_router(home_base_router, tags=["Home Base"])
app.include_router(journal_router, tags=["Journal"])
app.include_router(profile_router, tags=["Profile"])


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "NatureDex API",
        "version": app.version,
        "status": "running",
    }