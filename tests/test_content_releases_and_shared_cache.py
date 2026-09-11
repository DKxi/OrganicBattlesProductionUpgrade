import json
import time
import threading
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.settings import settings
from app.infrastructure.database.engine import SessionLocal
from app.infrastructure.database.models import Question, Track
from app.infrastructure.database.releases_repo import ReleasesRepository
from app.infrastructure.cache.shared_cache import SharedTrackCacheManager, shared_track_cache
from app.domain.content.loader import load_db_bundle
from scripts.ingest_questions_to_postgres import ingest_questions_data


@pytest.fixture(scope="module", autouse=True)
def seed_test_questions():
    """Ensure questions for track 'default' are ingested and active in the test database."""
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


def test_atomic_content_releases_lifecycle():
    """Test full atomic draft -> validate -> publish -> rollback lifecycle."""
    with SessionLocal() as db:
        repo = ReleasesRepository(db)

        # 1. Create a draft release
        draft = repo.create_draft_release("default", checksum="abc123sha")
        assert draft.status == "draft"
        assert draft.version > 0
        assert draft.published_at is None

        # 2. Verify draft release is not the active release
        active = repo.get_active_release("default")
        assert active is not None
        assert active.id != draft.id
        assert active.status == "published"

        # 3. Insert a question linked to this draft release
        test_q = Question(
            track_id="default",
            release_id=draft.id,
            raw_id="test_atomic_q1",
            chapter=1,
            chapter_title="Chapter 1",
            boss_name="Test Boss",
            boss_slug="test-boss",
            order_index=9999,
            topic="Atomic Ingestion",
            difficulty="Easy",
            question_type="Multiple Choice",
            prompt="Atomic release test prompt?",
            options_json=json.dumps([{"label": "A", "text": "Correct"}]),
            correct_option="A",
            correct_answer="Correct",
            explanation="Test explanation",
            spells_json="[20, 30, 45]",
            health_json="[100]",
            images_json="[]",
        )
        db.add(test_q)
        db.commit()

        # 4. While draft, load_db_bundle must NOT return this draft question
        bundle_before = load_db_bundle("default", db=db, root_dir=settings.root_dir)
        prompts_before = [q[0] for q in bundle_before.questions]
        assert "Atomic release test prompt?" not in prompts_before

        # 5. Atomically publish the draft release
        published = repo.publish_release(draft.id)
        assert published.status == "published"
        assert published.published_at is not None

        # 6. Now load_db_bundle with the newly published release contains the question
        bundle_after = load_db_bundle("default", db=db, root_dir=settings.root_dir, release_id=published.id)
        prompts_after = [q[0] for q in bundle_after.questions]
        assert "Atomic release test prompt?" in prompts_after

        # 7. Roll back to prior release version (e.g. v1)
        rolled_back = repo.rollback_to_release("default", target_version=1)
        assert rolled_back.version == 1
        assert rolled_back.status == "published"

        # Verify draft is now archived
        db.refresh(published)
        assert published.status == "archived"


def test_shared_cache_versioning_and_telemetry():
    """Verify caching by (track_id, release_id), hit ratio, bundle size, and load duration."""
    manager = SharedTrackCacheManager(max_cached_tracks=3, ttl_seconds=3600)

    # Initial stats
    stats = manager.stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_ratio"] == 0.0

    # Miss lookup
    res = manager.get("default", "v1")
    assert res is None
    assert manager.stats()["misses"] == 1

    # Populate bundle
    mock_bundle = {"name": "default_bundle", "questions": ["q1", "q2"]}
    manager.set("default", "v1", mock_bundle, load_duration_ms=45.2)

    # Hit lookup
    hit_res = manager.get("default", "v1")
    assert hit_res == mock_bundle
    stats = manager.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_ratio"] == 0.5
    assert stats["load_durations_ms"]["default"] == 45.2
    assert stats["bundle_sizes_bytes"]["default"] > 0

    # Version mismatch lookup (e.g. v2) should miss and not return v1
    v2_res = manager.get("default", "v2")
    assert v2_res is None


def test_shared_cache_rebuild_locking():
    """Verify rebuild locking prevents duplicate simultaneous bundle builds."""
    manager = SharedTrackCacheManager(max_cached_tracks=3, ttl_seconds=3600)
    build_count = 0
    build_count_lock = threading.Lock()

    def simulate_concurrent_loader():
        nonlocal build_count
        lock = manager.get_track_rebuild_lock("track_lock_test")
        with lock:
            val = manager.get("track_lock_test", "v1")
            if val is None:
                # Simulate heavy DB query / bundle build
                time.sleep(0.05)
                with build_count_lock:
                    build_count += 1
                manager.set("track_lock_test", "v1", "built_bundle", load_duration_ms=50.0)

    threads = [threading.Thread(target=simulate_concurrent_loader) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Even with 5 concurrent threads, the bundle should only be built ONCE
    assert build_count == 1
    assert manager.get("track_lock_test", "v1") == "built_bundle"


def test_cache_warming_utility():
    """Verify warm_tracks preloads popular tracks."""
    res = shared_track_cache.warm_tracks(settings.root_dir, ["default"])
    assert "default" in res
    assert res["default"]["status"] in ("warmed", "already_cached")
    assert "release_id" in res["default"]


def test_admin_releases_endpoints(admin_client):
    """Verify admin releases list, rollback endpoint, and cache warm endpoint."""
    # 1. GET releases for track
    res = admin_client.get("/api/v1/admin/tracks/default/releases")
    assert res.status_code == 200
    data = res.json()
    assert "track_id" in data
    assert "releases" in data
    assert len(data["releases"]) >= 1

    # 2. POST /admin/system/cache/warm
    warm_res = admin_client.post("/api/v1/admin/system/cache/warm?tracks=default")
    assert warm_res.status_code == 200
    warm_data = warm_res.json()
    assert warm_data["status"] == "ok"
    assert "results" in warm_data
    assert "stats" in warm_data

    # 3. GET /admin/system/config includes rich telemetry
    cfg_res = admin_client.get("/api/v1/admin/system/config")
    assert cfg_res.status_code == 200
    cfg = cfg_res.json()
    assert "track_cache" in cfg
    cache_telemetry = cfg["track_cache"]
    assert "hit_ratio" in cache_telemetry
    assert "hits" in cache_telemetry
    assert "misses" in cache_telemetry
    assert "load_durations_ms" in cache_telemetry
    assert "bundle_sizes_bytes" in cache_telemetry
