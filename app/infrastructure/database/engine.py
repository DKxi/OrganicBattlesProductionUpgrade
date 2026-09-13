import os
import sqlite3
import logging
import time
from typing import Generator, Dict, Any, Optional
from sqlalchemy import create_engine, Engine, text, event
from sqlalchemy.orm import sessionmaker, Session as DBSession
from app.settings import settings
from app.infrastructure.database.models import Base

logger = logging.getLogger("organicbattles.database")


@event.listens_for(Engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()


@event.listens_for(Engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    start = getattr(context, "_query_start_time", None)
    if start is not None:
        duration_ms = (time.time() - start) * 1000.0
        try:
            from app.observability.metrics import metrics_registry
            metrics_registry.record_query_latency(duration_ms, statement)
        except Exception:
            pass


def get_connection_pool_status(eng: Optional[Engine] = None) -> Dict[str, Any]:
    """Inspect active connection pool utilization."""
    target_engine = eng or globals().get("engine")
    if not target_engine:
        return {"status": "unavailable"}

    pool = getattr(target_engine, "pool", None)
    if not pool:
        return {"status": "no_pool"}

    size = getattr(pool, "size", lambda: 0)()
    checked_in = getattr(pool, "checkedin", lambda: 0)()
    checked_out = getattr(pool, "checkedout", lambda: 0)()
    overflow = getattr(pool, "overflow", lambda: 0)()
    total_capacity = size + max(0, overflow)
    utilization_pct = round((checked_out / total_capacity * 100), 2) if total_capacity > 0 else 0.0

    dialect = "sqlite" if str(target_engine.url).startswith("sqlite") else "postgresql"
    return {
        "dialect": dialect,
        "pool_type": pool.__class__.__name__,
        "size": size,
        "checked_in": checked_in,
        "checked_out": checked_out,
        "overflow": overflow,
        "total_capacity": total_capacity,
        "utilization_pct": utilization_pct,
    }


def _ensure_postgres_extensions(eng: Engine) -> None:
    """Ensure required PostgreSQL extensions like pg_trgm are enabled."""
    if eng.dialect.name == "postgresql":
        try:
            with eng.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        except Exception as exc:
            logger.debug("pg_trgm extension initialization note: %s", exc)


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


def is_supabase_pooler(url: str) -> bool:
    """Detect whether database connection points to a Supabase pooler or proxy."""
    if not url:
        return False
    normalized = url.lower()
    return "pooler.supabase.com" in normalized or "supabase.co" in normalized


def get_pool_config_summary(url: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculate deployment-aware database connection pool metrics.
    Applies conservative defaults (3 to 5 connections) for Supabase poolers,
    calculates cluster-wide maximum connections, and validates against service limits.
    """
    target_url = normalize_db_url(url or globals().get("current_db_url", settings.database_url))
    is_sqlite = target_url.startswith("sqlite")
    supabase_pooler = is_supabase_pooler(target_url)

    # 1. Determine pool_size
    if settings.db_pool_size is not None:
        pool_size = settings.db_pool_size
    elif supabase_pooler:
        # Conservative default: 3 connections per application worker
        pool_size = 3
    elif is_sqlite:
        pool_size = 5
    else:
        pool_size = 5

    # 2. Determine max_overflow
    if settings.db_max_overflow is not None:
        max_overflow = settings.db_max_overflow
    elif supabase_pooler:
        # Conservative burst: 2 overflow connections (total 5 peak per worker)
        max_overflow = 2
    elif is_sqlite:
        max_overflow = 0
    else:
        max_overflow = 10

    # 3. Calculate deployment scale
    workers = max(1, settings.web_concurrency)
    replicas = max(1, settings.app_replicas)
    total_workers = workers * replicas

    max_connections_per_worker = pool_size + max_overflow
    max_connection_total = max_connections_per_worker * total_workers
    service_limit = settings.db_max_connections_limit

    within_service_limit = max_connection_total <= service_limit
    if not within_service_limit and not is_sqlite:
        logger.warning(
            "Calculated maximum database connection total (%d) exceeds configured service limit (%d) "
            "(pool_size=%d, max_overflow=%d, workers=%d, replicas=%d). Adjust DB_POOL_SIZE/DB_MAX_OVERFLOW or cluster sizing.",
            max_connection_total,
            service_limit,
            pool_size,
            max_overflow,
            workers,
            replicas,
        )

    dialect = "sqlite" if is_sqlite else "postgresql"
    status = "healthy" if within_service_limit else "warning_exceeds_service_limit"

    return {
        "dialect": dialect,
        "is_supabase_pooler": supabase_pooler,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_timeout": settings.db_pool_timeout,
        "pool_recycle": settings.db_pool_recycle,
        "pool_pre_ping": True,
        "web_concurrency": workers,
        "app_replicas": replicas,
        "total_workers": total_workers,
        "max_connections_per_instance": max_connections_per_worker,
        "max_connection_total": max_connection_total,
        "service_limit": service_limit,
        "within_service_limit": within_service_limit,
        "status": status,
    }


def build_engine(url: str, poolclass: Optional[Any] = None) -> Engine:
    """Build a SQLAlchemy engine with dialect-specific connection pool settings."""
    normalized = normalize_db_url(url)
    connect_args = {"check_same_thread": False} if normalized.startswith("sqlite") else {}
    if poolclass is not None:
        return create_engine(
            normalized,
            connect_args=connect_args,
            poolclass=poolclass,
        )
    if normalized.startswith("sqlite"):
        return create_engine(
            normalized,
            connect_args=connect_args,
            pool_pre_ping=True,
        )

    summary = get_pool_config_summary(normalized)
    return create_engine(
        normalized,
        connect_args=connect_args,
        pool_pre_ping=summary["pool_pre_ping"],
        pool_size=summary["pool_size"],
        max_overflow=summary["max_overflow"],
        pool_timeout=summary["pool_timeout"],
        pool_recycle=summary["pool_recycle"],
    )


# Global active engine and session factory
current_db_url: str = normalize_db_url(settings.database_url)
engine: Engine = build_engine(current_db_url)

# Role-specific database engines & session factories (Player & Admin)
player_db_url: str = normalize_db_url(settings.database_url_player) if settings.database_url_player else current_db_url
admin_db_url: str = normalize_db_url(settings.database_url_admin) if settings.database_url_admin else current_db_url

player_engine: Engine = build_engine(player_db_url) if player_db_url != current_db_url else engine
admin_engine: Engine = build_engine(admin_db_url) if admin_db_url != current_db_url else engine

PlayerSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=player_engine)
AdminSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=admin_engine)
# Standard SessionLocal defaults to least-privilege player session factory
SessionLocal = PlayerSessionLocal


def set_session_user_context(db: DBSession, user_id: str) -> None:
    """Set transaction-local player identity for PostgreSQL Row-Level Security (RLS)."""
    try:
        bind = db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            db.execute(
                text("select set_config('app.current_user_id', :user_id, true)"),
                {"user_id": str(user_id)},
            )
    except Exception as exc:
        logger.debug("Could not set transaction-local user context: %s", exc)


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

            cursor.execute("PRAGMA table_info(OB_questions)")
            q_cols = [row[1] for row in cursor.fetchall()]
            if q_cols:
                if "release_id" not in q_cols:
                    cursor.execute("ALTER TABLE OB_questions ADD COLUMN release_id TEXT")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Auto schema migration note: %s", e)


def switch_database(new_url: str) -> Dict[str, Any]:
    """
    Live-switch the active database engine and session factory.
    Creates schema tables on target if not present.
    """
    global engine, current_db_url, player_engine, admin_engine
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

    # 2. Rename legacy tables if present, then run Alembic migrations on target database
    _ensure_postgres_extensions(test_engine)
    _migrate_legacy_table_names(test_engine)
    try:
        from app.infrastructure.database.alembic_runner import run_alembic_migrations
        run_alembic_migrations(target_engine=test_engine)
    except Exception as m_exc:
        logger.warning("Alembic migration note during switch: %s", m_exc)
        Base.metadata.create_all(bind=test_engine)

    # If target is SQLite, run schema column migrations
    if normalized_url.startswith("sqlite"):
        _migrate_sqlite_columns(normalized_url)

    # 3. Dispose old engine and rebind sessionmaker
    engine.dispose()
    if player_engine != engine:
        player_engine.dispose()
    if admin_engine != engine:
        admin_engine.dispose()

    engine = test_engine
    player_engine = test_engine
    admin_engine = test_engine
    current_db_url = normalized_url
    SessionLocal.configure(bind=engine)
    PlayerSessionLocal.configure(bind=player_engine)
    AdminSessionLocal.configure(bind=admin_engine)

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


def _seed_bosses_if_empty() -> None:
    """Populate OB_bosses and default question assignments if empty."""
    try:
        from app.infrastructure.database.bosses_repo import BossesRepository
        with SessionLocal() as db_session:
            repo = BossesRepository(db_session)
            repo.seed_default_bosses("organic1")
    except Exception as e:
        logger.debug("Auto bosses seed note: %s", e)


def _seed_admin_users_if_empty() -> None:
    """Seed initial default admin users (admin / admin and admin1 / admin2) if not present."""
    try:
        from app.infrastructure.database.admin_repo import AdminRepository
        with SessionLocal() as db_session:
            repo = AdminRepository(db_session)
            repo.seed_default_admins()
    except Exception as exc:
        logger.debug("Auto admin seed note: %s", exc)


def ensure_db_schema() -> None:
    """Ensure legacy tables are renamed, database tables are migrated via Alembic, and seeds are populated."""
    _ensure_postgres_extensions(engine)
    _migrate_legacy_table_names(engine)
    try:
        from app.infrastructure.database.alembic_runner import run_alembic_migrations
        run_alembic_migrations(target_engine=engine)
    except Exception as m_exc:
        logger.warning("Alembic migration note on startup: %s. Falling back to metadata ensure.", m_exc)
        Base.metadata.create_all(bind=engine)
    if current_db_url.startswith("sqlite"):
        _migrate_sqlite_columns(current_db_url)
    _seed_tracks_if_empty()
    _seed_bosses_if_empty()
    _seed_admin_users_if_empty()



def get_player_db() -> Generator[DBSession, None, None]:
    """FastAPI dependency yielding a player-scoped database session."""
    db = PlayerSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_admin_db() -> Generator[DBSession, None, None]:
    """FastAPI dependency yielding an admin-scoped database session."""
    db = AdminSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Default database dependency aliases get_player_db to share the exact same session instance across dependencies
get_db = get_player_db



