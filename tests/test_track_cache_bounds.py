import time
import threading
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.settings import settings
from app.infrastructure.cache.track_cache import BoundedTrackCache
from app.api.deps import TRACK_BUNDLES, get_content_bundle
from app.infrastructure.database.engine import SessionLocal
from app.domain.content.loader import load_db_bundle, invalidate_bundle_cache
from scripts.ingest_questions_to_postgres import ingest_questions_data


@pytest.fixture(scope="module", autouse=True)
def seed_test_questions():
    """Ensure questions for track 'default' are ingested into the test database."""
    with SessionLocal() as db:
        ingest_questions_data(db, target_track_id="default", root_dir=settings.root_dir)


def test_bounded_track_cache_lru_eviction():
    """Verify LRU eviction when cache exceeds max_size."""
    cache = BoundedTrackCache(max_size=3, ttl_seconds=3600)
    cache["t1"] = "bundle_1"
    cache["t2"] = "bundle_2"
    cache["t3"] = "bundle_3"
    assert len(cache) == 3

    # Access t1 so t2 becomes the least recently used
    assert cache["t1"] == "bundle_1"

    # Insert t4 -> t2 should be evicted
    cache["t4"] = "bundle_4"
    assert len(cache) == 3
    assert "t1" in cache
    assert "t2" not in cache
    assert "t3" in cache
    assert "t4" in cache

    stats = cache.stats()
    assert stats["size"] == 3
    assert stats["max_size"] == 3
    assert stats["evictions"] >= 1
    assert "t2" not in stats["cached_tracks"]


def test_bounded_track_cache_ttl_expiration():
    """Verify expired items are evicted on access and iteration."""
    cache = BoundedTrackCache(max_size=5, ttl_seconds=1)
    cache["fast_expire"] = "quick_bundle"
    assert "fast_expire" in cache

    time.sleep(1.1)
    # After TTL, key should be expired
    assert "fast_expire" not in cache
    assert cache.get("fast_expire") is None
    assert len(cache) == 0
    assert cache.stats()["evictions"] >= 1


def test_bounded_track_cache_key_normalization():
    """Verify 'track:foo' and 'foo' refer to the exact same cache entry."""
    cache = BoundedTrackCache(max_size=4, ttl_seconds=3600)
    cache["track:default"] = "default_bundle"

    assert "default" in cache
    assert "track:default" in cache
    assert cache["default"] == "default_bundle"
    assert cache["track:default"] == "default_bundle"

    # Setting via bare key updates prefixed entry
    cache["default"] = "updated_bundle"
    assert cache["track:default"] == "updated_bundle"
    assert len(cache) == 1


def test_bounded_track_cache_dict_methods():
    """Verify dict-like compatibility: pop, clear, get, iteration, items."""
    cache = BoundedTrackCache(max_size=4, ttl_seconds=3600)
    cache["a"] = 1
    cache["b"] = 2

    assert cache.get("a") == 1
    assert cache.get("missing", 999) == 999

    assert cache.pop("a") == 1
    assert "a" not in cache
    assert cache.pop("missing", None) is None

    cache["c"] = 3
    keys = list(cache.keys())
    assert "b" in keys and "c" in keys

    items = list(cache.items())
    assert ("b", 2) in items

    cache.clear()
    assert len(cache) == 0


def test_bounded_track_cache_thread_safety():
    """Verify concurrent reads and writes do not corrupt cache state."""
    cache = BoundedTrackCache(max_size=5, ttl_seconds=3600)
    errors = []

    def worker(worker_id: int):
        try:
            for i in range(50):
                key = f"track_{worker_id}_{i % 10}"
                cache[key] = f"val_{i}"
                _ = cache.get(key)
                _ = len(cache)
                _ = cache.stats()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread errors encountered: {errors}"
    assert len(cache) <= 5, "Cache must strictly enforce max_size across threads"


def test_admin_system_config_includes_track_cache_stats():
    """Verify GET /api/v1/admin/system/config returns track_cache telemetry."""
    client = TestClient(app)
    login_res = client.post(
        "/api/v1/admin/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]

    res = client.get(
        "/api/v1/admin/system/config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "track_cache" in data
    cache_stats = data["track_cache"]
    assert "max_size" in cache_stats
    assert "size" in cache_stats
    assert "hits" in cache_stats
    assert "misses" in cache_stats
    assert "evictions" in cache_stats
    assert cache_stats["max_size"] >= 1


def test_optimized_load_db_bundle_parity():
    """Verify that optimized load_db_bundle column querying retains complete data parity."""
    with SessionLocal() as db:
        bundle = load_db_bundle("default", db=db, root_dir=settings.root_dir)
        assert bundle is not None
        assert len(bundle.questions) >= 1350
        assert len(bundle.chapters) == 27
        assert len(bundle.question_bank_by_chapter[1]) == 50

        # Check first question tuple format (prompt, choices, correct_answer)
        first_q = bundle.question_bank_by_chapter[1][0]
        assert len(first_q) == 3
        prompt, choices, correct = first_q
        assert isinstance(prompt, str) and len(prompt) > 0
        assert isinstance(choices, list) and len(choices) >= 2
        assert isinstance(correct, str) and len(correct) > 0
