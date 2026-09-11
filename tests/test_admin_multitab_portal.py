import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DBSession

from app.main import app
from app.settings import settings
from app.infrastructure.database.models import User, GameSession, Question
from app.infrastructure.database.repositories import UserRepository
from app.infrastructure.identity.crypto import hash_password


from app.infrastructure.database.engine import SessionLocal


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_auth_header(client):
    resp = client.post(
        "/api/v1/admin/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


import uuid


def test_admin_users_and_verification_toggle(client, admin_auth_header):
    """Verify admin user list contains session_id and verification toggle works."""
    db_session = SessionLocal()
    user_id = uuid.uuid4().hex
    try:
        test_user = User(
            id=user_id,
            username=f"portal_user_{user_id[:6]}",
            email=f"portal_{user_id[:6]}@example.com",
            password_hash=hash_password("Password123!"),
            verified=0,
        )
        db_session.add(test_user)
        db_session.commit()
    finally:
        db_session.close()

    # 1. Fetch user list
    resp = client.get("/api/v1/admin/users", headers=admin_auth_header)
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    found = next((u for u in data["users"] if u["id"] == user_id), None)
    assert found is not None
    assert found["verified"] is False
    assert "session_id" in found

    # 2. Toggle verification to verified
    resp_toggle = client.post(f"/api/v1/admin/users/{user_id}/verify", headers=admin_auth_header)
    assert resp_toggle.status_code == 200
    assert resp_toggle.json()["verified"] is True

    db_check = SessionLocal()
    try:
        refreshed_user = db_check.query(User).filter(User.id == user_id).first()
        assert refreshed_user.verified == 1
    finally:
        db_check.close()

    # 3. Toggle back to unverified
    resp_toggle_back = client.post(f"/api/v1/admin/users/{user_id}/verify", headers=admin_auth_header)
    assert resp_toggle_back.status_code == 200
    assert resp_toggle_back.json()["verified"] is False


def test_admin_sessions_enriched_state(client, admin_auth_header):
    """Verify admin sessions response returns turn_id, version, cooldowns, and combat log."""
    db_session = SessionLocal()
    user_id = uuid.uuid4().hex
    sess_id = uuid.uuid4().hex
    try:
        user = User(
            id=user_id,
            username=f"session_user_{user_id[:6]}",
            email=f"session_{user_id[:6]}@example.com",
            password_hash=hash_password("Password123!"),
            verified=1,
        )
        db_session.add(user)

        import json
        sess = GameSession(
            id=sess_id,
            user_id=user.id,
            content_source="track:default",
            chapter=1,
            boss_index=0,
            player_hp=150,
            player_max_hp=150,
            boss_hp=100,
            turn_id="turn_tok_abc123",
            version=4,
            completed_json=json.dumps([]),
            cooldowns_json=json.dumps({"Fireball": 2}),
            log_json=json.dumps(["Player engaged Boss 1."]),
            active_spell="Acid Arrow",
        )
        db_session.add(sess)
        db_session.commit()
    finally:
        db_session.close()

    resp = client.get("/api/v1/admin/sessions", headers=admin_auth_header)
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data
    found_sess = next((s for s in data["sessions"] if s["session_id"] == sess_id), None)
    assert found_sess is not None
    assert found_sess["turn_id"] == "turn_tok_abc123"
    assert found_sess["version"] == 4
    assert found_sess["active_spell"] == "Acid Arrow"
    assert found_sess["cooldowns"] == {"Fireball": 2}
    assert found_sess["log"] == ["Player engaged Boss 1."]


def test_admin_system_config_and_runtime_environment(client, admin_auth_header):
    """Verify get_system_config returns runtime_environment details."""
    resp = client.get("/api/v1/admin/system/config", headers=admin_auth_header)
    assert resp.status_code == 200
    data = resp.json()

    assert "runtime_environment" in data
    re = data["runtime_environment"]
    assert "environment" in re
    assert "loaded_env_file" in re
    assert "debug" in re
    assert "cookie_secure" in re
    assert "allow_json_fallback" in re
    assert "web_concurrency" in re
    assert "app_replicas" in re
    assert "max_cluster_connections" in re
    assert "db_max_connections_limit" in re
    assert re["max_cluster_connections"] > 0


def test_admin_question_bank_and_releases_contract(client, admin_auth_header):
    """Verify question bank search and content releases endpoints."""
    # 1. Question bank query
    resp_q = client.get("/api/admin/tracks/default/questions?page=1&limit=5", headers=admin_auth_header)
    assert resp_q.status_code == 200
    q_data = resp_q.json()
    assert "items" in q_data
    assert "total" in q_data
    assert "pages" in q_data

    # 2. Releases query
    resp_r = client.get("/api/admin/tracks/default/releases", headers=admin_auth_header)
    assert resp_r.status_code == 200
    r_data = resp_r.json()
    assert "releases" in r_data


def test_admin_cache_warm_endpoint(client, admin_auth_header):
    """Verify cache warming trigger endpoint."""
    resp = client.post("/api/admin/system/cache/warm?tracks=default", headers=admin_auth_header)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "results" in data
    assert "stats" in data
