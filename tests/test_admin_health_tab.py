import pytest
from starlette.testclient import TestClient
from app.main import app
from app.settings import settings


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


def test_admin_system_health_requires_auth():
    """Unauthenticated request to /api/v1/admin/system/health must be rejected with 401."""
    client = TestClient(app)
    res = client.get("/api/v1/admin/system/health")
    assert res.status_code == 401


def test_admin_system_health_authorized(admin_client):
    """Authenticated admin request must return 200 and comprehensive diagnostic payload."""
    res = admin_client.get("/api/v1/admin/system/health")
    assert res.status_code == 200
    data = res.json()

    # Verdict and timestamp
    assert data["verdict"] in ["HEALTHY", "DEGRADED", "CRITICAL"]
    assert isinstance(data["timestamp"], int)
    assert data["timestamp"] > 0

    # Probes
    assert "probes" in data
    assert data["probes"]["liveness"] == "alive"
    assert data["probes"]["readiness"] in ["ready", "degraded", "unavailable"]

    # Database
    assert "database" in data
    db = data["database"]
    assert db["connected"] is True
    assert db["dialect"] in ["sqlite", "postgresql"]
    assert isinstance(db["ping_ms"], (int, float))
    assert db["ping_ms"] >= 0
    assert "display_url" in db

    # Connection pool
    assert "pool" in data
    pool = data["pool"]
    assert "pool_size" in pool or "checked_in" in pool or "dialect" in pool

    # Cache
    assert "cache" in data
    cache = data["cache"]
    assert "stats" in cache
    assert "health_metrics" in cache
    assert "fallback_status" in cache
    assert isinstance(cache["degraded_mode"], bool)

    # Host system metrics
    assert "system" in data
    sys = data["system"]
    assert "python_version" in sys
    assert "platform" in sys
    assert isinstance(sys["free_disk_gb"], (int, float))
    assert sys["free_disk_gb"] > 0
    assert isinstance(sys["total_disk_gb"], (int, float))
    assert sys["total_disk_gb"] > 0
    assert isinstance(sys["rss_mb"], (int, float))
    assert "environment" in sys


def test_admin_health_ui_elements_in_template():
    """Verify templates/index.html includes all required elements for the Health tab."""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Tab navigation button
    assert 'id="admin-tab-health"' in html
    assert "HEALTH" in html

    # Tab content container
    assert 'id="admin-health-tab-content"' in html

    # Status badge and controls
    assert 'id="health-overall-badge"' in html
    assert 'id="admin-health-refresh-btn"' in html
    assert 'id="admin-health-autorefresh"' in html

    # KPI diagnostic cards
    assert 'id="health-card-liveness"' in html
    assert 'id="health-card-readiness"' in html
    assert 'id="health-card-db"' in html
    assert 'id="health-card-pool"' in html
    assert 'id="health-card-cache"' in html
    assert 'id="health-card-memory"' in html
    assert 'id="health-card-disk"' in html
    assert 'id="health-card-workers"' in html

    # Detailed breakdown elements
    assert 'id="health-detail-dialect"' in html
    assert 'id="health-detail-url"' in html
    assert 'id="health-detail-ping"' in html
    assert 'id="health-detail-pool-status"' in html
    assert 'id="health-detail-env"' in html
    assert 'id="health-detail-platform"' in html
    assert 'id="health-detail-python"' in html
    assert 'id="health-detail-cache-backend"' in html

    # Probe activity log
    assert 'id="health-probe-log"' in html


def test_admin_health_js_bindings():
    """Verify static/js/main.js includes the health diagnostics controllers and handlers."""
    with open("static/js/main.js", "r", encoding="utf-8") as f:
        js = f.read()

    assert "loadHealthDiagnostics" in js
    assert "setupHealthAutoRefresh" in js
    assert "adminHealthInterval" in js
    assert "switchAdminTab('health')" in js
    assert "admin-health-refresh-btn" in js
    assert "admin-health-autorefresh" in js
    assert "/api/admin/system/health" in js
