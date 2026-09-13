import json
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database.models import GameSession
from app.infrastructure.database.engine import SessionLocal


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


class TestBattleRetryAndRestart:
    def test_defeat_retry_rejected_when_player_not_defeated(self, monkeypatch):
        """Defeat retry must require player defeat (player_hp <= 0)."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_retry_{uid}@test.com", f"user_{uid}")

        start_res = client.post("/api/game/new", headers=headers)
        assert start_res.status_code == 200
        sid = start_res.json()["session_id"]
        assert start_res.json()["player"]["hp"] > 0

        # Attempting retry while player is alive must fail with 400
        res = client.post("/api/battle/retry", headers=headers, json={"session_id": sid})
        assert res.status_code == 400
        assert "Cannot retry an active battle unless defeated" in res.json()["detail"]

    def test_defeat_retry_rejected_when_boss_already_defeated(self, monkeypatch):
        """Cannot retry if boss is already defeated."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_bossdef_{uid}@test.com", f"user_{uid}")

        start_res = client.post("/api/game/new", headers=headers)
        sid = start_res.json()["session_id"]

        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            gs.boss_hp = 0
            gs.player_hp = 0
            db.commit()

        res = client.post("/api/battle/retry", headers=headers, json={"session_id": sid})
        assert res.status_code == 400
        assert "The boss is already defeated" in res.json()["detail"]

    def test_defeat_retry_resets_current_boss_state_and_cursor(self, monkeypatch):
        """When defeated, retry resets player HP, boss HP, cursor for that boss, and invalidates turn state."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_succ_{uid}@test.com", f"user_{uid}")

        start_res = client.post("/api/game/new", headers=headers)
        sid = start_res.json()["session_id"]

        # Select a spell to advance turn and set an active question
        sel_res = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "fire-spark"})
        assert sel_res.status_code == 200
        turn_id = sel_res.json()["turn_id"]
        assert turn_id is not None

        # Simulate player defeat and advanced cursor
        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            gs.player_hp = 0
            gs.boss_hp = 50
            # Set cursor for chapter 1 boss
            cursors = {"1:orbital-ogre": 3, "other:boss": 5}
            gs.question_cursors_json = json.dumps(cursors)
            db.commit()

        # Defeat retry
        retry_res = client.post("/api/battle/retry", headers=headers, json={"session_id": sid})
        assert retry_res.status_code == 200
        data = retry_res.json()

        assert data["player"]["hp"] == data["player"]["max_hp"]
        assert data["boss"]["hp"] == data["boss"]["max_hp"]
        assert data["active_spell"] is None
        assert data["question"] is None
        assert data["turn_id"] is None

        # Verify cursor was reset to 0 for this boss in the database
        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            stored_cursors = json.loads(gs.question_cursors_json)
            # Active boss cursor was reset to 0
            for k in stored_cursors:
                if k.startswith("1:"):
                    assert stored_cursors[k] == 0
            assert stored_cursors.get("other:boss") == 5

        # Verify stale turn_id cannot be used anymore
        ans_res = client.post(
            "/api/battle/answer",
            headers=headers,
            json={"session_id": sid, "turn_id": turn_id, "answer": "A"},
        )
        assert ans_res.status_code == 400
        assert "No active question" in ans_res.json()["detail"]

    def test_retry_preserves_current_chapter_and_does_not_rollback_to_chapter_1(self, monkeypatch):
        """Retry must remain on user's current chapter and boss, never rolling back to Chapter 1."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_ch_pres_{uid}@test.com", f"user_{uid}")

        start_res = client.post("/api/game/new", headers=headers)
        sid = start_res.json()["session_id"]

        # Advance user to Chapter 2, Boss 0 (or Chapter 3)
        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            gs.chapter = 2
            gs.boss_index = 0
            gs.player_hp = 0  # defeated
            gs.boss_hp = 20
            gs.question_cursors_json = json.dumps({"1:ch1_boss": 4, "2:ch2_boss": 2})
            db.commit()

        # Retry battle
        res = client.post("/api/battle/retry", headers=headers, json={"session_id": sid})
        assert res.status_code == 200
        state = res.json()

        # CRITICAL ASSERTION: chapter must remain 2, NOT rolled back to 1!
        assert state["chapter"] == 2, f"Expected chapter 2, but rolled back to {state['chapter']}!"
        assert state["player"]["hp"] == state["player"]["max_hp"]

        # Verify database state
        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            assert gs.chapter == 2
            assert gs.boss_index == 0
            cursors = json.loads(gs.question_cursors_json)
            assert cursors.get("1:ch1_boss") == 4  # Untouched

    def test_practice_restart_allowed_mid_battle(self, monkeypatch):
        """Practice restart (/api/battle/restart or mode='practice') is allowed while player is alive."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_restart_{uid}@test.com", f"user_{uid}")

        start_res = client.post("/api/game/new", headers=headers)
        sid = start_res.json()["session_id"]

        # Simulate damage dealt and taken mid-battle (player_hp > 0, boss_hp > 0)
        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            gs.player_hp = 80
            gs.boss_hp = 40
            gs.chapter = 2
            gs.boss_index = 0
            db.commit()

        # Practice restart via dedicated endpoint POST /api/battle/restart
        restart_res = client.post("/api/battle/restart", headers=headers, json={"session_id": sid})
        assert restart_res.status_code == 200
        state = restart_res.json()

        assert state["chapter"] == 2
        assert state["player"]["hp"] == state["player"]["max_hp"]
        assert state["boss"]["hp"] == state["boss"]["max_hp"]
        assert "Practice restart" in state["log"][-1]

        # Also works via /api/battle/retry with mode="practice"
        res_mode = client.post(
            "/api/battle/retry",
            headers=headers,
            json={"session_id": sid, "mode": "practice"},
        )
        assert res_mode.status_code == 200
        assert res_mode.json()["chapter"] == 2


class TestBattleNextTurnProgression:
    def test_next_turn_rejected_when_boss_alive_full_hp(self, monkeypatch):
        """Cannot advance to next turn if current boss is at full health."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_nt_alive_{uid}@test.com", f"user_{uid}")

        start_res = client.post("/api/game/new", headers=headers)
        assert start_res.status_code == 200
        sid = start_res.json()["session_id"]
        assert start_res.json()["boss"]["hp"] > 0

        # Attempting next-turn on an alive boss must fail with 400 Bad Request
        res = client.post("/api/battle/next-turn", headers=headers, json={"session_id": sid})
        assert res.status_code == 400
        assert "Current boss is still alive" in res.json()["detail"]

    def test_next_turn_rejected_when_boss_alive_mid_hp(self, monkeypatch):
        """Cannot advance to next turn if current boss is partially damaged but alive."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_nt_mid_{uid}@test.com", f"user_{uid}")

        start_res = client.post("/api/game/new", headers=headers)
        sid = start_res.json()["session_id"]

        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            gs.boss_hp = 35
            db.commit()

        res = client.post("/api/battle/next-turn", headers=headers, json={"session_id": sid})
        assert res.status_code == 400
        assert "Current boss is still alive (35 HP remaining)" in res.json()["detail"]

    def test_next_turn_rejected_when_player_defeated(self, monkeypatch):
        """Cannot advance if player is defeated even if boss is defeated."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_nt_pdef_{uid}@test.com", f"user_{uid}")

        start_res = client.post("/api/game/new", headers=headers)
        sid = start_res.json()["session_id"]

        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            gs.boss_hp = 0
            gs.player_hp = 0
            db.commit()

        res = client.post("/api/battle/next-turn", headers=headers, json={"session_id": sid})
        assert res.status_code == 400
        assert "Player has been defeated" in res.json()["detail"]

    def test_next_turn_rejected_when_turn_in_progress(self, monkeypatch):
        """Cannot advance while a combat question turn is actively pending."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_nt_turn_{uid}@test.com", f"user_{uid}")

        start_res = client.post("/api/game/new", headers=headers)
        sid = start_res.json()["session_id"]

        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            gs.boss_hp = 0
            gs.turn_id = "test_pending_turn_123"
            gs.active_spell = "fire-spark"
            db.commit()

        res = client.post("/api/battle/next-turn", headers=headers, json={"session_id": sid})
        assert res.status_code == 400
        assert "question turn is in progress" in res.json()["detail"]

    def test_next_turn_succeeds_when_boss_defeated_and_prevents_replay(self, monkeypatch):
        """Advance succeeds when boss is defeated (boss_hp <= 0), and sequential call is blocked."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_nt_win_{uid}@test.com", f"user_{uid}")

        start_res = client.post("/api/game/new", headers=headers)
        sid = start_res.json()["session_id"]
        initial_boss_slug = start_res.json()["boss"]["id"]

        # Simulate legitimate boss defeat
        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            gs.boss_hp = 0
            gs.turn_id = None
            gs.active_spell = None
            db.commit()

        # Legitimate next-turn call succeeds
        res = client.post("/api/battle/next-turn", headers=headers, json={"session_id": sid})
        assert res.status_code == 200
        state = res.json()
        assert state["boss"]["hp"] == state["boss"]["max_hp"]
        assert state["player"]["hp"] == state["player"]["max_hp"]
        assert initial_boss_slug in state["completed"]

        # Second call immediately after advancing must fail because next boss has full HP!
        res_repeat = client.post("/api/battle/next-turn", headers=headers, json={"session_id": sid})
        assert res_repeat.status_code == 400
        assert "Current boss is still alive" in res_repeat.json()["detail"]
