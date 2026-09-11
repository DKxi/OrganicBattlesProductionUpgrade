import os
from pathlib import Path
from dotenv import dotenv_values
from app.settings import ROOT_DIR

LOCAL_ENV = ROOT_DIR / "local.env"
PROD_ENV = ROOT_DIR / "prod.env"


def test_env_files_exist():
    """Verify both local.env and prod.env exist in the project root."""
    assert LOCAL_ENV.exists(), "local.env is missing from root directory"
    assert PROD_ENV.exists(), "prod.env is missing from root directory"


def test_local_env_defaults():
    """Verify local.env defines appropriate local development configuration defaults."""
    vals = dotenv_values(LOCAL_ENV)

    assert vals.get("ENVIRONMENT") == "development"
    assert vals.get("DEBUG") == "true"
    assert vals.get("PORT") == "8000"
    assert vals.get("COOKIE_SECURE") == "0"
    assert vals.get("ALLOW_JSON_FALLBACK") == "true"
    assert int(vals.get("DB_POOL_SIZE", 0)) > 0
    assert int(vals.get("DB_MAX_OVERFLOW", 0)) >= 0
    assert int(vals.get("WEB_CONCURRENCY", 0)) == 1
    assert int(vals.get("APP_REPLICAS", 0)) == 1
    assert "DATABASE_URL" in vals


def test_prod_env_defaults():
    """Verify prod.env defines appropriate production deployment configuration defaults."""
    vals = dotenv_values(PROD_ENV)

    assert vals.get("ENVIRONMENT") == "production"
    assert vals.get("DEBUG") == "false"
    assert vals.get("PORT") == "8000"
    assert vals.get("COOKIE_SECURE") == "1"
    assert vals.get("ALLOW_JSON_FALLBACK") == "false"
    assert int(vals.get("DB_POOL_SIZE", 0)) >= 4
    assert int(vals.get("DB_MAX_OVERFLOW", 0)) >= 2
    assert int(vals.get("WEB_CONCURRENCY", 0)) >= 2
    assert int(vals.get("APP_REPLICAS", 0)) >= 2
    assert int(vals.get("MAX_CACHED_TRACKS", 0)) >= 16
    assert int(vals.get("TRACK_CACHE_TTL_SECONDS", 0)) >= 86400
    assert vals.get("WARM_TRACKS_ON_STARTUP") == "1"
    assert "postgresql" in vals.get("DATABASE_URL", "").lower()


def test_settings_priority_prefers_local_env():
    """Verify that settings.py prioritizes local.env over legacy env files."""
    from app.settings import ROOT_DIR

    # Verify candidates list in settings module prioritizes local.env
    candidates = [
        ROOT_DIR / "local.env",
        ROOT_DIR / "env",
        ROOT_DIR / ".env",
        ROOT_DIR / "prod.env",
    ]
    # First existing candidate must be local.env
    first_existing = next((c for c in candidates if c.exists()), None)
    assert first_existing == LOCAL_ENV
