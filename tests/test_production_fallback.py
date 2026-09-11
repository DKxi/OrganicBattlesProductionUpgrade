from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.domain.content.entities import ContentBundle
from app.domain.content.loader import load_track_bundle
from app.infrastructure.cache.shared_cache import shared_track_cache
from app.main import app
from app.settings import settings

ROOT_DIR = Path(__file__).parents[1]
client = TestClient(app)


@pytest.fixture
def admin_client():
    c = TestClient(app)
    login_res = c.post(
        "/api/v1/admin/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def test_db_unavailable_no_cache_and_fallback_disabled_raises_503():
    """When DB fails and no cached content exists and ALLOW_JSON_FALLBACK is False, loader must raise 503."""
    with patch.object(settings, "allow_json_fallback", False):
        shared_track_cache.clear()
        
        # Simulate DB engine failure when attempting to load bundle from database
        with patch("app.domain.content.loader.load_db_bundle", side_effect=OperationalError("connection refused", {}, Exception("DB down"))):
            with pytest.raises(HTTPException) as exc_info:
                load_track_bundle(ROOT_DIR, "nonexistent_uncached_track")
            
            assert exc_info.value.status_code == 503
            assert "Database is unavailable and no validated cache exists" in exc_info.value.detail


def test_db_unavailable_validated_cache_exists_serves_degraded():
    """When DB fails but a validated cache exists, loader must serve cache and record degraded status."""
    dummy_bundle = ContentBundle(source_name="shared_cache")
    shared_track_cache.clear()
    shared_track_cache.set(track_id="alkanes", release_id="rel_mock_v1", bundle=dummy_bundle)
    
    with patch.object(settings, "allow_json_fallback", False):
        with patch("app.domain.content.loader.load_db_bundle", side_effect=OperationalError("connection refused", {}, Exception("DB down"))):
            bundle = load_track_bundle(ROOT_DIR, "alkanes")
            assert bundle.source_name == "shared_cache"
            
            # Check recorded status
            status = shared_track_cache.get_content_status("alkanes")
            assert status["status"] == "degraded"
            assert status["source"] == "cache"
            assert status["release_id"] == "rel_mock_v1"
            assert shared_track_cache.is_degraded() is True


def test_db_unavailable_json_fallback_allowed_serves_json():
    """When DB fails and ALLOW_JSON_FALLBACK is True, loader falls back to filesystem JSON and records fallback status."""
    with patch.object(settings, "allow_json_fallback", True):
        shared_track_cache.clear()
        
        with patch("app.domain.content.loader.load_db_bundle", side_effect=OperationalError("connection refused", {}, Exception("DB down"))):
            bundle = load_track_bundle(ROOT_DIR, "alkanes")
            assert len(bundle.questions) > 0
            
            status = shared_track_cache.get_content_status("alkanes")
            assert status["source"] == "filesystem_json"
            assert status["fallback_status"] == "json_fallback"


def test_health_ready_probe_all_states():
    """Test /health/ready and /readyz probe behavior for ready, degraded, and unavailable."""
    # 1. Healthy state
    shared_track_cache.clear()
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database"] == "available"

    # 2. Degraded state: DB down but validated cache exists
    dummy_bundle = ContentBundle(source_name="shared_cache")
    shared_track_cache.set(track_id="alkanes", release_id="rel_mock_v1", bundle=dummy_bundle)

    with patch("sqlalchemy.orm.Session.execute", side_effect=Exception("DB connection down")):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["database"] == "unavailable"
        assert data["fallback_status"] == "cache_degraded"

        readyz_resp = client.get("/readyz")
        assert readyz_resp.status_code == 200
        assert readyz_resp.json()["status"] == "degraded"

    # 3. Unavailable state: DB down and no cache exists
    shared_track_cache.clear()
    with patch("sqlalchemy.orm.Session.execute", side_effect=Exception("DB connection down")):
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unavailable"
        assert data["database"] == "unavailable"

        readyz_resp = client.get("/readyz")
        assert readyz_resp.status_code == 503
        assert readyz_resp.json()["status"] == "unavailable"


def test_admin_system_config_includes_health_metrics(admin_client):
    """Verify /admin/system/config reports fallback and health metrics."""
    resp = admin_client.get("/api/v1/admin/system/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "health" in data
    health = data["health"]
    assert "allow_json_fallback" in health
    assert "has_cached_content" in health
    assert "degraded_mode" in health
    assert "content_sources" in health
