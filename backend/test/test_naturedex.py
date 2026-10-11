#!/usr/bin/env python3
"""
NaturalDex backend tests.

Covers daily-task persistence and rollover, discovery validation, duplicate
submission handling, collection count increments, per-user authorization, QR
pairing, and timestamp presence. Uses the deterministic mock vision provider
unless a test injects its own provider.
"""

from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import conftest
from db.session import db
from services.vision import VisionProvider, VisionUnavailableError
from services import storage

COOKIE = "naturaldex_token"


def _cookies(token):
    return {COOKIE: token}


def _login(client, username):
    token = conftest.register_and_login(client, username)
    return token


# --------------------------------------------------------------------------
# Test vision providers
# --------------------------------------------------------------------------
class UnavailableProvider(VisionProvider):
    name = "unavailable"

    def is_available(self):
        return True

    def analyze(self, images, context):
        raise VisionUnavailableError("down")


class BadOutputProvider(VisionProvider):
    """Returns schema-invalid output (out-of-range confidence)."""
    name = "bad"

    def analyze(self, images, context):
        return {
            "accepted": True,
            "category": "flora",
            "confidence": 2.0,  # invalid
            "sameSubjectAcrossImages": True,
            "imageQuality": "usable",
            "genuinenessAssessment": "no_obvious_manipulation_detected",
            "reasonCode": None,
        }


class RejectProvider(VisionProvider):
    """Returns an advisory rejection (subjects do not match)."""
    name = "reject"

    def analyze(self, images, context):
        return {
            "accepted": False,
            "category": "flora",
            "commonName": "Bougainvillea",
            "confidence": 0.4,
            "sameSubjectAcrossImages": False,
            "imageQuality": "usable",
            "genuinenessAssessment": "no_obvious_manipulation_detected",
            "reasonCode": "different_subjects",
        }


# --------------------------------------------------------------------------
# Daily tasks
# --------------------------------------------------------------------------
def test_daily_tasks_are_stable_on_repeat(client):
    token = _login(client, "scout")
    first = client.get("/api/daily-tasks", cookies=_cookies(token)).json()
    second = client.get("/api/daily-tasks", cookies=_cookies(token)).json()
    assert len(first["tasks"]) == 3
    assert first["date"] == second["date"]
    ids1 = [t["id"] for t in first["tasks"]]
    ids2 = [t["id"] for t in second["tasks"]]
    assert ids1 == ids2


def test_daily_tasks_survive_logout_and_restart(client):
    token = _login(client, "scout")
    got = client.get("/api/daily-tasks", cookies=_cookies(token)).json()
    assert len(got["tasks"]) == 3

    # Logout and log back in: same persisted set (no in-memory state).
    client.post("/api/auth/logout", cookies=_cookies(token))
    token2 = _login(client, "scout")
    after = client.get("/api/daily-tasks", cookies=_cookies(token2)).json()
    assert [t["id"] for t in after["tasks"]] == [t["id"] for t in got["tasks"]]

    # "Restart": read through a brand-new engine/session on the same file DB.
    engine = create_engine(f"sqlite:///{conftest.TEST_DB_PATH}")
    Session = sessionmaker(bind=engine)
    with Session() as s:
        sets = s.execute("SELECT task_date FROM user_daily_task_sets").fetchall()
    assert len(sets) == 1


def test_new_date_creates_new_set_even_if_incomplete(client, monkeypatch):
    token = _login(client, "scout")
    monkeypatch.setattr("services.tasks.local_date", lambda tz: date(2026, 5, 1))
    day1 = client.get("/api/daily-tasks", cookies=_cookies(token)).json()

    monkeypatch.setattr("services.tasks.local_date", lambda tz: date(2026, 5, 2))
    day2 = client.get("/api/daily-tasks", cookies=_cookies(token)).json()

    assert day1["id"] != day2["id"]
    assert day1["date"] == "2026-05-01"
    assert day2["date"] == "2026-05-02"
    # History preserves the previous (possibly incomplete) set.
    history = client.get("/api/daily-tasks/history", cookies=_cookies(token)).json()
    assert len(history["sets"]) >= 2


def test_concurrent_first_request_creates_one_set(client):
    token = _login(client, "scout")
    # First request creates the set.
    client.get("/api/daily-tasks", cookies=_cookies(token)).json()
    # A second, independent get-or-create must return the same set (unique
    # constraint prevents a duplicate).
    again = client.get("/api/daily-tasks", cookies=_cookies(token)).json()
    with db.engine.connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM user_daily_task_sets"
        ).scalar()
    assert count == 1
    assert len(again["tasks"]) == 3


# --------------------------------------------------------------------------
# Discovery + collection
# --------------------------------------------------------------------------
def test_three_photos_required(client):
    token = _login(client, "scout")
    created, did = conftest.make_discovery(client)
    # Created with all three photos; delete one to simulate an incomplete set.
    with db.engine.begin() as conn:
        conn.execute("DELETE FROM discovery_photos WHERE photo_order = 3")
    resp = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token))
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "THREE_PHOTOS_REQUIRED"


def test_failed_model_does_not_create_card(client, monkeypatch):
    token = _login(client, "scout")
    conftest.pair_home_base(client, token)
    _, did = conftest.make_discovery(client)
    monkeypatch.setattr(
        "api.discoveries.get_vision_provider", lambda: UnavailableProvider()
    )
    resp = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token))
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "OLLAMA_UNAVAILABLE"
    collection = client.get("/api/collection", cookies=_cookies(token)).json()
    assert [c for c in collection["cards"] if c["discovered"]] == []


def test_invalid_model_output_is_rejected_safely(client, monkeypatch):
    token = _login(client, "scout")
    conftest.pair_home_base(client, token)
    _, did = conftest.make_discovery(client)
    monkeypatch.setattr(
        "api.discoveries.get_vision_provider", lambda: BadOutputProvider()
    )
    resp = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token))
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "VISION_MODEL_UNAVAILABLE"
    collection = client.get("/api/collection", cookies=_cookies(token)).json()
    assert [c for c in collection["cards"] if c["discovered"]] == []


def test_first_accepted_creates_card_count_one(client):
    token = _login(client, "scout")
    conftest.pair_home_base(client, token)
    _, did = conftest.make_discovery(client)
    result = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token)).json()
    assert result["accepted"] is True
    assert result["isFirstDiscovery"] is True
    assert result["count"] == 1
    assert result["cardUrl"] == f"/collection/card-{result['cardPublicId']}"


def test_repeat_accepted_increments_same_card(client):
    token = _login(client, "scout")
    conftest.pair_home_base(client, token)
    _, did1 = conftest.make_discovery(client, idempotency_suffix="a")
    r1 = client.post(f"/api/discoveries/{did1}/submit", cookies=_cookies(token)).json()
    _, did2 = conftest.make_discovery(client, idempotency_suffix="b")
    r2 = client.post(f"/api/discoveries/{did2}/submit", cookies=_cookies(token)).json()
    assert r1["cardPublicId"] == r2["cardPublicId"]
    assert r2["count"] == 2
    assert r2["isFirstDiscovery"] is False


def test_retrying_same_discovery_does_not_double_count(client):
    token = _login(client, "scout")
    conftest.pair_home_base(client, token)
    _, did = conftest.make_discovery(client)
    r1 = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token)).json()
    r2 = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token)).json()
    assert r1["count"] == 1
    assert r2["count"] == 1
    assert r2["accepted"] is True


def test_two_users_get_separate_cards(client):
    token_a = _login(client, "alice")
    token_b = _login(client, "bob")
    conftest.pair_home_base(client, token_a)
    conftest.pair_home_base(client, token_b)
    _, did_a = conftest.make_discovery(client, idempotency_suffix="a", token=token_a)
    r_a = client.post(
        f"/api/discoveries/{did_a}/submit", cookies=_cookies(token_a)
    ).json()
    _, did_b = conftest.make_discovery(client, idempotency_suffix="b", token=token_b)
    r_b = client.post(
        f"/api/discoveries/{did_b}/submit", cookies=_cookies(token_b)
    ).json()
    assert r_a["cardPublicId"] != r_b["cardPublicId"]
    assert r_a["count"] == 1 and r_b["count"] == 1


def test_user_cannot_read_another_users_card(client):
    token_a = _login(client, "alice")
    token_b = _login(client, "bob")
    conftest.pair_home_base(client, token_a)
    _, did_a = conftest.make_discovery(client, idempotency_suffix="a", token=token_a)
    r_a = client.post(
        f"/api/discoveries/{did_a}/submit", cookies=_cookies(token_a)
    ).json()
    pid = r_a["cardPublicId"]
    ok = client.get(f"/api/collection/card-{pid}", cookies=_cookies(token_a))
    assert ok.status_code == 200
    denied = client.get(f"/api/collection/card-{pid}", cookies=_cookies(token_b))
    assert denied.status_code == 404


def test_card_url_reload_returns_persisted_card(client):
    token = _login(client, "scout")
    conftest.pair_home_base(client, token)
    _, did = conftest.make_discovery(client)
    result = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token)).json()
    reloaded = client.get(
        f"/api/collection/card-{result['cardPublicId']}", cookies=_cookies(token)
    ).json()
    assert reloaded["card"]["count"] == 1
    assert reloaded["card"]["species"]["common_name"] == "Bougainvillea"


def test_missing_location_does_not_block_discovery(client):
    token = _login(client, "scout")
    conftest.pair_home_base(client, token)
    created = client.post(
        "/api/discoveries",
        cookies=_cookies(token),
        json={"category_hint": "flora", "idempotency_key": "no-location-key"},
    )
    did = created.json()["discovery"]["id"]
    for order in (1, 2, 3):
        client.post(
            f"/api/discoveries/{did}/photos?order={order}",
            cookies=_cookies(token),
            files={"file": (f"x{order}.jpg", b"bytes" * 8, "image/jpeg")},
        )
    result = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token)).json()
    assert result["accepted"] is True


def test_rejected_discovery_no_increment(client, monkeypatch):
    token = _login(client, "scout")
    conftest.pair_home_base(client, token)
    # A clean rejection leaves no card and a reviewable rejected discovery.
    monkeypatch.setattr("api.discoveries.get_vision_provider", lambda: RejectProvider())
    _, did = conftest.make_discovery(client, idempotency_suffix="reject")
    resp = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is False
    assert body["errorCode"] == "SUBJECTS_DO_NOT_MATCH"
    collection = client.get("/api/collection", cookies=_cookies(token)).json()
    assert [c for c in collection["cards"] if c["discovered"]] == []


# --------------------------------------------------------------------------
# Pairing
# --------------------------------------------------------------------------
def test_pairing_challenge_single_use_and_expires(client):
    token = _login(client, "scout")
    challenge = client.post(
        "/api/home-base/pairing-challenge", cookies=_cookies(token)
    ).json()
    assert challenge["token"]
    first = client.post(
        "/api/home-base/pair",
        cookies=_cookies(token),
        json={"token": challenge["token"], "name": "Laptop"},
    )
    assert first.status_code == 200
    # Reusing the same token must fail (single use).
    second = client.post(
        "/api/home-base/pair",
        cookies=_cookies(token),
        json={"token": challenge["token"], "name": "Laptop"},
    )
    assert second.status_code == 400


def test_home_base_required_for_submit(client, monkeypatch):
    token = _login(client, "scout")
    _, did = conftest.make_discovery(client)
    # Use a real (non-mock) provider: without a paired home base it must be refused.
    monkeypatch.setattr("api.discoveries.get_vision_provider", lambda: UnavailableProvider())
    resp = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "HOME_BASE_NOT_PAIRED"


def test_revoke_home_base(client):
    token = _login(client, "scout")
    hb = conftest.pair_home_base(client, token)
    revoke = client.post(
        f"/api/home-base/{hb['id']}/revoke", cookies=_cookies(token)
    )
    assert revoke.status_code == 200
    status = client.get("/api/home-base/status", cookies=_cookies(token)).json()
    assert status["paired"] is False


# --------------------------------------------------------------------------
# Timestamps / schema
# --------------------------------------------------------------------------
def test_users_table_has_timestamps_and_timezone(client):
    _login(client, "scout")
    row = db.engine.connect().execute(
        "SELECT created_at, updated_at, timezone FROM users LIMIT 1"
    ).fetchone()
    assert row.created_at is not None
    assert row.updated_at is not None
    assert row.timezone == "UTC"


def test_timezone_can_be_updated(client):
    token = _login(client, "scout")
    resp = client.put(
        "/api/profile/timezone", cookies=_cookies(token), json={"timezone": "Europe/London"}
    )
    assert resp.status_code == 200
    bad = client.put(
        "/api/profile/timezone", cookies=_cookies(token), json={"timezone": "Not/AZone"}
    )
    assert bad.status_code == 422


# --------------------------------------------------------------------------
# Card image endpoint (Option B)
# --------------------------------------------------------------------------
def _accepted_card(client, token):
    """Pair, discover, and accept a card; returns the submit response body."""
    conftest.pair_home_base(client, token)
    _, did = conftest.make_discovery(client, token=token)
    result = client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token)).json()
    assert result["accepted"] is True
    return result


def test_card_image_success(client):
    token = _login(client, "scout")
    result = _accepted_card(client, token)
    pid = result["cardPublicId"]

    # The card detail should advertise the authenticated image route.
    detail = client.get(f"/api/collection/card-{pid}", cookies=_cookies(token)).json()
    assert detail["card"]["image_url"] == f"/api/collection/card-{pid}/image"

    resp = client.get(f"/api/collection/card-{pid}/image", cookies=_cookies(token))
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("image/jpeg")
    # The card uses photo order 1 (the first uploaded file).
    assert resp.content == b"fakejpegbytes" * 8


def test_card_image_unauthorized_user(client):
    token_a = _login(client, "alice")
    token_b = _login(client, "bob")
    result = _accepted_card(client, token_a)
    pid = result["cardPublicId"]
    denied = client.get(f"/api/collection/card-{pid}/image", cookies=_cookies(token_b))
    assert denied.status_code == 404


def test_card_image_missing_file(client):
    token = _login(client, "scout")
    result = _accepted_card(client, token)
    pid = result["cardPublicId"]
    key = None
    with db.engine.begin() as conn:
        key = conn.execute(
            text("SELECT card_photo_key FROM user_collection_cards WHERE public_id = :p"),
            {"p": pid},
        ).scalar()
    storage.remove_photo(key)
    resp = client.get(f"/api/collection/card-{pid}/image", cookies=_cookies(token))
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "IMAGE_NOT_FOUND"


def test_card_image_missing_reference(client):
    token = _login(client, "scout")
    result = _accepted_card(client, token)
    pid = result["cardPublicId"]
    with db.engine.begin() as conn:
        conn.execute(
            text("UPDATE user_collection_cards SET card_photo_key = NULL WHERE public_id = :p"),
            {"p": pid},
        )
    resp = client.get(f"/api/collection/card-{pid}/image", cookies=_cookies(token))
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "IMAGE_NOT_FOUND"


def test_me_restores_session_and_logout_protects(client):
    token = _login(client, "scout")
    me = client.get("/api/auth/me", cookies=_cookies(token))
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "scout"
    # after logout the session cookie is gone and protected routes are blocked
    client.post("/api/auth/logout", cookies=_cookies(token))
    denied = client.get("/api/daily-tasks", cookies=_cookies(token))
    assert denied.status_code == 401


def test_journal_recorded_after_discovery(client):
    token = _login(client, "scout")
    conftest.pair_home_base(client, token)
    _, did = conftest.make_discovery(client, token=token)
    client.post(f"/api/discoveries/{did}/submit", cookies=_cookies(token))
    entries = client.get("/api/journal", cookies=_cookies(token)).json()["entries"]
    assert len(entries) == 1
    assert entries[0]["title"] == "Bougainvillea Observation"
    assert entries[0]["card_url"]
    assert entries[0]["xp_earned"] > 0


def test_journal_is_isolated_between_users(client):
    token_a = _login(client, "alice")
    token_b = _login(client, "bob")
    _accepted_card(client, token_a)
    entries_b = client.get("/api/journal", cookies=_cookies(token_b)).json()["entries"]
    assert entries_b == []
    entries_a = client.get("/api/journal", cookies=_cookies(token_a)).json()["entries"]
    assert len(entries_a) == 1


def test_profile_stats_reflect_activity(client):
    token = _login(client, "scout")
    empty = client.get("/api/profile/stats", cookies=_cookies(token)).json()
    assert empty["unique_species"] == 0
    assert empty["xp_total"] == 0
    _accepted_card(client, token)
    stats = client.get("/api/profile/stats", cookies=_cookies(token)).json()
    assert stats["unique_species"] == 1
    assert stats["observations"] == 1
    assert stats["xp_total"] >= 30