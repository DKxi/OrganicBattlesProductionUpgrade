import logging
from pathlib import Path
from typing import Optional
from sqlalchemy import Engine, text
from alembic.config import Config
from alembic import command
from app.settings import settings

logger = logging.getLogger("organicbattles.migrations")


def get_alembic_config(connection=None, target_url: Optional[str] = None) -> Config:
    """Build programmatic Alembic configuration pointing to alembic.ini without hardcoded credentials."""
    alembic_ini_path = settings.root_dir / "alembic.ini"
    if not alembic_ini_path.exists():
        # Fallback to current working directory
        alembic_ini_path = Path("alembic.ini")

    cfg = Config(str(alembic_ini_path))
    cfg.set_main_option("script_location", str(settings.root_dir / "migrations"))

    if target_url:
        cfg.set_main_option("sqlalchemy.url", target_url)

    if connection is not None:
        cfg.attributes["connection"] = connection

    return cfg


def run_alembic_migrations(target_engine: Optional[Engine] = None, target_url: Optional[str] = None) -> None:
    """
    Execute all pending Alembic migrations up to 'head'.
    Replaces Base.metadata.create_all() as the production schema mechanism.
    """
    try:
        if target_engine is not None:
            logger.info("Executing Alembic migrations on target engine (%s)...", target_engine.dialect.name)
            with target_engine.begin() as connection:
                cfg = get_alembic_config(connection=connection, target_url=target_url)
                command.upgrade(cfg, "head")
        else:
            logger.info("Executing Alembic migrations using application engine settings...")
            from app.infrastructure.database.engine import engine
            with engine.begin() as connection:
                cfg = get_alembic_config(connection=connection, target_url=target_url)
                command.upgrade(cfg, "head")
        logger.info("Alembic migrations completed successfully.")
    except Exception as exc:
        logger.error("Alembic migration failed: %s", exc, exc_info=True)
        raise


def get_current_migration_revision(target_engine: Optional[Engine] = None) -> Optional[str]:
    """Retrieve the current applied revision ID from alembic_version table."""
    from app.infrastructure.database.engine import engine as default_engine
    eng = target_engine or default_engine
    try:
        with eng.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            return row[0] if row else None
    except Exception:
        return None
