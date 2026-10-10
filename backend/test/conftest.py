#!/usr/bin/env python3
"""
Pytest configuration for the NaturalDex backend.

Places ``backend/src`` on the import path, isolates tests to a temporary SQLite
database, and forces the deterministic mock vision provider (no network). An
autouse fixture clears tables before every test and the TestClient lifespan
re-seeds the task pool and guide species.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# backend/test/conftest.py -> parents[1] == backend; src lives at backend/src.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_TMP_ROOT = Path(tempfile.mkdtemp(prefix="naturedex-test-"))
TEST_DB_PATH = _TMP_ROOT / "naturedex_test.db"

# Must be set before any `db.session` import so the singleton uses a temp DB and
# never touches a real development database.
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["UPLOAD_DIR"] = str(_TMP_ROOT / "uploads")
os.environ["VISION_PROVIDER"] = "mock"
os.environ["USER_DEFAULT_TIMEZONE"] = "UTC"
os.environ["DEBUG"] = "false"

from db.session import db  # noqa: E402
from sqlalchemy import text  # noqa: E402

# child-first order so foreign keys never block deletion.
_TABLES = [
    "xp_events",
    "collection_card_observations",
    "discovery_photos",
    "discoveries",
    "pairing_challenges",
    "home_bases",
    "user_daily_tasks",
    "user_daily_task_sets",
    "user_collection_cards",
    "species",
    "task_catalog",
    "users",
]


@pytest.fixture(autouse=True)
def clean_tables():
    with db.engine.begin() as conn:
        for table in _TABLES:
            conn.execute(text(f"DELETE FROM {table}"))


@pytest.fixture()
def client(clean_tables):
    # Depends on clean_tables so it runs after wipe and the TestClient lifespan
    # re-seeds the task pool and guide species into the freshly emptied tables.
    from main import app  # wait until env is configured
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


def register_and_login(client, username="scout"):
    """Register + login a user and return the session cookie value."""
    client.post(
        "/api/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    resp = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert resp.status_code == 200, resp.text
    return resp.cookies.get("naturaldex_token")


def pair_home_base(client, token):
    """Pair a home base for the user who owns ``token``."""
    challenge = client.post(
        "/api/home-base/pairing-challenge", cookies=_cookies(token)
    ).json()
    pair = client.post(
        "/api/home-base/pair",
        cookies=_cookies(token),
        json={"token": challenge["token"], "name": "Test Laptop"},
    )
    assert pair.status_code == 200, pair.text
    return pair.json()["home_base"]


def make_discovery(client, category_hint="flora", idempotency_suffix="default", token=None):
    """Create a discovery and attach three valid photos.

    Pass ``token`` to act as a specific user; otherwise the client's current
    session cookie is used. Returns (created_payload, discovery_id).
    """
    cookies = _cookies(token) if token else None
    key = f"k-{idempotency_suffix}-{'x' * 12}"
    response_kwargs = {"json": {"category_hint": category_hint, "idempotency_key": key}}
    if cookies:
        response_kwargs["cookies"] = cookies
    created = client.post("/api/discoveries", **response_kwargs)
    assert created.status_code == 200, created.text
    discovery_id = created.json()["discovery"]["id"]
    for order in (1, 2, 3):
        kw = {
            "files": {"file": (f"p{order}.jpg", b"fakejpegbytes" * 8, "image/jpeg")},
        }
        if cookies:
            kw["cookies"] = cookies
        resp = client.post(
            f"/api/discoveries/{discovery_id}/photos?order={order}", **kw
        )
        assert resp.status_code == 200, resp.text
    return created.json()["discovery"], discovery_id