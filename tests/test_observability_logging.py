import os
import json
import logging
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import settings
from app.observability.logging import (
    setup_logging,
    get_logging_config,
    update_logging_config,
    tail_log_file,
    DEFAULT_LOG_FILE,
    PROPERTIES_FILE,
)
from app.infrastructure.identity.crypto import code_hash
from app.infrastructure.cache.memory import set_admin_token


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def admin_headers():
    token = "observability-admin-token"
    set_admin_token(code_hash(token))
    return {"Authorization": f"Bearer {token}"}


def test_setup_logging_and_file_creation():
    """Verify setup_logging initializes log directory and file properly."""
    setup_logging()
    assert PROPERTIES_FILE.is_file(), "logging.properties should exist in root directory"
    assert DEFAULT_LOG_FILE.parent.is_dir(), "logs/ directory must exist"

    # Emit test logs across distinct subsystems
    api_logger = logging.getLogger("organicbattles.api")
    combat_logger = logging.getLogger("organicbattles.battle")
    auth_logger = logging.getLogger("organicbattles.auth")

    api_logger.info("Test API log message: verification event")
    combat_logger.info("Test Combat log message: spell cast")
    auth_logger.info("Test Auth log message: user session")

    # Flush all handlers to disk
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert DEFAULT_LOG_FILE.is_file(), "Active log file logs/organic_battles.log must exist"
    content = DEFAULT_LOG_FILE.read_text(encoding="utf-8", errors="replace")
    assert "Test API log message: verification event" in content
    assert "Test Combat log message: spell cast" in content
    assert "Test Auth log message: user session" in content


def test_get_logging_config():
    """Verify get_logging_config returns correct schema and logger names."""
    cfg = get_logging_config()
    assert "properties_file" in cfg
    assert "log_file" in cfg
    assert "levels" in cfg
    assert "root" in cfg["levels"]
    assert "organicbattles.api" in cfg["levels"]
    assert "organicbattles.battle" in cfg["levels"]
    assert "organicbattles.auth" in cfg["levels"]
    assert "organicbattles.database" in cfg["levels"]
    assert "allowed_levels" in cfg
    assert "DEBUG" in cfg["allowed_levels"]
    assert "INFO" in cfg["allowed_levels"]


def test_update_logging_config_dynamic_and_persisted():
    """Verify update_logging_config updates active Python loggers and persists to logging.properties."""
    # Set organicbattles.battle to DEBUG
    updated = update_logging_config(levels={"organicbattles.battle": "DEBUG", "organicbattles.api": "WARNING"})
    assert updated["levels"]["organicbattles.battle"] == "DEBUG"
    assert updated["levels"]["organicbattles.api"] == "WARNING"

    # Check active logger directly in memory
    battle_logger = logging.getLogger("organicbattles.battle")
    assert battle_logger.level == logging.DEBUG

    api_logger = logging.getLogger("organicbattles.api")
    assert battle_logger.level == logging.DEBUG
    assert api_logger.level == logging.WARNING

    # Verify logging.properties file was updated
    prop_text = PROPERTIES_FILE.read_text(encoding="utf-8")
    assert "level=DEBUG" in prop_text or "level = DEBUG" in prop_text

    # Restore to INFO
    update_logging_config(levels={"organicbattles.battle": "INFO", "organicbattles.api": "INFO"})


def test_tail_log_file():
    """Verify tail_log_file safely returns the last lines."""
    lines = tail_log_file(lines=10)
    assert isinstance(lines, list)
    assert len(lines) > 0


def test_admin_get_logging_config_endpoint(client, admin_headers):
    """Test GET /api/admin/system/logging."""
    response = client.get("/api/admin/system/logging", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "levels" in data
    assert "log_file" in data
    assert data["file_exists"] is True


def test_admin_update_logging_config_endpoint(client, admin_headers):
    """Test POST /api/admin/system/logging."""
    response = client.post(
        "/api/admin/system/logging",
        json={"levels": {"organicbattles.auth": "DEBUG"}},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["config"]["levels"]["organicbattles.auth"] == "DEBUG"

    # Restore
    client.post(
        "/api/admin/system/logging",
        json={"levels": {"organicbattles.auth": "INFO"}},
        headers=admin_headers,
    )


def test_admin_tail_logs_endpoint(client, admin_headers):
    """Test GET /api/admin/system/logging/tail."""
    response = client.get("/api/admin/system/logging/tail?lines=20", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "lines" in data
    assert isinstance(data["lines"], list)
    assert data["lines_count"] == len(data["lines"])


def test_middleware_request_logging(client):
    """Verify that requests pass through middleware and write structured logs."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers
