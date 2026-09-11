from unittest.mock import patch, MagicMock
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.settings import settings
from app.infrastructure.database.engine import (
    is_supabase_pooler,
    get_pool_config_summary,
    build_engine,
)


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


def test_is_supabase_pooler_detection():
    """Verify accurate detection of Supabase poolers and proxies."""
    assert is_supabase_pooler("postgresql+psycopg2://postgres.abc:pass@aws-0-us-west-2.pooler.supabase.com:5432/postgres") is True
    assert is_supabase_pooler("postgresql://user:pass@db.projectref.supabase.co:6543/postgres") is True
    assert is_supabase_pooler("postgresql://postgres:pass@localhost:5432/organic_battles") is False
    assert is_supabase_pooler("sqlite:///test.sqlite3") is False
    assert is_supabase_pooler("") is False


def test_supabase_pooler_conservative_defaults():
    """When using a Supabase pooler without explicit overrides, start conservatively with 3-5 connections."""
    with patch.object(settings, "db_pool_size", None), \
         patch.object(settings, "db_max_overflow", None), \
         patch.object(settings, "web_concurrency", 1), \
         patch.object(settings, "app_replicas", 1):
        summary = get_pool_config_summary("postgresql+psycopg2://postgres.abc:pass@aws-0-us-west-2.pooler.supabase.com:5432/postgres")
        assert summary["is_supabase_pooler"] is True
        assert summary["pool_size"] == 3
        assert summary["max_overflow"] == 2
        assert summary["max_connections_per_instance"] == 5
        assert summary["max_connection_total"] == 5
        assert summary["within_service_limit"] is True
        assert summary["status"] == "healthy"


def test_standard_postgres_defaults():
    """When using standard PostgreSQL without pooler, apply standard server pool defaults."""
    with patch.object(settings, "db_pool_size", None), \
         patch.object(settings, "db_max_overflow", None):
        summary = get_pool_config_summary("postgresql://postgres:pass@localhost:5432/postgres")
        assert summary["is_supabase_pooler"] is False
        assert summary["pool_size"] == 5
        assert summary["max_overflow"] == 10
        assert summary["max_connections_per_instance"] == 15


def test_explicit_environment_variable_precedence():
    """Explicit environment variables (DB_POOL_SIZE, DB_MAX_OVERFLOW, etc.) override defaults."""
    with patch.object(settings, "db_pool_size", 8), \
         patch.object(settings, "db_max_overflow", 12), \
         patch.object(settings, "db_pool_timeout", 45), \
         patch.object(settings, "db_pool_recycle", 900):
        summary = get_pool_config_summary("postgresql+psycopg2://postgres.abc:pass@aws-0-us-west-2.pooler.supabase.com:5432/postgres")
        assert summary["pool_size"] == 8
        assert summary["max_overflow"] == 12
        assert summary["pool_timeout"] == 45
        assert summary["pool_recycle"] == 900
        assert summary["max_connections_per_instance"] == 20


def test_calculate_max_connection_total_across_workers_and_replicas():
    """Calculate maximum connection total across all workers and replicas."""
    with patch.object(settings, "db_pool_size", 4), \
         patch.object(settings, "db_max_overflow", 2), \
         patch.object(settings, "web_concurrency", 4), \
         patch.object(settings, "app_replicas", 3), \
         patch.object(settings, "db_max_connections_limit", 100):
        # 4 workers * 3 replicas = 12 total workers
        # 4 pool_size + 2 max_overflow = 6 per worker
        # 12 * 6 = 72 max total connections
        summary = get_pool_config_summary("postgresql://user:pass@remote-host:5432/db")
        assert summary["total_workers"] == 12
        assert summary["max_connections_per_instance"] == 6
        assert summary["max_connection_total"] == 72
        assert summary["service_limit"] == 100
        assert summary["within_service_limit"] is True
        assert summary["status"] == "healthy"


def test_service_limit_exceeded_warning():
    """When calculated connection total exceeds service limit, mark warning status."""
    with patch.object(settings, "db_pool_size", 10), \
         patch.object(settings, "db_max_overflow", 20), \
         patch.object(settings, "web_concurrency", 4), \
         patch.object(settings, "app_replicas", 2), \
         patch.object(settings, "db_max_connections_limit", 50):
        # 8 workers * 30 per worker = 240 connections > 50 service limit
        summary = get_pool_config_summary("postgresql://user:pass@remote-host:5432/db")
        assert summary["max_connection_total"] == 240
        assert summary["service_limit"] == 50
        assert summary["within_service_limit"] is False
        assert summary["status"] == "warning_exceeds_service_limit"


def test_build_engine_passes_pool_settings():
    """Verify build_engine configures SQLAlchemy with computed pool arguments."""
    with patch("app.infrastructure.database.engine.create_engine") as mock_create_engine, \
         patch.object(settings, "db_pool_size", 5), \
         patch.object(settings, "db_max_overflow", 3), \
         patch.object(settings, "db_pool_timeout", 25), \
         patch.object(settings, "db_pool_recycle", 600):
        build_engine("postgresql://postgres:pass@localhost:5432/organic_battles")
        mock_create_engine.assert_called_once()
        _, kwargs = mock_create_engine.call_args
        assert kwargs["pool_size"] == 5
        assert kwargs["max_overflow"] == 3
        assert kwargs["pool_timeout"] == 25
        assert kwargs["pool_recycle"] == 600
        assert kwargs["pool_pre_ping"] is True


def test_admin_system_config_includes_database_pool_telemetry(admin_client):
    """Verify GET /api/v1/admin/system/config reports deployment-aware pool information."""
    resp = admin_client.get("/api/v1/admin/system/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "database_pool" in data
    pool = data["database_pool"]
    assert "dialect" in pool
    assert "pool_size" in pool
    assert "max_overflow" in pool
    assert "pool_timeout" in pool
    assert "pool_recycle" in pool
    assert "total_workers" in pool
    assert "max_connections_per_instance" in pool
    assert "max_connection_total" in pool
    assert "service_limit" in pool
    assert "within_service_limit" in pool
    assert "status" in pool
