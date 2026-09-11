import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.settings import settings
from app.infrastructure.database.engine import SessionLocal
from app.infrastructure.database.models import User
from app.infrastructure.identity.crypto import hash_password


@pytest.fixture
def client():
    return TestClient(app)


def test_signup_accepts_valid_username_patterns(client):
    """Test valid usernames matching ^[A-Za-z0-9_.-]{3,24}$ are accepted."""
    valid_usernames = [
        f"usr_{uuid.uuid4().hex[:4]}",
        f"u-name-{uuid.uuid4().hex[:4]}",
        f"user.dot.{uuid.uuid4().hex[:4]}",
        f"A1_b2.{uuid.uuid4().hex[:4]}",
    ]
    for uname in valid_usernames:
        res = client.post(
            "/api/auth/signup",
            json={
                "email": f"{uname}@example.com",
                "username": uname,
                "password": "ValidPassword123!",
            },
        )
        assert res.status_code == 200, f"Failed for valid username: {uname}, detail: {res.text}"


def test_signup_rejects_invalid_username_patterns_including_xss(client):
    """Test usernames violating ^[A-Za-z0-9_.-]{3,24}$ or containing XSS vectors are rejected."""
    invalid_usernames = [
        "<svg onload=alert(1)>",       # Stored XSS attempt
        "<script>alert(1)</script>",   # Script tag attempt
        "ab",                          # Too short (< 3)
        "a" * 25,                      # Too long (> 24)
        "user name",                   # Contains spaces
        "user@name",                   # Contains @
        "user$name",                   # Contains $
        "user#tag",                    # Contains #
        "user!alert",                  # Contains !
        "user%20name",                 # Contains %
        "user;drop",                   # Contains ;
    ]
    for uname in invalid_usernames:
        res = client.post(
            "/api/auth/signup",
            json={
                "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
                "username": uname,
                "password": "ValidPassword123!",
            },
        )
        assert res.status_code == 422, f"Should reject invalid username: {uname}, got: {res.status_code}"


def test_admin_create_user_enforces_strict_username_pattern(client):
    """Test creating admin users requires valid pattern ^[A-Za-z0-9_.-]{3,24}$."""
    # Login as admin
    login_res = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin"})
    assert login_res.status_code == 200
    token = login_res.cookies.get("admin_token") or login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}

    # Invalid admin username (XSS vector)
    bad_res = client.post(
        "/api/v1/admin/manage/users",
        headers=headers,
        json={"username": "<img src=x onerror=1>", "password": "AdminPassword123!"},
    )
    assert bad_res.status_code in (400, 422)

    # Valid admin username
    valid_uname = f"adm_{uuid.uuid4().hex[:6]}"
    good_res = client.post(
        "/api/v1/admin/manage/users",
        headers=headers,
        json={"username": valid_uname, "password": "AdminPassword123!"},
    )
    assert good_res.status_code == 200
    assert good_res.json()["username"] == valid_uname


def test_admin_update_user_credentials_enforces_strict_username_pattern(client):
    """Test updating an existing player's username enforces ^[A-Za-z0-9_.-]{3,24}$."""
    # Create player
    uname = f"upd_{uuid.uuid4().hex[:6]}"
    with SessionLocal() as db:
        user = User(
            id=str(uuid.uuid4()),
            email=f"{uname}@example.com",
            username=uname,
            password_hash=hash_password("Password123!"),
            verified=1,
        )
        db.add(user)
        db.commit()
        user_id = user.id

    # Login as admin
    login_res = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin"})
    token = login_res.cookies.get("admin_token") or login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt update with XSS payload
    bad_res = client.post(
        f"/api/v1/admin/users/{user_id}/credentials",
        headers=headers,
        json={"username": "<script>evil()</script>"},
    )
    assert bad_res.status_code in (400, 422)

    # Valid update
    new_valid_name = f"new_{uuid.uuid4().hex[:6]}"
    good_res = client.post(
        f"/api/v1/admin/users/{user_id}/credentials",
        headers=headers,
        json={"username": new_valid_name},
    )
    assert good_res.status_code == 200
    assert good_res.json()["username"] == new_valid_name


def test_browser_admin_login_does_not_return_token_in_body(client):
    """Verify browser login responses do NOT return the admin token in JSON body, but DO set HttpOnly cookie."""
    # Browser login with client_type="browser"
    res = client.post(
        "/api/v1/admin/login",
        json={"username": "admin", "password": "admin", "client_type": "browser"},
        headers={"X-Client-Type": "browser"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["username"] == "admin"
    assert "token" not in data, f"Security violation: Token leaked in browser response body! data: {data}"

    # Verify HttpOnly cookie was set
    cookie = res.cookies.get("admin_token")
    assert cookie is not None, "admin_token cookie must be set"


def test_api_admin_login_still_returns_token_for_automation(client):
    """Verify non-browser API clients can still receive token in body for backward-compatible automation."""
    res = client.post(
        "/api/v1/admin/login",
        json={"username": "admin", "password": "admin"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "token" in data
    assert res.cookies.get("admin_token") is not None
