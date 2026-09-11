import pytest
from starlette.testclient import TestClient

from app.main import app
from app.infrastructure.database.engine import SessionLocal, ensure_db_schema
from app.infrastructure.database.models import (
    User,
    AdminUser,
    AdminSession,
    AdminAuditLog,
    Question,
)
from app.infrastructure.database.admin_repo import AdminRepository
from app.infrastructure.identity.crypto import code_hash
from app.observability.logging import ADMIN_LOG_FILE, DEFAULT_LOG_FILE


@pytest.fixture(autouse=True)
def setup_db():
    ensure_db_schema()
    yield


def test_default_admin_users_seeded():
    """Verify that default admin users ('admin' and 'admin1') are seeded in OB_admin_users with secure hashes."""
    with SessionLocal() as db:
        repo = AdminRepository(db)
        admin = repo.get_by_username("admin")
        assert admin is not None, "Default admin user 'admin' not found in OB_admin_users"
        assert admin.role in ("admin", "superadmin")
        assert admin.is_active == 1
        assert "$" in admin.password_hash  # PBKDF2 salt$digest format

        admin1 = repo.get_by_username("admin1")
        assert admin1 is not None, "Default admin user 'admin1' not found in OB_admin_users"
        assert admin1.is_active == 1

        # Verify credential validation logic against database
        assert repo.verify_admin_credentials("admin", "admin") is not None
        assert repo.verify_admin_credentials("admin", "wrongpassword") is None
        assert repo.verify_admin_credentials("admin1", "admin2") is not None
        assert repo.verify_admin_credentials("admin1", "wrongpassword") is None


def test_database_admin_login_and_session_tracking():
    """Verify admin login authenticates from database and persists session in OB_admin_sessions."""
    client = TestClient(app)

    # 1. Login with admin/admin
    res = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["username"] == "admin"
    assert "token" in data
    assert "admin_id" in data
    token = data["token"]
    thash = code_hash(token)

    # Verify session recorded in database
    with SessionLocal() as db:
        sess = db.query(AdminSession).filter(AdminSession.token_hash == thash).first()
        assert sess is not None
        assert sess.admin_user_id == data["admin_id"]

    # 2. Login with admin1/admin2
    res2 = client.post("/api/v1/admin/login", json={"username": "admin1", "password": "admin2"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["username"] == "admin1"

    # 3. Invalid credentials rejected
    fail_res = client.post("/api/v1/admin/login", json={"username": "admin", "password": "wrong"})
    assert fail_res.status_code == 401


def test_player_cannot_login_as_admin_and_vice_versa():
    """Verify player credentials cannot access admin portal and admin credentials cannot log into player sessions."""
    client = TestClient(app)

    # 1. Sign up a regular player
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "player_sec_test@example.com", "username": "player_sec_user", "password": "player_password_123"},
    )
    assert signup_res.status_code == 200

    # 2. Player credentials attempted on Admin Login -> MUST FAIL (401)
    admin_login_attempt = client.post(
        "/api/v1/admin/login",
        json={"username": "player_sec_user", "password": "player_password_123"},
    )
    assert admin_login_attempt.status_code == 401

    # 3. Admin credentials attempted on Player Login -> MUST FAIL (401)
    player_login_attempt = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert player_login_attempt.status_code == 401


def test_player_cannot_signup_with_admin_username():
    """Verify regular user registration rejects usernames reserved for or belonging to administrators."""
    client = TestClient(app)

    # Try signing up with 'admin'
    res = client.post(
        "/api/v1/auth/signup",
        json={"email": "fake_admin@example.com", "username": "admin", "password": "some_password_123"},
    )
    assert res.status_code == 400
    assert "reserved" in res.json()["detail"].lower()

    # Try signing up with 'admin1'
    res2 = client.post(
        "/api/v1/auth/signup",
        json={"email": "fake_admin1@example.com", "username": "admin1", "password": "some_password_123"},
    )
    assert res2.status_code == 400
    assert "reserved" in res2.json()["detail"].lower()


def test_admin_question_bank_changes_logged_with_admin_id():
    """Verify question bank updates and reordering log the admin user ID to admin.log and OB_admin_audit_logs."""
    client = TestClient(app)

    # Log in as admin
    login_res = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin"}).json()
    token = login_res["token"]
    admin_id = login_res["admin_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Find or create a test question
    with SessionLocal() as db:
        q = db.query(Question).first()
        if not q:
            q = Question(
                track_id="organic1",
                raw_id="test_raw_q1",
                chapter=1,
                chapter_title="Chapter 1",
                boss_name="Alchemist",
                boss_slug="alchemist",
                order_index=1,
                topic="Basics",
                difficulty="easy",
                prompt="Initial prompt for audit test?",
                options_json=[{"label": "A", "text": "Choice A"}, {"label": "B", "text": "Choice B"}],
                correct_option="A",
                correct_answer="Choice A",
                explanation="Initial explanation",
                spells_json=[20, 30, 45],
                health_json=[100],
            )
            db.add(q)
            db.commit()
            db.refresh(q)
        qid = q.id
        track_id = q.track_id


    # Update question prompt
    updated_prompt = f"Updated prompt by Admin test at {qid}"
    update_res = client.put(
        f"/api/v1/admin/questions/{qid}",
        json={"prompt": updated_prompt},
        headers=headers,
    )
    assert update_res.status_code == 200

    # Verify audit log in database
    with SessionLocal() as db:
        audit = (
            db.query(AdminAuditLog)
            .filter(AdminAuditLog.action == "UPDATE_QUESTION", AdminAuditLog.target_id == str(qid))
            .order_by(AdminAuditLog.created_at.desc())
            .first()
        )
        assert audit is not None, "Audit log entry for UPDATE_QUESTION not found"
        assert audit.admin_user_id == admin_id
        assert audit.admin_username == "admin"
        assert audit.target_type == "question"

    # Verify separate admin log file contains the action
    if ADMIN_LOG_FILE.is_file():
        content = ADMIN_LOG_FILE.read_text(encoding="utf-8")
        assert "[ADMIN_ACTION]" in content
        assert admin_id in content


def test_admin_logs_separated_from_player_logs():
    """Verify admin operations write to logs/admin.log and admin tail endpoint returns admin lines."""
    client = TestClient(app)
    login_res = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin"}).json()
    token = login_res["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Call admin logging tail endpoint for admin logs
    tail_res = client.get("/api/v1/admin/system/logging/tail?log_type=admin", headers=headers)
    assert tail_res.status_code == 200
    data = tail_res.json()
    assert data["log_type"] == "admin"
    assert "admin.log" in data["log_file"]


def test_admin_logout_revokes_db_session():
    """Verify logging out deletes the session from OB_admin_sessions and invalidates access."""
    client = TestClient(app)

    # 1. Log in
    login_res = client.post("/api/v1/admin/login", json={"username": "admin1", "password": "admin2"}).json()
    token = login_res["token"]
    thash = code_hash(token)
    headers = {"Authorization": f"Bearer {token}"}

    # Verify session exists in DB
    with SessionLocal() as db:
        sess = db.query(AdminSession).filter(AdminSession.token_hash == thash).first()
        assert sess is not None

    # Verify access to admin status
    status_res = client.get("/api/v1/admin/status", headers=headers)
    assert status_res.status_code == 200

    # 2. Log out
    logout_res = client.post("/api/v1/admin/logout", headers=headers)
    assert logout_res.status_code == 200

    # Verify session was deleted from DB
    with SessionLocal() as db:
        sess_after = db.query(AdminSession).filter(AdminSession.token_hash == thash).first()
        assert sess_after is None

    # 3. Subsequent request with old token -> MUST FAIL (401)
    revoked_res = client.get("/api/v1/admin/status", headers=headers)
    assert revoked_res.status_code == 401
