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
    Runs with deployment migrator privileges and NullPool for one-shot jobs.
    """
    from sqlalchemy.pool import NullPool
    from app.infrastructure.database.engine import build_engine

    try:
        eng = target_engine
        if eng is None:
            mig_url = target_url or settings.database_url_migration or settings.database_url
            logger.info("Building one-shot migration engine with NullPool for %s...", mig_url.split("@")[-1] if "@" in mig_url else mig_url)
            eng = build_engine(mig_url, poolclass=NullPool)

        logger.info("Executing Alembic migrations on target engine (%s)...", eng.dialect.name)
        with eng.begin() as connection:
            # Assume table ownership role on PostgreSQL if ob_owner exists
            if connection.dialect.name == "postgresql":
                try:
                    connection.execute(text("SET ROLE ob_owner;"))
                    logger.info("Assumed role 'ob_owner' for migration execution.")
                except Exception as role_exc:
                    logger.debug("Could not assume ob_owner role (skipping if not yet provisioned): %s", role_exc)

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
