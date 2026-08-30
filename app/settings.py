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


class Settings(BaseModel):
    """Centralized, validated application configuration."""
    project_name: str = "Organic Battles"
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    database_url: str = Field(default_factory=lambda: get_config_value("DATABASE_URL", default=f"sqlite:///{ROOT_DIR / 'organic_battles.sqlite3'}"))
    database_path: Path = Field(default_factory=lambda: Path(get_config_value("DATABASE_PATH", default=str(ROOT_DIR / "organic_battles.sqlite3"))))
    game_content_source: Optional[str] = Field(default_factory=lambda: os.getenv("GAME_CONTENT_SOURCE"))
    
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


settings = Settings()
