import pytest
import json
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database.engine import SessionLocal
from app.infrastructure.database.models import User, GameSession
from app.infrastructure.identity.crypto import hash_password
from app.domain.combat.rules import grade_answer, evaluate_combat_turn


@pytest.fixture
def test_user_and_session():
    client = TestClient(app)
    username = f"shuffle_user_{uuid.uuid4().hex[:6]}"
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


def test_grade_answer_validates_by_correct_answer_text():
    # Validates matching text
    assert grade_answer("Electrophilic Addition", "Electrophilic Addition") is True
    assert grade_answer("electrophilic addition", "Electrophilic Addition") is True
    assert grade_answer("  Electrophilic Addition  ", "Electrophilic Addition") is True
    
    # Rejects incorrect text
    assert grade_answer("Nucleophilic Substitution", "Electrophilic Addition") is False
    assert grade_answer("", "Electrophilic Addition") is False
    assert grade_answer("Electrophilic Addition", "") is False


def test_grade_answer_resolves_option_letter_with_choices():
    choices = [
        "Elimination E1",
        "Electrophilic Addition",
        "Free Radical Halogenation",
        "Nucleophilic Substitution SN2",
    ]
    correct_text = "Electrophilic Addition"

    # Option 'B' corresponds to index 1, which is "Electrophilic Addition"
    assert grade_answer("B", correct_text, choices=choices) is True
    assert grade_answer("b", correct_text, choices=choices) is True

    # Option 'A' corresponds to "Elimination E1", which is incorrect
    assert grade_answer("A", correct_text, choices=choices) is False

    # Option 'C' and 'D' are incorrect
    assert grade_answer("C", correct_text, choices=choices) is False
    assert grade_answer("D", correct_text, choices=choices) is False

    # Without choices provided, option letters do not match unless text literally equals "B"
    assert grade_answer("B", correct_text, choices=None) is False


def test_evaluate_combat_turn_with_choices():
    choices = [
        "Sn1",
        "Sn2",
        "E1",
        "E2",
    ]
    correct_text = "Sn2"

    # Answer by text
    res_text, p_hp, b_hp = evaluate_combat_turn(
        spell_id="fire-spark",
        submitted_answer="Sn2",
        question_prompt="Which mechanism involves inversion of configuration?",
        correct_answer=correct_text,
        explanation="SN2 proceeds via backside attack.",
        current_player_hp=100,
        current_boss_hp=100,
        rng_roll=0.9,
        choices=choices,
    )
    assert res_text.correct is True
    assert b_hp == 80

    # Answer by letter 'B' (index 1 is Sn2)
    res_letter, p_hp, b_hp = evaluate_combat_turn(
        spell_id="fire-spark",
        submitted_answer="B",
        question_prompt="Which mechanism involves inversion of configuration?",
        correct_answer=correct_text,
        explanation="SN2 proceeds via backside attack.",
        current_player_hp=100,
        current_boss_hp=100,
        rng_roll=0.9,
        choices=choices,
    )
    assert res_letter.correct is True
    assert b_hp == 80


def test_select_spell_shuffles_choices_and_preserves_correct_answer(test_user_and_session):
    client, headers, sid, _ = test_user_and_session

    res = client.post("/api/battle/select-spell", headers=headers, json={"spell_id": "fire-spark", "session_id": sid})
    assert res.status_code == 200
    state = res.json()

    assert state["active_spell"] == "fire-spark"
    assert state["question"] is not None
    assert len(state["question"]["choices"]) == 4

    # The choices stored in session.active_question_json should match state["question"]["choices"]
    with SessionLocal() as db:
        session = db.query(GameSession).filter(GameSession.id == sid).first()
        active_q = json.loads(session.active_question_json)
        prompt, choices, correct_answer = active_q[0], active_q[1], active_q[2]
        assert choices == state["question"]["choices"]
        assert correct_answer in choices


def test_answer_question_with_shuffled_choices(test_user_and_session):
    client, headers, sid, _ = test_user_and_session

    # Select spell
    sel_res = client.post("/api/battle/select-spell", headers=headers, json={"spell_id": "fire-spark", "session_id": sid})
    assert sel_res.status_code == 200
    state = sel_res.json()

    with SessionLocal() as db:
        session = db.query(GameSession).filter(GameSession.id == sid).first()
        active_q = json.loads(session.active_question_json)
        correct_answer = active_q[2]
        turn_id = session.turn_id
        version = session.version

    # Answering with exact correct answer text
    ans_res = client.post(
        "/api/battle/answer",
        headers=headers,
        json={
            "session_id": sid,
            "answer": correct_answer,
            "turn_id": turn_id,
            "expected_version": version,
        },
    )
    assert ans_res.status_code == 200
    res = ans_res.json()
    assert res["correct"] is True
    assert res["damage"] > 0
