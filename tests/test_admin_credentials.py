import time
import secrets
import pytest
from starlette.testclient import TestClient
from app.main import app


def test_admin_update_user_username_and_password():
    """Verify that an admin can update a user's username and reset their password."""
    client = TestClient(app)

    # 1. Sign up a new user
    uid = secrets.token_hex(4)
    email = f"admin_cred_{uid}@example.com"
    old_username = f"OriginalName_{uid}"
    old_password = "password123"
    signup_res = client.post("/api/v1/auth/signup", json={"email": email, "username": old_username, "password": old_password})
    assert signup_res.status_code == 200

    # Verify user in database
    from database import SessionLocal
    from models import User
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    user.verified = 1
    db.commit()
    user_id = user.id
    db.close()

    # 2. Log in as admin
    admin_login_res = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin"})
    assert admin_login_res.status_code == 200
    admin_token = admin_login_res.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Update username to "RenamedWizard" and password to "brandnewsecret123"
    new_username = f"RenamedWizard_{uid}"
    new_password = "brandnewsecret123"
    update_res = client.post(
        f"/api/v1/admin/users/{user_id}/credentials",
        json={"username": new_username, "password": new_password},
        headers=admin_headers,
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["status"] == "ok"
    assert data["username"] == new_username
    assert "username" in data["updated"]
    assert "password" in data["updated"]

    # 4. Attempt login with old password (must fail)
    old_login_res = client.post("/api/v1/auth/login", json={"username": new_username, "password": old_password})
    assert old_login_res.status_code == 401

    # 5. Attempt login with new username and new password (must succeed!)
    new_login_res = client.post("/api/v1/auth/login", json={"username": new_username, "password": new_password})
    assert new_login_res.status_code == 200
    assert "token" in new_login_res.json()


def test_admin_update_credentials_validation():
    """Verify validation rules: minimum password length, username uniqueness, and auth protection."""
    client = TestClient(app)

    # 1. Sign up User A and User B
    uid = secrets.token_hex(4)
    email_a = f"usera_{uid}@example.com"
    email_b = f"userb_{uid}@example.com"
    user_a_name = f"UserAlpha_{uid}"
    user_b_name = f"UserBeta_{uid}"
    client.post("/api/v1/auth/signup", json={"email": email_a, "username": user_a_name, "password": "password123"})
    client.post("/api/v1/auth/signup", json={"email": email_b, "username": user_b_name, "password": "password123"})

    from database import SessionLocal
    from models import User
    db = SessionLocal()
    user_a = db.query(User).filter(User.email == email_a).first()
    user_b = db.query(User).filter(User.email == email_b).first()
    user_a_id = user_a.id
    user_b_id = user_b.id
    db.close()


    # 2. Reject unauthenticated request
    unauth_res = client.post(f"/api/v1/admin/users/{user_a_id}/credentials", json={"username": "NewName"})
    assert unauth_res.status_code == 401

    # 3. Log in as admin
    admin_login_res = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin"})
    admin_token = admin_login_res.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Reject duplicate username (User A trying to take User B's username)
    dup_res = client.post(
        f"/api/v1/admin/users/{user_a_id}/credentials",
        json={"username": "UserBeta"},
        headers=admin_headers,
    )
    assert dup_res.status_code == 400
    assert "already taken" in dup_res.json().get("detail", dup_res.json().get("error", {}).get("message", ""))

    # 5. Reject short password (< 8 chars)
    short_pw_res = client.post(
        f"/api/v1/admin/users/{user_a_id}/credentials",
        json={"password": "123"},
        headers=admin_headers,
    )
    assert short_pw_res.status_code == 400
    assert "at least 8 characters" in short_pw_res.json().get("detail", short_pw_res.json().get("error", {}).get("message", ""))

    # 6. Reject short username (< 3 chars)
    short_user_res = client.post(
        f"/api/v1/admin/users/{user_a_id}/credentials",
        json={"username": "ab"},
        headers=admin_headers,
    )
    assert short_user_res.status_code == 400
