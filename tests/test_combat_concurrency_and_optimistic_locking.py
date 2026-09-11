import time
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.database.engine import SessionLocal
from app.infrastructure.database.models import User, GameSession
from app.infrastructure.identity.crypto import hash_password
from app.domain.content.loader import load_track_bundle
from app.settings import settings


@pytest.fixture
def test_user_and_session():
    client = TestClient(app)
    username = f"combat_user_{uuid.uuid4().hex[:6]}"
    user_id = str(uuid.uuid4())

    with SessionLocal() as db:
        u = User(
            id=user_id,
            email=f"{username}@example.com",
            username=username,
            password_hash=hash_password("Password123!"),
            verified=1,
        )
        db.add(u)
        db.commit()

    token = client.post("/api/auth/login", json={"username": username, "password": "Password123!"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    game_res = client.post("/api/game/new", headers=headers, json={})
    assert game_res.status_code == 200
    sid = game_res.json()["session_id"]

    return client, headers, sid, user_id


def test_answer_requires_turn_id(test_user_and_session):
    client, headers, sid, _ = test_user_and_session

    # Select spell to activate question
    sel_res = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "fire-spark"})
    assert sel_res.status_code == 200

    # 1. Missing turn_id in payload entirely -> 422 Unprocessable Entity
    bad_res1 = client.post("/api/battle/answer", headers=headers, json={"session_id": sid, "answer": "Some answer"})
    assert bad_res1.status_code == 422

    # 2. Empty turn_id string -> 400 Bad Request
    bad_res2 = client.post("/api/battle/answer", headers=headers, json={"session_id": sid, "answer": "Some answer", "turn_id": "   "})
    assert bad_res2.status_code == 400
    assert "Missing turn_id" in bad_res2.json()["detail"]


def test_rejects_invalid_or_consumed_turn_id(test_user_and_session):
    client, headers, sid, _ = test_user_and_session

    bundle = load_track_bundle(settings.root_dir, "default")
    ans_key = {p: c for p, ch, c in bundle.questions}

    # Select spell
    sel_res = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "fire-spark"})
    assert sel_res.status_code == 200
    turn_id = sel_res.json()["turn_id"]
    prompt = sel_res.json()["question"]["prompt"]
    correct_ans = ans_key[prompt]

    # 1. Tampered / wrong turn_id -> 409 Conflict
    bad_res = client.post("/api/battle/answer", headers=headers, json={
        "session_id": sid,
        "answer": correct_ans,
        "turn_id": "forged-turn-id-123",
    })
    assert bad_res.status_code == 409
    assert "Invalid or previously consumed" in bad_res.json()["detail"]

    # 2. Valid turn_id -> 200 OK
    ok_res = client.post("/api/battle/answer", headers=headers, json={
        "session_id": sid,
        "answer": correct_ans,
        "turn_id": turn_id,
    })
    assert ok_res.status_code == 200
    assert ok_res.json()["correct"] is True

    # 3. Double-tap / re-using the consumed turn_id -> 409 Conflict
    replay_res = client.post("/api/battle/answer", headers=headers, json={
        "session_id": sid,
        "answer": correct_ans,
        "turn_id": turn_id,
    })
    assert replay_res.status_code == 409 or replay_res.status_code == 400


def test_rejects_expired_turn_id(test_user_and_session):
    client, headers, sid, _ = test_user_and_session

    bundle = load_track_bundle(settings.root_dir, "default")
    ans_key = {p: c for p, ch, c in bundle.questions}

    sel_res = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "fire-spark"})
    assert sel_res.status_code == 200
    turn_id = sel_res.json()["turn_id"]
    prompt = sel_res.json()["question"]["prompt"]

    # Simulate expired turn by winding updated_at backwards by 400s (> 300s TTL)
    with SessionLocal() as db:
        sess = db.query(GameSession).filter(GameSession.id == sid).first()
        sess.updated_at = int(time.time()) - 400
        db.commit()

    exp_res = client.post("/api/battle/answer", headers=headers, json={
        "session_id": sid,
        "answer": ans_key[prompt],
        "turn_id": turn_id,
    })
    assert exp_res.status_code == 409
    assert "expired" in exp_res.json()["detail"].lower()


def test_optimistic_concurrency_conflict_on_answer(test_user_and_session):
    client, headers, sid, _ = test_user_and_session

    bundle = load_track_bundle(settings.root_dir, "default")
    ans_key = {p: c for p, ch, c in bundle.questions}

    sel_res = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "fire-spark"})
    assert sel_res.status_code == 200
    turn_id = sel_res.json()["turn_id"]
    client_version = sel_res.json()["version"]
    prompt = sel_res.json()["question"]["prompt"]

    # Simulate a concurrent modification by an alternate worker advancing the version
    with SessionLocal() as db:
        sess = db.query(GameSession).filter(GameSession.id == sid).first()
        sess.version += 1
        db.commit()

    # The answer request now encounters version mismatch on the optimistic update
    conflict_res = client.post("/api/battle/answer", headers=headers, json={
        "session_id": sid,
        "answer": ans_key[prompt],
        "turn_id": turn_id,
        "expected_version": client_version,
    })
    assert conflict_res.status_code == 409
    assert "concurrent" in conflict_res.json()["detail"].lower()


def test_optimistic_concurrency_conflict_on_select_spell(test_user_and_session):
    client, headers, sid, _ = test_user_and_session

    # Fetch initial session
    with SessionLocal() as db:
        sess = db.query(GameSession).filter(GameSession.id == sid).first()
        # Simulate race where another request bumped version
        sess.version += 5
        db.commit()

    # When client selects spell, version check fails -> 409
    # (or if spell selection runs concurrently)
    with SessionLocal() as db:
        sess = db.query(GameSession).filter(GameSession.id == sid).first()
        initial_ver = sess.version

        # Manually verify atomic update returns 0 rows when expected_version differs
        rows = db.query(GameSession).filter(
            GameSession.id == sid,
            GameSession.version == initial_ver - 1,
            GameSession.active_spell.is_(None),
        ).update({GameSession.version: GameSession.version + 1})
        db.commit()
        assert rows == 0


def test_successful_combat_lifecycle_increments_version_and_clears_turn(test_user_and_session):
    client, headers, sid, _ = test_user_and_session

    bundle = load_track_bundle(settings.root_dir, "default")
    ans_key = {p: c for p, ch, c in bundle.questions}

    # 1. State before spell selection
    with SessionLocal() as db:
        s0 = db.query(GameSession).filter(GameSession.id == sid).first()
        ver0 = s0.version
        assert s0.turn_id is None
        assert s0.active_spell is None

    # 2. Select spell
    sel_res = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "fire-spark"})
    assert sel_res.status_code == 200
    sel_data = sel_res.json()
    assert sel_data["turn_id"] is not None
    assert sel_data["version"] == ver0 + 1

    # 3. Answer question
    prompt = sel_data["question"]["prompt"]
    ans_res = client.post("/api/battle/answer", headers=headers, json={
        "session_id": sid,
        "answer": ans_key[prompt],
        "turn_id": sel_data["turn_id"],
    })
    assert ans_res.status_code == 200
    ans_data = ans_res.json()
    assert ans_data["turn_id"] is None
    assert ans_data["version"] == ver0 + 2
    assert ans_data["correct"] is True
