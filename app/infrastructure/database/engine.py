import os
import sqlite3
import logging
from typing import Generator, Dict, Any
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session as DBSession
from app.settings import settings
from app.infrastructure.database.models import Base

logger = logging.getLogger("organicbattles.database")


def normalize_db_url(url: str) -> str:
    """Normalize database connection URL for SQLAlchemy compatibility."""
    if not url:
        return url
    trimmed = url.strip()
    if trimmed.startswith("postgres://"):
        return "postgresql+psycopg2://" + trimmed[len("postgres://"):]
    if trimmed.startswith("postgresql://") and not trimmed.startswith("postgresql+"):
        return "postgresql+psycopg2://" + trimmed[len("postgresql://"):]
    return trimmed


def build_engine(url: str) -> Engine:
    """Build a SQLAlchemy engine with dialect-specific connection pool settings."""
    normalized = normalize_db_url(url)
    connect_args = {"check_same_thread": False} if normalized.startswith("sqlite") else {}
    if normalized.startswith("sqlite"):
        return create_engine(
            normalized,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
    return create_engine(
        normalized,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


# Global active engine and session factory
current_db_url: str = normalize_db_url(settings.database_url)
engine: Engine = build_engine(current_db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_active_engine() -> Engine:
    """Return the currently active database engine."""
    return engine



def _migrate_legacy_table_names(eng: Engine) -> None:
    """Rename legacy un-prefixed tables to OB_ prefix if present."""
    try:
        with eng.begin() as conn:
            if eng.dialect.name == "sqlite":
                existing = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
            else:
                existing = {row[0] for row in conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")).fetchall()}

            table_renames = [
                ("curricula", "OB_curricula"),
                ("tracks", "OB_tracks"),
                ("questions", "OB_questions"),
                ("users", "OB_users"),
                ("verification_codes", "OB_verification_codes"),
                ("auth_sessions", "OB_auth_sessions"),
                ("game_sessions", "OB_game_sessions"),
            ]
            for old_tbl, new_tbl in table_renames:
                if old_tbl in existing and new_tbl not in existing:
                    logger.info("Migrating legacy table name %s -> %s", old_tbl, new_tbl)
                    conn.execute(text(f'ALTER TABLE "{old_tbl}" RENAME TO "{new_tbl}"'))
    except Exception as exc:
        logger.warning("Table prefix rename check note: %s", exc)


def _migrate_sqlite_columns(url: str) -> None:
    """Run SQLite auto-migrations for missing columns if SQLite database file exists."""
    db_file = url.replace("sqlite:///", "")
    if db_file and os.path.exists(db_file):
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(OB_users)")
            user_cols = [row[1] for row in cursor.fetchall()]
            if user_cols:
                if "content_source" not in user_cols:
                    cursor.execute("ALTER TABLE OB_users ADD COLUMN content_source TEXT")
                if "progress_json" not in user_cols:
                    cursor.execute("ALTER TABLE OB_users ADD COLUMN progress_json TEXT")

            cursor.execute("PRAGMA table_info(OB_game_sessions)")
            sess_cols = [row[1] for row in cursor.fetchall()]
            if sess_cols:
                if "content_source" not in sess_cols:
                    cursor.execute("ALTER TABLE OB_game_sessions ADD COLUMN content_source TEXT")
                if "turn_id" not in sess_cols:
                    cursor.execute("ALTER TABLE OB_game_sessions ADD COLUMN turn_id TEXT")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Auto schema migration note: %s", e)


def switch_database(new_url: str) -> Dict[str, Any]:
    """
    Live-switch the active database engine and session factory.
    Creates schema tables on target if not present.
    """
    global engine, current_db_url
    normalized_url = normalize_db_url(new_url)
    logger.info("Switching database from %s to %s", current_db_url, normalized_url)

    # 1. Test connectivity
    test_engine = build_engine(normalized_url)
    try:
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        test_engine.dispose()
        raise

    # 2. Rename legacy tables if present, then auto-create schema on target database
    _migrate_legacy_table_names(test_engine)
    Base.metadata.create_all(bind=test_engine)

    # If target is SQLite, run schema column migrations
    if normalized_url.startswith("sqlite"):
        _migrate_sqlite_columns(normalized_url)

    # 3. Dispose old engine and rebind sessionmaker
    engine.dispose()
    engine = test_engine
    current_db_url = normalized_url
    SessionLocal.configure(bind=engine)

    # 4. Seed tracks if newly targeted database is empty
    _seed_tracks_if_empty()

    dialect = "postgresql" if "postgresql" in normalized_url else "sqlite"
    return {"status": "ok", "dialect": dialect, "url": normalized_url}


def _seed_tracks_if_empty() -> None:
    """Populate curricula and tracks tables from data/tracks_config.json if empty."""
    try:
        from app.infrastructure.database.tracks_repo import TracksRepository
        with SessionLocal() as db_session:
            repo = TracksRepository(db_session)
            repo.seed_if_empty(settings.root_dir / "data" / "tracks_config.json")
    except Exception as e:
        logger.warning("Auto tracks seed note: %s", e)


def ensure_db_schema() -> None:
    """Ensure legacy tables are renamed, database tables exist, SQLite columns are up to date, and tracks are seeded."""
    _migrate_legacy_table_names(engine)
    Base.metadata.create_all(bind=engine)
    if current_db_url.startswith("sqlite"):
        _migrate_sqlite_columns(current_db_url)
    _seed_tracks_if_empty()


def get_db() -> Generator[DBSession, None, None]:
    """FastAPI dependency yielding a thread-safe database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


