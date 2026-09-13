import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database.models import GameSession
from app.infrastructure.database.engine import SessionLocal

ROOT_DIR = Path(__file__).resolve().parent.parent


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


class TestExplanationFlowAndStaleness:
    def test_backend_returns_explanation_on_correct_and_incorrect_answers(self, monkeypatch):
        """Backend battle answer endpoint must return explanation, correct_answer, and prompt for both outcomes."""
        client = TestClient(app)
        uid = uuid.uuid4().hex[:8]
        headers = _get_auth_headers(client, monkeypatch, f"test_exp_{uid}@test.com", f"user_{uid}")

        # Start game
        start_res = client.post("/api/game/new", headers=headers)
        assert start_res.status_code == 200
        sid = start_res.json()["session_id"]

        # 1. Turn 1: Select spell
        sel1 = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "fire-spark"})
        assert sel1.status_code == 200
        q1 = sel1.json()["question"]
        t1 = sel1.json()["turn_id"]

        # Find the correct answer for q1 from database active_question_json
        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            import json
            active_q = json.loads(gs.active_question_json)
            # active_q is (prompt, choices, correct_letter, explanation)
            correct_letter = active_q[2]

        # Submit INCORRECT answer (non-matching string ensures incorrect grading regardless of choice shuffle)
        wrong_answer = "Definitely Wrong Answer 123"
        ans_wrong = client.post(
            "/api/battle/answer",
            headers=headers,
            json={"session_id": sid, "turn_id": t1, "answer": wrong_answer},
        )
        assert ans_wrong.status_code == 200
        data_wrong = ans_wrong.json()
        assert data_wrong["correct"] is False
        assert data_wrong["explanation"] is not None
        assert len(data_wrong["explanation"]) > 0
        assert data_wrong["correct_answer"] == correct_letter
        assert data_wrong["question_prompt"] is not None

        # 2. Turn 2: Select spell again (use resonance-burst to avoid cooldown) and submit CORRECT answer
        sel2 = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "resonance-burst"})
        assert sel2.status_code == 200
        t2 = sel2.json()["turn_id"]

        with SessionLocal() as db:
            gs = db.query(GameSession).filter(GameSession.id == sid).first()
            active_q2 = json.loads(gs.active_question_json)
            correct_letter2 = active_q2[2]

        ans_correct = client.post(
            "/api/battle/answer",
            headers=headers,
            json={"session_id": sid, "turn_id": t2, "answer": correct_letter2},
        )
        assert ans_correct.status_code == 200
        data_correct = ans_correct.json()
        assert data_correct["correct"] is True
        # Both outcomes must return explanation payload
        assert data_correct["explanation"] is not None
        assert len(data_correct["explanation"]) > 0
        assert data_correct["correct_answer"] == correct_letter2
        assert data_correct["question_prompt"] is not None

    def test_frontend_js_explanation_contract(self):
        """Verify frontend JavaScript adheres to explanation surfacing, staleness clearing, and defeat access."""
        js_path = ROOT_DIR / "static" / "js" / "main.js"
        assert js_path.exists()
        content = js_path.read_text()

        # 1. clearExplanation helper defined and resets state
        assert "function clearExplanation()" in content
        assert "window.lastExplanation = null;" in content

        # 2. showExplanation uses textContent
        assert "$('#explanation-question').textContent" in content
        assert "$('#explanation-answer').textContent" in content
        assert "$('#explanation-copy').textContent" in content

        # 3. Title adapts based on result.correct
        assert "result.correct ? 'WHY THIS ANSWER IS CORRECT' : 'WHY THIS ANSWER?'" in content

        # 4. showBattleModal supports secondaryAction
        assert "secondaryAction = null" in content
        assert "outcome-secondary" in content

        # 5. Correct answers store track-qualified explanation
        assert "if (r.explanation)" in content
        assert "window.lastExplanation = {" in content

        # 6. Defeat modal provides VIEW EXPLANATION secondary action
        assert "secondaryAction: r.explanation ? 'VIEW EXPLANATION' : null" in content

        # 7. render(s) clears stale explanation across track/session changes
        assert "window.lastExplanation.track_id !== s.track_id" in content

        # 8. Track switch and new game call clearExplanation()
        assert "clearExplanation();" in content
