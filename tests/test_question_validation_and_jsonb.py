import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.database.engine import SessionLocal
from app.infrastructure.database.models import Question, Track, Curriculum
from app.api.deps import auth_admin
from app.domain.content.validator import validate_question_payload, QuestionValidationError
from app.domain.content.loader import load_db_bundle
from app.settings import settings


def test_validator_at_least_two_choices():
    with pytest.raises(QuestionValidationError, match="at least two choices"):
        validate_question_payload(
            options=[{"label": "A", "text": "Only one"}],
            correct_option="A",
            correct_answer="Only one",
        )


def test_validator_unique_and_valid_option_labels():
    # Duplicate label
    with pytest.raises(QuestionValidationError, match="duplicated"):
        validate_question_payload(
            options=[
                {"label": "A", "text": "Choice 1"},
                {"label": "A", "text": "Choice 2"},
            ],
            correct_option="A",
            correct_answer="Choice 1",
        )

    # Empty label
    with pytest.raises(QuestionValidationError, match="empty label"):
        validate_question_payload(
            options=[
                {"label": "", "text": "Choice 1"},
                {"label": "B", "text": "Choice 2"},
            ],
            correct_option="B",
            correct_answer="Choice 2",
        )

    # Empty choice text
    with pytest.raises(QuestionValidationError, match="empty choice text"):
        validate_question_payload(
            options=[
                {"label": "A", "text": "   "},
                {"label": "B", "text": "Choice 2"},
            ],
            correct_option="B",
            correct_answer="Choice 2",
        )


def test_validator_correct_option_and_answer_correspondence():
    # Correct option not in options
    with pytest.raises(QuestionValidationError, match="matched 0 options"):
        validate_question_payload(
            options=[
                {"label": "A", "text": "Choice 1"},
                {"label": "B", "text": "Choice 2"},
            ],
            correct_option="C",
            correct_answer="Choice 1",
        )

    # Correct option label text does not match correct_answer
    with pytest.raises(QuestionValidationError, match="does not correspond to correct_answer"):
        validate_question_payload(
            options=[
                {"label": "A", "text": "Choice 1"},
                {"label": "B", "text": "Choice 2"},
            ],
            correct_option="A",
            correct_answer="Choice 2",
        )


def test_validator_positive_health_and_spells():
    valid_opts = [
        {"label": "A", "text": "Alpha"},
        {"label": "B", "text": "Beta"},
    ]

    # Non-positive spell
    with pytest.raises(QuestionValidationError, match="positive numbers"):
        validate_question_payload(
            options=valid_opts,
            correct_option="A",
            correct_answer="Alpha",
            spells=[20, 0, 45],
        )

    # Negative health
    with pytest.raises(QuestionValidationError, match="positive numbers"):
        validate_question_payload(
            options=valid_opts,
            correct_option="A",
            correct_answer="Alpha",
            health=[-10],
        )


def test_validator_safe_and_recognized_images():
    valid_opts = [
        {"label": "A", "text": "Alpha"},
        {"label": "B", "text": "Beta"},
    ]

    # Path traversal
    with pytest.raises(QuestionValidationError, match="Path traversal"):
        validate_question_payload(
            options=valid_opts,
            correct_option="A",
            correct_answer="Alpha",
            images=["../secret.png"],
        )

    # Invalid extension
    with pytest.raises(QuestionValidationError, match="recognized image format"):
        validate_question_payload(
            options=valid_opts,
            correct_option="A",
            correct_answer="Alpha",
            images=["malicious.sh"],
        )

    # Valid images with unicode characters
    opts, c_opt, c_ans, sp, hl, imgs = validate_question_payload(
        options=valid_opts,
        correct_option="A",
        correct_answer="Alpha",
        images=["hückel-hexer.png", "diels–alder-dragon.png", "boss.webp"],
    )
    assert len(imgs) == 3
    assert imgs[0] == "hückel-hexer.png"


def test_question_json_model_persistence():
    with SessionLocal() as db:
        q = Question(
            track_id="default",
            raw_id="json_test_q1",
            chapter=1,
            chapter_title="Chapter 1",
            boss_name="JSON Boss",
            boss_slug="json-boss",
            order_index=8888,
            topic="JSON Validation",
            difficulty="Medium",
            question_type="Multiple Choice",
            prompt="Persistence test prompt?",
            options_json=[
                {"label": "A", "text": "Option A"},
                {"label": "B", "text": "Option B"},
            ],
            correct_option="A",
            correct_answer="Option A",
            explanation="Validated JSON persistence",
            spells_json=[25, 35, 50],
            health_json=[120],
            images_json=["json-boss.png"],
        )
        db.add(q)
        db.commit()
        db.refresh(q)

        assert isinstance(q.options_json, list)
        assert len(q.options_json) == 2
        assert q.options_json[0]["label"] == "A"
        assert isinstance(q.spells_json, list)
        assert q.spells_json == [25, 35, 50]
        assert isinstance(q.health_json, list)
        assert q.health_json == [120]
        assert isinstance(q.images_json, list)
        assert q.images_json == ["json-boss.png"]

        # Clean up
        db.delete(q)
        db.commit()


def test_admin_api_rejects_raw_json_strings_and_validates():
    with SessionLocal() as db:
        q = Question(
            track_id="default",
            raw_id="admin_test_q1",
            chapter=1,
            chapter_title="Chapter 1",
            boss_name="Admin Test Boss",
            boss_slug="admin-test-boss",
            order_index=9998,
            topic="Admin Validation",
            difficulty="Medium",
            question_type="Multiple Choice",
            prompt="Initial prompt?",
            options_json=[
                {"label": "A", "text": "Choice A"},
                {"label": "B", "text": "Choice B"},
            ],
            correct_option="A",
            correct_answer="Choice A",
            explanation="Explanation",
            spells_json=[20, 30, 45],
            health_json=[100],
            images_json=["admin-boss.png"],
        )
        db.add(q)
        db.commit()
        db.refresh(q)
        qid = q.id

    app.dependency_overrides[auth_admin] = lambda: {"username": "admin", "is_admin": True}
    try:
        client = TestClient(app)

        # First fetch question ID from default track
        res = client.get(f"/api/v1/admin/questions/{qid}")
        assert res.status_code == 200
        item = res.json()
        assert item["id"] == qid

        # 1. Raw string options_json should be rejected (extra field forbidden)
        res_bad_str = client.put(
            f"/api/v1/admin/questions/{qid}",
            json={"options_json": '[{"label": "A", "text": "Raw"}]'},
        )
        assert res_bad_str.status_code == 422

        # 2. Raw string spells_json should be rejected (extra field forbidden)
        res_bad_spells = client.put(
            f"/api/v1/admin/questions/{qid}",
            json={"spells_json": "[10, 20]"},
        )
        assert res_bad_spells.status_code == 422

        # 3. Invalid choices schema (fewer than 2 options) should return 400
        res_single = client.put(
            f"/api/v1/admin/questions/{qid}",
            json={
                "options": [{"label": "A", "text": "Only One"}],
                "correct_option": "A",
                "correct_answer": "Only One",
            },
        )
        assert res_single.status_code == 400
        assert "at least two choices" in res_single.json()["detail"]

        # 4. Mismatched correct_option text and correct_answer should return 400
        res_mismatch = client.put(
            f"/api/v1/admin/questions/{qid}",
            json={
                "options": [
                    {"label": "A", "text": "Correct Text"},
                    {"label": "B", "text": "Wrong Text"},
                ],
                "correct_option": "A",
                "correct_answer": "Wrong Text",
            },
        )
        assert res_mismatch.status_code == 400
        assert "does not correspond to correct_answer" in res_mismatch.json()["detail"]

        # 5. Valid update succeeds
        valid_update = {
            "prompt": "Updated Prompt?",
            "options": [
                {"label": "A", "text": "Updated A"},
                {"label": "B", "text": "Updated B"},
            ],
            "correct_option": "A",
            "correct_answer": "Updated A",
            "spells": [20, 30, 45],
            "health": [100],
        }
        res_ok = client.put(
            f"/api/v1/admin/questions/{qid}",
            json=valid_update,
        )
        assert res_ok.status_code == 200
        assert res_ok.json()["status"] == "ok"
    finally:
        app.dependency_overrides.clear()
        with SessionLocal() as db:
            to_delete = db.query(Question).filter(Question.id == qid).first()
            if to_delete:
                db.delete(to_delete)
                db.commit()
