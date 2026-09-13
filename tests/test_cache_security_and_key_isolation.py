import os
import zlib
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.settings import settings
from app.domain.content.entities import ContentBundle
from app.infrastructure.cache.shared_cache import (
    SharedTrackCacheManager,
    serialize_bundle,
    deserialize_bundle,
    mask_redis_url,
)
from app.domain.content.loader import load_track_bundle


def test_pickle_is_not_imported_or_used():
    """Verify pickle is completely absent from shared_cache module."""
    import app.infrastructure.cache.shared_cache as sc
    assert "pickle" not in dir(sc), "pickle module should not be imported in shared_cache"

    file_content = Path(sc.__file__).read_text(encoding="utf-8")
    assert "import pickle" not in file_content
    assert "pickle.loads" not in file_content
    assert "pickle.dumps" not in file_content


def test_schema_validated_bundle_serialization_round_trip():
    """Verify ContentBundle round-trip serialization maintains full fidelity, including tuple keys."""
    bundle = ContentBundle(
        source_name="app",
        chapters=[{"id": 1, "name": "Alkanes", "bosses": [("ogre", "Orbital Ogre", 100, 15, "Mini-Boss", "", "")]}],
        questions=[("What is methane?", ["CH4", "C2H6", "C3H8", "C4H10"], "CH4")],
        explanations={"What is methane?": "Methane is the simplest alkane."},
        question_bank_by_chapter={1: [("What is methane?", ["CH4", "C2H6"], "CH4")]},
        question_boss_bank={(1, "ogre"): [("What is methane?", ["CH4", "C2H6"], "CH4")]},
        boss_spell_values={(1, "ogre"): [15, 30, 50]},
        boss_images={"ogre": "ogre.png"},
        spell_values={(1, "ogre", "What is methane?"): [15, 30, 50]},
        spells={"spark": {"name": "Spark", "damage": 15}},
        json_spell_damage={1: 15, 2: 30},
        data_dir=Path("/tmp/data"),
        boss_dir=Path("/tmp/bosses"),
    )

    serialized = serialize_bundle(bundle)
    assert isinstance(serialized, bytes)

    # Decompress and verify it is pure JSON
    decompressed = zlib.decompress(serialized)
    parsed_json = json.loads(decompressed.decode("utf-8"))
    assert parsed_json["_type"] == "ContentBundle"
    assert parsed_json["version"] == 1

    # Deserialize back to ContentBundle
    restored = deserialize_bundle(serialized)
    assert isinstance(restored, ContentBundle)
    assert restored.source_name == "app"
    assert len(restored.chapters) == 1
    assert restored.questions[0] == ("What is methane?", ["CH4", "C2H6", "C3H8", "C4H10"], "CH4")
    assert restored.question_boss_bank[(1, "ogre")] == [("What is methane?", ["CH4", "C2H6"], "CH4")]
    assert restored.boss_spell_values[(1, "ogre")] == [15, 30, 50]
    assert restored.spell_values[(1, "ogre", "What is methane?")] == [15, 30, 50]
    assert restored.json_spell_damage[1] == 15


def test_malicious_pickle_payload_rejected_safely():
    """Verify an attacker-controlled pickle payload is rejected and cannot execute arbitrary code."""
    marker_file = Path("/tmp/antigravity_exploit_marker.txt")
    if marker_file.exists():
        marker_file.unlink()

    # Construct malicious pickle payload attempting RCE
    import pickle
    class Exploit:
        def __reduce__(self):
            return (os.system, (f"touch {marker_file}",))

    malicious_bytes = pickle.dumps(Exploit())
    compressed_exploit = zlib.compress(malicious_bytes)

    # Attempt deserialization through deserialize_bundle
    with pytest.raises((json.decoder.JSONDecodeError, UnicodeDecodeError, ValueError)):
        deserialize_bundle(compressed_exploit)

    # Verify exploit was NEVER executed
    assert not marker_file.exists(), "Arbitrary code execution occurred via pickle payload!"


def test_cache_key_isolation_custom_folder_vs_db():
    """Verify custom folder bundles and normal track bundles have strictly isolated cache keys."""
    manager = SharedTrackCacheManager(max_cached_tracks=10, ttl_seconds=3600)

    db_key = manager.format_cache_key("default", release_id="v1", source_identity="db")
    custom_key = manager.format_cache_key("default", release_id="v1", source_identity="custom_abc123")

    assert db_key == "default:db:v1"
    assert custom_key == "default:custom_abc123:v1"
    assert db_key != custom_key

    # Cache two different bundles under normal vs custom
    normal_bundle = {"track": "default", "type": "production_database"}
    custom_bundle = {"track": "default", "type": "user_custom_folder"}

    manager.set("default", "v1", normal_bundle, source_identity="db")
    manager.set("default", "v1", custom_bundle, source_identity="custom_abc123")

    # Lookups should be strictly separated
    assert manager.get("default", "v1", source_identity="db") == normal_bundle
    assert manager.get("default", "v1", source_identity="custom_abc123") == custom_bundle

    # Rebuild locks are also isolated
    lock_db = manager.get_track_rebuild_lock("default", source_identity="db")
    lock_custom = manager.get_track_rebuild_lock("default", source_identity="custom_abc123")
    assert lock_db is not lock_custom


def test_redis_url_credential_masking():
    """Verify Redis URLs with passwords are properly masked for logging."""
    unmasked_plain = "redis://default:mySecretPass123@redis-cluster.internal:6379/0"
    masked_plain = mask_redis_url(unmasked_plain)
    assert "mySecretPass123" not in masked_plain
    assert masked_plain == "redis://default:***@redis-cluster.internal:6379/0"

    unmasked_tls = "rediss://:SuperSecurePass@secure-cache.prod:6380/1"
    masked_tls = mask_redis_url(unmasked_tls)
    assert "SuperSecurePass" not in masked_tls
    assert masked_tls == "rediss://:***@secure-cache.prod:6380/1"


def test_redis_prefix_and_scan_iter_used_on_invalidation():
    """Verify Redis keys use prefix 'ob:' and invalidation uses scan_iter instead of blocking KEYS."""
    mock_redis = MagicMock()
    mock_redis.scan_iter.return_value = [b"ob:bundle:default:db:v1", b"ob:bundle:default:custom_1:v1"]

    manager = SharedTrackCacheManager(max_cached_tracks=5, ttl_seconds=3600, redis_key_prefix="ob:")
    manager._redis_client = mock_redis

    # Invalidate track
    manager.invalidate_track("default")

    # Verify scan_iter was called with proper pattern
    mock_redis.scan_iter.assert_called_once_with(match="ob:bundle:default:*", count=100)
    mock_redis.delete.assert_called_once_with(b"ob:bundle:default:db:v1", b"ob:bundle:default:custom_1:v1")
    # Verify blocking keys() was NOT called
    mock_redis.keys.assert_not_called()


def test_fallback_serves_validated_cache_when_db_unavailable():
    """Verify get_any_validated serves previously cached bundle before JSON fallback."""
    manager = SharedTrackCacheManager(max_cached_tracks=5, ttl_seconds=3600)
    cached_bundle = ContentBundle(
        source_name="database",
        chapters=[{"id": 1, "name": "Cached Chapter", "bosses": []}],
        questions=[("Cached Question?", ["A", "B"], "A")],
    )

    manager.set("test-track", "v1", cached_bundle, source_identity="db")

    result = manager.get_any_validated("test-track", source_identity="db")
    assert result is not None
    version, bundle = result
    assert version == "v1"
    assert bundle.questions[0][0] == "Cached Question?"
