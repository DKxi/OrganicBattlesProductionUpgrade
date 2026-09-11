import time
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.settings import settings
from app.infrastructure.database.engine import SessionLocal
from app.infrastructure.database.models import Question, ContentRelease
from app.infrastructure.cache.shared_cache import shared_track_cache
from scripts.ingest_questions_to_postgres import ingest_questions_data


@pytest.fixture(scope="module", autouse=True)
def seed_test_database():
    with SessionLocal() as db:
        ingest_questions_data(db, target_track_id="default", root_dir=settings.root_dir)


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


def test_reorder_scoped_by_track_chapter_and_boss(admin_client):
    """Verify reordering scoped to track, chapter, and boss works cleanly."""
    with SessionLocal() as db:
        qs = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        assert len(qs) >= 3
        orig_ids = [q.id for q in qs]
        base_order = min(q.order_index for q in qs)

    # Reverse order
    reversed_ids = list(reversed(orig_ids))
    resp = admin_client.post(
        "/api/v1/admin/tracks/default/chapters/1/bosses/orbital-ogre/reorder",
        json={"question_ids": reversed_ids},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["boss_slug"] == "orbital-ogre"
    assert data["reordered_count"] == len(reversed_ids)
    assert "release_id" in data

    # Verify new sequential order_index and updated_at
    with SessionLocal() as db:
        for idx, q_id in enumerate(reversed_ids):
            q = db.query(Question).filter(Question.id == q_id).first()
            assert q.order_index == base_order + idx
            assert q.updated_at > 0

    # Restore original order using chapter endpoint with boss_slug query parameter
    restore_resp = admin_client.post(
        "/api/v1/admin/tracks/default/chapters/1/reorder?boss_slug=orbital-ogre",
        json={"question_ids": orig_ids},
    )
    assert restore_resp.status_code == 200


def test_reject_duplicate_ids(admin_client):
    """Duplicate IDs in reorder request must be rejected with 400 Bad Request."""
    with SessionLocal() as db:
        qs = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        orig_ids = [q.id for q in qs]

    duplicate_ids = list(orig_ids)
    duplicate_ids[0] = duplicate_ids[1]  # duplicate ID

    resp = admin_client.post(
        "/api/v1/admin/tracks/default/chapters/1/bosses/orbital-ogre/reorder",
        json={"question_ids": duplicate_ids},
    )
    assert resp.status_code == 400
    assert "Duplicate question IDs are not permitted" in resp.json()["detail"]


def test_reject_unknown_ids(admin_client):
    """Unknown question IDs not belonging to the scoped boss must be rejected with 400."""
    with SessionLocal() as db:
        qs = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        orig_ids = [q.id for q in qs]

    unknown_ids = list(orig_ids)
    unknown_ids[0] = 99999999

    resp = admin_client.post(
        "/api/v1/admin/tracks/default/chapters/1/bosses/orbital-ogre/reorder",
        json={"question_ids": unknown_ids},
    )
    assert resp.status_code == 400
    assert "Unknown question ID(s)" in resp.json()["detail"]


def test_reject_partial_id_list(admin_client):
    """A partial ID list must be rejected with 400 to prevent collisions with untouched questions."""
    with SessionLocal() as db:
        qs = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        orig_ids = [q.id for q in qs]

    partial_ids = orig_ids[:2]  # Only 2 out of many

    resp = admin_client.post(
        "/api/v1/admin/tracks/default/chapters/1/bosses/orbital-ogre/reorder",
        json={"question_ids": partial_ids},
    )
    assert resp.status_code == 400
    assert "Incomplete question ID set" in resp.json()["detail"]


def test_explicit_move_before_and_move_after_operations(admin_client):
    """Verify explicit move-before and move-after operations produce expected reordering."""
    with SessionLocal() as db:
        qs = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        orig_ids = [q.id for q in qs]
        first_id = orig_ids[0]
        second_id = orig_ids[1]
        last_id = orig_ids[-1]

    # Move first_id AFTER last_id
    resp = admin_client.post(
        "/api/v1/admin/tracks/default/chapters/1/bosses/orbital-ogre/reorder",
        json={
            "move_question_id": first_id,
            "target_question_id": last_id,
            "position": "after",
        },
    )
    assert resp.status_code == 200

    with SessionLocal() as db:
        qs_after = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        assert qs_after[-1].id == first_id

    # Move first_id BEFORE second_id (restoring it back to top)
    resp = admin_client.post(
        "/api/v1/admin/tracks/default/chapters/1/bosses/orbital-ogre/reorder",
        json={
            "move_question_id": first_id,
            "target_question_id": second_id,
            "position": "before",
        },
    )
    assert resp.status_code == 200

    with SessionLocal() as db:
        qs_restored = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        assert [q.id for q in qs_restored] == orig_ids


def test_single_transaction_and_complete_rollback_on_failure(admin_client):
    """When an error occurs during reorder, the transaction must roll back completely leaving no negative or modified indexes."""
    with SessionLocal() as db:
        qs = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        orig_state = [(q.id, q.order_index, q.release_id) for q in qs]
        orig_ids = [q.id for q in qs]

    reversed_ids = list(reversed(orig_ids))

    # Simulate an error inside transaction during publish_release
    with patch("app.infrastructure.database.releases_repo.ReleasesRepository.publish_release", side_effect=RuntimeError("Simulated DB crash")):
        resp = admin_client.post(
            "/api/v1/admin/tracks/default/chapters/1/bosses/orbital-ogre/reorder",
            json={"question_ids": reversed_ids},
        )
        assert resp.status_code == 500
        assert "Reorder operation failed and was rolled back" in resp.json()["detail"]

    # Verify complete rollback: order_index, release_id, and no negative numbers
    with SessionLocal() as db:
        qs_post = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        post_state = [(q.id, q.order_index, q.release_id) for q in qs_post]
        assert post_state == orig_state
        # Assert no negative order indexes exist
        assert all(q.order_index >= 0 for q in qs_post)


def test_reorder_publishes_new_release_and_invalidates_cache(admin_client):
    """Verify that successful reordering publishes a new content release and invalidates shared cache."""
    with SessionLocal() as db:
        initial_active = (
            db.query(ContentRelease)
            .filter(ContentRelease.track_id == "default", ContentRelease.status == "published")
            .order_by(ContentRelease.version.desc())
            .first()
        )
        initial_version = initial_active.version if initial_active else 1

        qs = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        orig_ids = [q.id for q in qs]

    # Warm cache first
    dummy_bundle = type("DummyBundle", (), {"track_id": "default"})()
    shared_track_cache.set(track_id="default", release_id=f"default_v{initial_version}", bundle=dummy_bundle)
    assert shared_track_cache.get("default", f"default_v{initial_version}") is not None

    # Perform reorder
    reordered_ids = list(orig_ids)
    reordered_ids[0], reordered_ids[1] = reordered_ids[1], reordered_ids[0]

    resp = admin_client.post(
        "/api/v1/admin/tracks/default/chapters/1/bosses/orbital-ogre/reorder",
        json={"question_ids": reordered_ids},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_version"] > initial_version

    # Verify cache invalidated
    assert shared_track_cache.get("default", f"default_v{initial_version}") is None

    # Verify new release marked published in DB
    with SessionLocal() as db:
        new_active = (
            db.query(ContentRelease)
            .filter(ContentRelease.track_id == "default", ContentRelease.status == "published")
            .order_by(ContentRelease.version.desc())
            .first()
        )
        assert new_active.version == data["new_version"]
        assert new_active.id == data["release_id"]
