import time
import pytest
from starlette.testclient import TestClient
from sqlalchemy import inspect

from app.main import app
from app.settings import settings
from app.infrastructure.database.engine import engine, SessionLocal, ensure_db_schema
from app.infrastructure.database.models import (
    Boss,
    BossQuestionAssignment,
    PlayerQuestionProgress,
    AnswerAttempt,
    Question,
    User,
    GameSession,
)
from app.infrastructure.database.progress_repo import ProgressRepository
from app.infrastructure.database.bosses_repo import BossesRepository


@pytest.fixture
def admin_client():
    client = TestClient(app)
    login_res = client.post(
        "/api/v1/admin/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_long_term_tables_exist():
    """Verify all 4 new long-term schema tables are created in the database."""
    ensure_db_schema()
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "OB_bosses" in tables
    assert "OB_boss_question_assignments" in tables
    assert "OB_player_question_progress" in tables
    assert "OB_answer_attempts" in tables


def test_boss_model_and_question_assignment():
    """Verify Boss and BossQuestionAssignment model relationships and constraints."""
    with SessionLocal() as db:
        boss_repo = BossesRepository(db)
        boss = boss_repo.create_or_update_boss(
            boss_id="test_boss_alkane",
            slug="alkane_guardian",
            track_id="organic1",
            chapter=1,
            order_index=99,
            name="Alkane Guardian",
            image_file="alkane_guardian.png",
            health=120,
            element="Alkanes",
            strategy={"burn_vulnerable": True},
        )
        db.commit()

        # Fetch or insert a question for organic1
        q = db.query(Question).filter(Question.track_id == "organic1").first()
        if not q:
            q = Question(
                track_id="organic1",
                raw_id="q_b1",
                chapter=1,
                chapter_title="Chapter 1",
                boss_name="Alkane Guardian",
                boss_slug="alkane_guardian",
                order_index=1,
                topic="Alkanes",
                difficulty="Easy",
                prompt="What is methane?",
                options_json=[{"label": "A", "text": "CH4"}, {"label": "B", "text": "C2H6"}],
                correct_option="A",
                correct_answer="CH4",
                explanation="Methane is CH4",
            )
            db.add(q)
            db.commit()

        assignment = boss_repo.assign_question_to_boss(
            boss_id=boss.id,
            question_id=q.id,
            track_id="organic1",
            order_index=1,
            weight=1.5,
        )
        db.commit()

        # Verify relationships
        reloaded_boss = boss_repo.get_boss("test_boss_alkane")
        assert reloaded_boss is not None
        assert len(reloaded_boss.question_assignments) >= 1
        assert reloaded_boss.question_assignments[0].question_id == q.id
        assert reloaded_boss.question_assignments[0].weight == 1.5


def test_player_question_progress_sm2_algorithm():
    """Verify SM-2 spaced repetition calculations on consecutive correct answers and incorrect reset."""
    with SessionLocal() as db:
        repo = ProgressRepository(db)
        user_id = f"test_learner_{int(time.time())}"
        q_id = 9999

        # Attempt 1: Correct
        p1 = repo.update_progress(user_id=user_id, question_id=q_id, track_id="organic1", is_correct=True)
        assert p1.repetitions == 1
        assert p1.interval_days == 1.0
        assert p1.mastery_score == 0.25
        assert p1.total_attempts == 1
        assert p1.correct_attempts == 1
        assert p1.next_review_at > int(time.time())

        # Attempt 2: Correct
        p2 = repo.update_progress(user_id=user_id, question_id=q_id, track_id="organic1", is_correct=True)
        assert p2.repetitions == 2
        assert p2.interval_days == 6.0
        assert p2.mastery_score == 0.50
        assert p2.total_attempts == 2
        assert p2.correct_attempts == 2

        # Attempt 3: Correct
        p3 = repo.update_progress(user_id=user_id, question_id=q_id, track_id="organic1", is_correct=True)
        assert p3.repetitions == 3
        assert p3.interval_days > 6.0
        assert p3.mastery_score == 0.75

        # Attempt 4: Incorrect (streak reset)
        p4 = repo.update_progress(user_id=user_id, question_id=q_id, track_id="organic1", is_correct=False)
        assert p4.repetitions == 0
        assert p4.interval_days == 1.0
        assert p4.mastery_score < 0.75
        assert p4.total_attempts == 4
        assert p4.correct_attempts == 3

        db.commit()


def test_answer_attempt_recording():
    """Verify recording immutable answer attempts."""
    with SessionLocal() as db:
        q = db.query(Question).first()
        if not q:
            q = Question(
                track_id="organic1",
                raw_id="q_att_1",
                chapter=1,
                chapter_title="Chapter 1",
                boss_name="Alkane Guardian",
                boss_slug="alkane_guardian",
                order_index=1,
                topic="Alkanes",
                difficulty="Easy",
                prompt="What is ethane?",
                options_json=[{"label": "A", "text": "C2H6"}, {"label": "B", "text": "CH4"}],
                correct_option="A",
                correct_answer="C2H6",
                explanation="Ethane is C2H6",
            )
            db.add(q)
            db.commit()

        repo = ProgressRepository(db)
        att = repo.record_attempt(
            user_id="research_user_1",
            question_id=q.id,
            track_id="organic1",
            boss_slug="methane_elemental",
            selected_option="B",
            is_correct=True,
            damage_dealt=35,
            damage_taken=0,
            time_taken_ms=1450,
        )
        repo.update_progress(
            user_id="research_user_1",
            question_id=q.id,
            track_id="organic1",
            is_correct=True,
        )
        db.commit()

        reloaded = db.query(AnswerAttempt).filter(AnswerAttempt.id == att.id).first()
        assert reloaded is not None
        assert reloaded.user_id == "research_user_1"
        assert reloaded.boss_slug == "methane_elemental"
        assert reloaded.is_correct == 1
        assert reloaded.damage_dealt == 35
        assert reloaded.time_taken_ms == 1450


def test_battle_answer_creates_attempt_and_progress(admin_client, monkeypatch):
    """Verify combat turn execution writes to OB_answer_attempts and updates OB_player_question_progress."""
    client = TestClient(app)
    username = f"player_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "Password123!"

    codes = []
    def mock_send(email_addr, uname, code):
        codes.append(code)

    import app as app_mod
    monkeypatch.setattr(app_mod, "send_verification_email", mock_send)

    signup_res = client.post("/api/auth/signup", json={
        "email": email,
        "username": username,
        "password": password
    })
    assert signup_res.status_code == 200
    assert len(codes) > 0
    code = codes[0]

    verify_res = client.post("/api/auth/verify", json={"code": code})
    assert verify_res.status_code == 200
    token = verify_res.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    # Start battle session
    start_res = client.post("/api/game/new", headers={"Authorization": f"Bearer {token}"})
    assert start_res.status_code == 200
    sid = start_res.json()["session_id"]
    client.post(
        "/api/avatar/finalize",
        params={"session_id": sid},
        json={'body':'arc','skin':'warm','hair':'nebula','outfit':'coat','accessory':'goggles','aura':'teal'},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Select spell
    spell_res = client.post(
        "/api/battle/select-spell",
        params={"session_id": sid},
        json={"spell_id": "fire-spark"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert spell_res.status_code == 200
    spell_data = spell_res.json()
    turn_id = spell_data["turn_id"]
    choices = spell_data["question"]["choices"]
    prompt = spell_data["question"]["prompt"]

    # Ensure matching question row exists in DB for this prompt
    with SessionLocal() as db:
        q = db.query(Question).filter(Question.prompt == prompt).first()
        if not q:
            q = Question(
                track_id="default",
                raw_id="q_battle_sync",
                chapter=1,
                chapter_title="Chapter 1",
                boss_name="Boss 1",
                boss_slug="boss_1",
                order_index=1,
                topic="Alkanes",
                difficulty="Easy",
                prompt=prompt,
                options_json=[{"label": "A", "text": choices[0]}, {"label": "B", "text": choices[1]}],
                correct_option="A",
                correct_answer=choices[0],
                explanation="Correct explanation",
            )
            db.add(q)
            db.commit()

    # Submit answer
    answer_res = client.post(
        "/api/battle/answer",
        params={"session_id": sid},
        json={"turn_id": turn_id, "answer": choices[0]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert answer_res.status_code == 200

    # Check that an answer attempt and player progress were recorded
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None

        attempt = db.query(AnswerAttempt).filter(AnswerAttempt.user_id == user.id).first()
        assert attempt is not None
        assert attempt.selected_option == choices[0]

        progress = db.query(PlayerQuestionProgress).filter(PlayerQuestionProgress.user_id == user.id).first()
        assert progress is not None
        assert progress.total_attempts >= 1


def test_admin_analytics_endpoints(admin_client):
    """Verify admin learning analytics endpoints."""
    # 1. Overview analytics
    overview_res = admin_client.get("/api/v1/admin/analytics/overview")
    assert overview_res.status_code == 200
    data = overview_res.json()
    assert "total_attempts" in data
    assert "overall_accuracy" in data
    assert "unique_players" in data
    assert "struggling_questions" in data
    assert data["total_attempts"] >= 1

    # 2. Question detailed analytics
    with SessionLocal() as db:
        attempt = db.query(AnswerAttempt).first()
        assert attempt is not None
        target_q_id = attempt.question_id

    q_res = admin_client.get(f"/api/v1/admin/analytics/questions/{target_q_id}")
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["question_id"] == target_q_id
    assert "accuracy" in q_data
    assert "option_distribution" in q_data

    # 3. User mastery analytics
    u_res = admin_client.get(f"/api/v1/admin/analytics/users/{attempt.user_id}/mastery")
    assert u_res.status_code == 200
    u_data = u_res.json()
    assert "summary" in u_data
    assert u_data["summary"]["total_tracked"] >= 1

    # Clean up test question and invalidate cache so later tests are unaffected
    with SessionLocal() as db:
        db.query(Question).filter(Question.raw_id == "q_battle_sync").delete()
        db.commit()
    from app.infrastructure.cache.shared_cache import shared_track_cache
    shared_track_cache.invalidate_track("default")
    from app.api.deps import TRACK_BUNDLES
    TRACK_BUNDLES.clear()


def test_sync_bosses_from_questions():
    """Verify that sync_bosses_from_questions extracts distinct bosses and populates OB_bosses and assignments."""
    from app.infrastructure.database.models import Track
    try:
        with SessionLocal() as db:
            # Create test track if not present
            test_track = db.query(Track).filter(Track.id == "sync_test_track").first()
            if not test_track:
                test_track = Track(
                    id="sync_test_track",
                    curriculum_id="foundational",
                    title="Sync Test Track",
                    detail="Testing boss sync",
                    data_folder="data/tracks/sync",
                    boss_folder="data/tracks/sync/bosses",
                    questions=2,
                    chapters=1,
                )
                db.add(test_track)
                db.commit()

            # Insert two questions with distinct bosses in chapter 1
            q1 = Question(
                track_id="sync_test_track",
                raw_id="sync_q1",
                chapter=1,
                chapter_title="Sync Chapter 1",
                boss_name="Sync Ogre",
                boss_slug="sync-ogre",
                order_index=1,
                topic="Bonding",
                difficulty="Easy",
                prompt="Question 1 for Sync Ogre",
                options_json=[{"label": "A", "text": "Ans A"}, {"label": "B", "text": "Ans B"}],
                correct_option="A",
                correct_answer="Ans A",
                explanation="Explanation 1",
                health_json=[100],
                images_json=["sync-ogre.png"],
            )
            q2 = Question(
                track_id="sync_test_track",
                raw_id="sync_q2",
                chapter=1,
                chapter_title="Sync Chapter 1",
                boss_name="Sync Dragon",
                boss_slug="sync-dragon",
                order_index=2,
                topic="Kinetics",
                difficulty="Medium",
                prompt="Question 2 for Sync Dragon",
                options_json=[{"label": "A", "text": "Ans A"}, {"label": "B", "text": "Ans B"}],
                correct_option="A",
                correct_answer="Ans A",
                explanation="Explanation 2",
                health_json=[150],
                images_json=["sync-dragon.png"],
            )
            db.add_all([q1, q2])
            db.commit()

            boss_repo = BossesRepository(db)
            stats = boss_repo.sync_bosses_from_questions(track_id="sync_test_track")
            assert stats["bosses"] >= 2
            assert stats["assignments"] >= 2

            # Verify bosses created in OB_bosses
            bosses = boss_repo.get_bosses_for_track("sync_test_track", chapter=1)
            assert len(bosses) == 2
            slugs = [b.slug for b in bosses]
            assert "sync-ogre" in slugs
            assert "sync-dragon" in slugs

            ogre = boss_repo.get_boss_by_slug("sync_test_track", "sync-ogre")
            assert ogre.name == "Sync Ogre"
            assert ogre.health == 100
            assert ogre.image_file == "sync-ogre.png"
            assert len(ogre.question_assignments) >= 1

            dragon = boss_repo.get_boss_by_slug("sync_test_track", "sync-dragon")
            assert dragon.name == "Sync Dragon"
            assert dragon.health == 150
            assert dragon.image_file == "sync-dragon.png"
            assert len(dragon.question_assignments) >= 1

            # Test idempotency (syncing again shouldn't fail or duplicate)
            stats_repeat = boss_repo.sync_bosses_from_questions(track_id="sync_test_track")
            assert stats_repeat["bosses"] >= 2
            assert len(boss_repo.get_bosses_for_track("sync_test_track", chapter=1)) == 2
    finally:
        with SessionLocal() as clean_db:
            clean_db.query(BossQuestionAssignment).filter(BossQuestionAssignment.track_id == "sync_test_track").delete()
            clean_db.query(Boss).filter(Boss.track_id == "sync_test_track").delete()
            clean_db.query(Question).filter(Question.track_id == "sync_test_track").delete()
            clean_db.query(Track).filter(Track.id == "sync_test_track").delete()
            clean_db.commit()

