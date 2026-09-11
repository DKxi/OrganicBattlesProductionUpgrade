import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database.models import User, GameSession
from app.infrastructure.database.repositories import SessionRepository
from app.infrastructure.database.engine import SessionLocal
from app.api.v1.auth import hash_password


def _get_auth_headers(client: TestClient, monkeypatch, email: str, username: str) -> dict:
    """Helper to register/verify and return auth headers."""
    codes = []
    def mock_send(email_addr, uname, code):
        codes.append(code)

    import app as app_mod
    monkeypatch.setattr(app_mod, "send_verification_email", mock_send)

    signup_res = client.post("/api/auth/signup", json={
        "email": email,
        "username": username,
        "password": "Password123!"
    })
    assert signup_res.status_code == 200, f"Signup failed: {signup_res.text}"
    assert len(codes) > 0, "No code generated"
    code = codes[-1]

    verify_res = client.post("/api/auth/verify", json={"code": code})
    assert verify_res.status_code == 200, f"Verify failed: {verify_res.text}"
    token = verify_res.json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestSessionRepositoryOwnership:
    def test_repository_ownership_filtering(self):
        """Repository must query by session ID AND user ID, rejecting cross-user access."""
        db = SessionLocal()
        try:
            repo = SessionRepository(db)
            
            # Setup two users
            u1 = User(id="user_owner_001", email="owner@test.com", username="owner", password_hash=hash_password("pass"))
            u2 = User(id="user_attacker_002", email="attacker@test.com", username="attacker", password_hash=hash_password("pass"))
            db.merge(u1)
            db.merge(u2)
            
            # Setup session belonging to owner
            sess = GameSession(
                id="sess_owner_999",
                user_id="user_owner_001",
                chapter=1,
                boss_index=0,
                player_hp=100,
                player_max_hp=100,
                boss_hp=100,
                version=1,
            )
            db.merge(sess)
            db.commit()

            # 1. get_by_id without user_id returns session
            assert repo.get_by_id("sess_owner_999") is not None

            # 2. get_by_id with correct user_id returns session
            assert repo.get_by_id("sess_owner_999", user_id="user_owner_001") is not None

            # 3. get_by_id with attacker user_id returns None (SQL filter enforced)
            assert repo.get_by_id("sess_owner_999", user_id="user_attacker_002") is None

            # 4. exists check
            assert repo.exists("sess_owner_999") is True
            assert repo.exists("sess_ghost_000") is False

            # 5. get_for_user_or_raise for attacker raises 403 Forbidden
            with pytest.raises(HTTPException) as exc_info:
                repo.get_for_user_or_raise(user_id="user_attacker_002", session_id="sess_owner_999")
            assert exc_info.value.status_code == 403
            assert "Not authorized" in exc_info.value.detail

            # 6. get_for_user_or_raise for non-existent session raises 404 Not Found
            with pytest.raises(HTTPException) as exc_info:
                repo.get_for_user_or_raise(user_id="user_attacker_002", session_id="sess_ghost_000")
            assert exc_info.value.status_code == 404

            # 7. delete by attacker fails and preserves session
            deleted = repo.delete("sess_owner_999", user_id="user_attacker_002")
            assert deleted is False
            assert repo.get_by_id("sess_owner_999") is not None

            # 8. delete by owner succeeds
            deleted = repo.delete("sess_owner_999", user_id="user_owner_001")
            assert deleted is True
            assert repo.get_by_id("sess_owner_999") is None
        finally:
            db.close()


import uuid


class TestSessionOwnershipEndpoints:
    def test_cross_user_battle_and_game_access_rejected_with_403(self, monkeypatch):
        """Verify that all battle and game endpoints reject foreign session_id with HTTP 403."""
        client = TestClient(app)

        # 1. Register User A (owner) and User B (attacker)
        uid_a = uuid.uuid4().hex[:8]
        uid_b = uuid.uuid4().hex[:8]
        headers_a = _get_auth_headers(client, monkeypatch, f"user_a_{uid_a}@test.com", f"user_a_{uid_a}")
        headers_b = _get_auth_headers(client, monkeypatch, f"user_b_{uid_b}@test.com", f"user_b_{uid_b}")

        # 2. User A initializes game session
        init_res = client.post("/api/game/new", headers=headers_a)
        assert init_res.status_code == 200
        session_a_id = init_res.json()["session_id"]
        assert session_a_id

        # 3. User B initializes their own game session
        init_res_b = client.post("/api/game/new", headers=headers_b)
        assert init_res_b.status_code == 200
        session_b_id = init_res_b.json()["session_id"]
        assert session_b_id != session_a_id

        # --- Test 1: GET /api/game/state ---
        res = client.get(f"/api/game/state?session_id={session_a_id}", headers=headers_b)
        assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
        assert "Not authorized" in res.json()["detail"]

        # Non-existent session returns 404
        res = client.get("/api/game/state?session_id=nonexistent_sess_12345", headers=headers_b)
        assert res.status_code == 404

        # Owner gets 200
        res = client.get(f"/api/game/state?session_id={session_a_id}", headers=headers_a)
        assert res.status_code == 200

        # --- Test 2: POST /api/battle/select-spell ---
        # User B attempts to select spell on User A's session (via query param and json body)
        res = client.post(
            f"/api/battle/select-spell?session_id={session_a_id}",
            headers=headers_b,
            json={"spell_id": "fire-spark"},
        )
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]

        res = client.post(
            "/api/battle/select-spell",
            headers=headers_b,
            json={"session_id": session_a_id, "spell_id": "fire-spark"},
        )
        assert res.status_code == 403

        # Non-existent session returns 404
        res = client.post(
            "/api/battle/select-spell",
            headers=headers_b,
            json={"session_id": "nonexistent_sess_12345", "spell_id": "fire-spark"},
        )
        assert res.status_code == 404

        # User A successfully selects spell on their own session
        res_a_spell = client.post(
            "/api/battle/select-spell",
            headers=headers_a,
            json={"session_id": session_a_id, "spell_id": "fire-spark"},
        )
        assert res_a_spell.status_code == 200
        turn_id = res_a_spell.json()["turn_id"]

        # --- Test 3: POST /api/battle/answer ---
        # User B attempts to answer question on User A's session
        res = client.post(
            "/api/battle/answer",
            headers=headers_b,
            json={"session_id": session_a_id, "turn_id": turn_id, "answer": "A"},
        )
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]

        # Non-existent session returns 404
        res = client.post(
            "/api/battle/answer",
            headers=headers_b,
            json={"session_id": "nonexistent_sess_12345", "turn_id": turn_id, "answer": "A"},
        )
        assert res.status_code == 404

        # --- Test 4: POST /api/battle/next-turn ---
        res = client.post(f"/api/battle/next-turn?session_id={session_a_id}", headers=headers_b)
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]

        res = client.post("/api/battle/next-turn?session_id=nonexistent_sess_12345", headers=headers_b)
        assert res.status_code == 404

        # --- Test 5: POST /api/battle/retry ---
        res = client.post(f"/api/battle/retry?session_id={session_a_id}", headers=headers_b)
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]

        res = client.post("/api/battle/retry?session_id=nonexistent_sess_12345", headers=headers_b)
        assert res.status_code == 404

        # --- Test 6: POST /api/avatar/finalize ---
        # User B attempts to finalize avatar claiming User A's session
        res = client.post(
            f"/api/avatar/finalize?session_id={session_a_id}",
            headers=headers_b,
            json={"character": "organic-apprentice", "body": "arc", "config": {}},
        )
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]

        # --- Test 7: POST /api/game/track ---
        # User B attempts to change track on User A's session
        res = client.post(
            "/api/game/track",
            headers=headers_b,
            json={"session_id": session_a_id, "track_id": "standard_track"},
        )
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]

        res = client.post(
            "/api/game/track",
            headers=headers_b,
            json={"session_id": "nonexistent_sess_12345", "track_id": "standard_track"},
        )
        assert res.status_code == 404
