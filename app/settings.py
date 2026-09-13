import os
from pathlib import Path
from typing import Optional, Any
from pydantic import BaseModel, Field

try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT_DIR = Path(__file__).resolve().parent.parent
SECRETS_PATH = ROOT_DIR / "secrets.toml"
_loaded_env_file = None
try:
    from dotenv import load_dotenv

    # Prioritize local.env over legacy env, .env, and prod.env
    _custom_env = os.getenv("ENV_FILE")
    _candidates = [
        ROOT_DIR / _custom_env if _custom_env else None,
        ROOT_DIR / "local.env",
        ROOT_DIR / "env",
        ROOT_DIR / ".env",
        ROOT_DIR / "prod.env",
    ]
    for _cand in _candidates:
        if _cand and _cand.exists():
            load_dotenv(_cand, override=False)
            _loaded_env_file = _cand
            break
except ImportError:
    pass

try:
    with SECRETS_PATH.open("rb") as secrets_file:
        SECRETS = tomllib.load(secrets_file)
except FileNotFoundError:
    SECRETS = {}



def get_config_value(environment_name: str, *secret_path: str, default: Any = None) -> Any:
    """Read process environment first, then matching secrets.toml value, else default."""
    value = os.getenv(environment_name)
    if value is not None:
        return value
    if not secret_path:
        return default
    current = SECRETS
    for part in secret_path:
        if not isinstance(current, dict):
            return default
        current = current.get(part)
    return current if current is not None else default


DEFAULT_DATABASE_URL = f"sqlite:///{ROOT_DIR / 'organic_battles.sqlite3'}"


class Settings(BaseModel):
    """Centralized, validated application configuration."""
    project_name: str = "Organic Battles"
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    database_url: str = Field(default_factory=lambda: get_config_value("DATABASE_URL", default=DEFAULT_DATABASE_URL))
    database_url_player: str = Field(default_factory=lambda: get_config_value("DATABASE_URL_PLAYER", default=None) or get_config_value("DATABASE_URL", default=DEFAULT_DATABASE_URL))
    database_url_admin: str = Field(default_factory=lambda: get_config_value("DATABASE_URL_ADMIN", default=None) or get_config_value("DATABASE_URL", default=DEFAULT_DATABASE_URL))
    database_url_ingest: str = Field(default_factory=lambda: get_config_value("DATABASE_URL_INGEST", default=None) or get_config_value("DATABASE_URL", default=DEFAULT_DATABASE_URL))
    database_url_migration: str = Field(default_factory=lambda: get_config_value("DATABASE_URL_MIGRATION", default=None) or get_config_value("DATABASE_URL", default=DEFAULT_DATABASE_URL))
    database_path: Path = Field(default_factory=lambda: Path(get_config_value("DATABASE_PATH", default=str(ROOT_DIR / "organic_battles.sqlite3"))))
    game_content_source: Optional[str] = None
    
    # Database Connection Pooling & Deployment Scale
    db_pool_size: Optional[int] = Field(default_factory=lambda: int(os.environ["DB_POOL_SIZE"]) if os.environ.get("DB_POOL_SIZE") else None)
    db_max_overflow: Optional[int] = Field(default_factory=lambda: int(os.environ["DB_MAX_OVERFLOW"]) if os.environ.get("DB_MAX_OVERFLOW") else None)
    db_pool_timeout: int = Field(default_factory=lambda: int(get_config_value("DB_POOL_TIMEOUT", default=30)))
    db_pool_recycle: int = Field(default_factory=lambda: int(get_config_value("DB_POOL_RECYCLE", default=1800)))
    web_concurrency: int = Field(default_factory=lambda: int(os.getenv("WEB_CONCURRENCY", os.getenv("WORKERS", "1"))))
    app_replicas: int = Field(default_factory=lambda: int(os.getenv("APP_REPLICAS", os.getenv("REPLICAS", "1"))))
    db_max_connections_limit: int = Field(default_factory=lambda: int(get_config_value("DB_MAX_CONNECTIONS_LIMIT", default=60)))
    
    # Content & Cache Management
    max_cached_tracks: int = Field(default_factory=lambda: int(get_config_value("MAX_CACHED_TRACKS", default=4)))
    track_cache_ttl_seconds: int = Field(default_factory=lambda: int(get_config_value("TRACK_CACHE_TTL_SECONDS", default=3600)))
    redis_url: Optional[str] = Field(default_factory=lambda: get_config_value("REDIS_URL", default=None))
    warm_tracks_on_startup: bool = Field(default_factory=lambda: get_config_value("WARM_TRACKS_ON_STARTUP", default="0") == "1")
    popular_tracks_to_warm: str = Field(default_factory=lambda: str(get_config_value("POPULAR_TRACKS", default="default,adv-vocab,found-nomenclature")))
    allow_json_fallback: bool = Field(default_factory=lambda: str(get_config_value("ALLOW_JSON_FALLBACK", default="0")).lower() in ("1", "true", "yes"))
    
    # Auth & Security
    verification_code_ttl_seconds: int = Field(default_factory=lambda: int(get_config_value("VERIFICATION_CODE_TTL_SECONDS", default=900)))
    auth_session_ttl_days: int = Field(default_factory=lambda: int(get_config_value("AUTH_SESSION_TTL_DAYS", default=30)))
    cookie_secure: bool = Field(default_factory=lambda: get_config_value("COOKIE_SECURE", default="0") == "1")
    cookie_samesite: str = Field(default_factory=lambda: get_config_value("COOKIE_SAMESITE", default="lax"))
    
    # Admin Credentials
    admin_username: str = Field(default_factory=lambda: str(get_config_value("ADMIN_USERNAME", default="admin")))
    admin_password: str = Field(default_factory=lambda: str(get_config_value("ADMIN_PASSWORD", default="admin")))
    admin_session_ttl_hours: int = Field(default_factory=lambda: int(get_config_value("ADMIN_SESSION_TTL_HOURS", default=24)))
    
    # SMTP Email Settings
    smtp_host: Optional[str] = Field(default_factory=lambda: get_config_value("SMTP_HOST", "gmail", "smtp_host"))
    smtp_port: int = Field(default_factory=lambda: int(get_config_value("SMTP_PORT", "gmail", "smtp_port", default=587)))
    smtp_username: Optional[str] = Field(default_factory=lambda: get_config_value("SMTP_USERNAME", "gmail", "sender"))
    smtp_password: Optional[str] = Field(default_factory=lambda: get_config_value("SMTP_PASSWORD", "gmail", "app_password"))
    smtp_from: Optional[str] = Field(default_factory=lambda: get_config_value("SMTP_FROM", "gmail", "sender"))

    root_dir: Path = ROOT_DIR
    loaded_env_file_name: Optional[str] = Field(default_factory=lambda: _loaded_env_file.name if _loaded_env_file else None)

    s3_endpoint_url: str = Field(default_factory=lambda: get_config_value("S3_ENDPOINT_URL", default=""))
    s3_region: str = Field(default_factory=lambda: get_config_value("S3_REGION", default="us-west-2"))
    s3_access_key_id: str = Field(default_factory=lambda: get_config_value("S3_ACCESS_KEY_ID", default=""))
    s3_secret_access_key: str = Field(default_factory=lambda: get_config_value("S3_SECRET_ACCESS_KEY", default=""))
    s3_advanced_bosses_bucket: str = Field(default_factory=lambda: get_config_value("S3_ADVANCED_BOSSES_BUCKET", default="AdvancedBosses"))
    supabase_storage_public_url: Optional[str] = Field(default_factory=lambda: get_config_value("SUPABASE_STORAGE_PUBLIC_URL", default=None))
    use_supabase_boss_storage: bool = Field(default_factory=lambda: get_config_value("USE_SUPABASE_BOSS_STORAGE", default=True, env_type=bool))

    @property
    def supabase_public_storage_base_url(self) -> str:
        """Returns the public Supabase storage base URL for AdvancedBosses."""
        if self.supabase_storage_public_url:
            return self.supabase_storage_public_url.rstrip("/")
        if self.s3_endpoint_url:
            import re
            m = re.search(r"https?://([a-zA-Z0-9_-]+)\.storage\.supabase\.co", self.s3_endpoint_url)
            if m:
                ref = m.group(1)
                return f"https://{ref}.supabase.co/storage/v1/object/public/{self.s3_advanced_bosses_bucket}"
        return f"https://aamwrwbsrmorllisdffc.supabase.co/storage/v1/object/public/{self.s3_advanced_bosses_bucket}"


settings = Settings()
