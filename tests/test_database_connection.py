import re
import pytest
from pathlib import Path
from dotenv import dotenv_values
import psycopg2
from sqlalchemy import create_engine, text

ROOT_DIR = Path(__file__).parents[1]
ENV_FILE = (
    ROOT_DIR / "local.env"
    if (ROOT_DIR / "local.env").exists()
    else (ROOT_DIR / "env" if (ROOT_DIR / "env").exists() else ROOT_DIR / ".env")
)


def get_database_env():
    """Load database settings from env or .env file."""
    if not ENV_FILE.exists():
        pytest.skip(f"No env or .env file found at {ENV_FILE}")
    values = dotenv_values(ENV_FILE)
    return values


def resolve_postgres_url(raw_url: str) -> str:
    """
    Ensure the PostgreSQL URL is formatted properly.
    If the URL points to Supabase's direct IPv6 hostname (db.<ref>.supabase.co)
    and the local environment lacks IPv6 routing, resolve to the Supabase IPv4 Pooler URL.
    """
    if not raw_url:
        return raw_url

    # Convert postgresql:// to postgresql+psycopg2:// if needed for SQLAlchemy
    url = raw_url.strip()
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]

    # Check if this is a direct Supabase host: db.<ref>.supabase.co
    match = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@db\.([^\.]+)\.supabase\.co:(\d+)/(.+)", url)
    if match:
        user, pwd, ref, port, dbname = match.groups()
        # Test if direct host can be resolved
        try:
            import socket
            socket.gethostbyname(f"db.{ref}.supabase.co")
            return url
        except Exception:
            # Fallback to Supabase IPv4 connection pooler in us-west-2 (session mode port 5432)
            pooler_host = "aws-0-us-west-2.pooler.supabase.com"
            pooler_user = f"{user}.{ref}"
            return f"postgresql+psycopg2://{pooler_user}:{pwd}@{pooler_host}:5432/{dbname}"

    return url


def test_env_file_contains_database_settings():
    """Verify that the env file exists and contains valid database configurations (SQLite or PostgreSQL)."""
    values = get_database_env()
    db_url = values.get("DATABASE_URL")
    
    # Must have either DATABASE_URL or individual host/port/database keys
    has_url = bool(db_url and ("postgresql" in db_url.lower() or "sqlite" in db_url.lower()))
    has_parts = bool(values.get("host") and values.get("database"))
    
    assert has_url or has_parts, f"No database configuration found in {ENV_FILE}"
    
    if db_url:
        is_valid = ("postgresql" in db_url.lower() or "sqlite" in db_url.lower())
        assert is_valid, f"Expected SQLite or PostgreSQL URL, got: {db_url}"


def test_supabase_postgresql_connection_raw_psycopg2():
    """Test raw TCP connection to the Supabase PostgreSQL database using psycopg2."""
    values = get_database_env()
    db_url = values.get("DATABASE_URL")
    if not db_url or "postgresql" not in db_url.lower():
        pytest.skip("PostgreSQL is not active in env file (SQLite or other dialect configured)")

    resolved_url = resolve_postgres_url(db_url)
    
    # Convert SQLAlchemy driver prefix to standard psycopg2 connection URI
    psycopg2_url = resolved_url.replace("postgresql+psycopg2://", "postgresql://")

    conn = None
    try:
        conn = psycopg2.connect(psycopg2_url, connect_timeout=10)
        assert conn is not None
        cur = conn.cursor()
        
        # 1. Query server version
        cur.execute("SELECT version();")
        version_str = cur.fetchone()[0]
        assert "PostgreSQL" in version_str, f"Unexpected version string: {version_str}"
        
        # 2. Query database and user
        cur.execute("SELECT current_database(), current_user;")
        db_name, user_name = cur.fetchone()
        assert db_name == "postgres"
        assert "postgres" in user_name
        
        cur.close()
    finally:
        if conn:
            conn.close()


def test_supabase_postgresql_connection_sqlalchemy():
    """Test connection pool and query execution using SQLAlchemy engine."""
    values = get_database_env()
    db_url = values.get("DATABASE_URL")
    if not db_url or "postgresql" not in db_url.lower():
        pytest.skip("DATABASE_URL is not configured for PostgreSQL")

    resolved_url = resolve_postgres_url(db_url)
    if resolved_url.startswith("postgresql://"):
        resolved_url = "postgresql+psycopg2://" + resolved_url[len("postgresql://"):]

    engine = create_engine(resolved_url, pool_pre_ping=True, pool_timeout=10)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1;")).scalar()
        assert res == 1

        db_version = conn.execute(text("SHOW server_version;")).scalar()
        assert db_version is not None
        assert float(db_version.split(".")[0]) >= 14  # Supabase runs modern PostgreSQL (15/17)
    engine.dispose()


def test_supabase_postgresql_schema_tables_queryable():
    """Verify that public tables can be queried and inspected in the Supabase PostgreSQL database."""
    values = get_database_env()
    db_url = values.get("DATABASE_URL")
    if not db_url or "postgresql" not in db_url.lower():
        pytest.skip("DATABASE_URL is not configured for PostgreSQL")

    resolved_url = resolve_postgres_url(db_url)
    if resolved_url.startswith("postgresql://"):
        resolved_url = "postgresql+psycopg2://" + resolved_url[len("postgresql://"):]

    engine = create_engine(resolved_url, pool_pre_ping=True)
    with engine.connect() as conn:
        # Check information_schema for existing tables
        tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
        )).fetchall()
        table_names = [t[0] for t in tables]
        assert isinstance(table_names, list)
    engine.dispose()


def test_sqlite_connection_if_configured():
    """Test local SQLite database file connectivity when SQLite is selected in env."""
    values = get_database_env()
    db_url = values.get("DATABASE_URL")
    if not db_url or not db_url.startswith("sqlite"):
        pytest.skip("SQLite is not active in env file (PostgreSQL is selected)")

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1;")).scalar()
        assert res == 1
    engine.dispose()


def test_normalize_db_url():
    """Verify normalize_db_url converts postgres URLs to use psycopg2 driver."""
    from app.infrastructure.database.engine import normalize_db_url
    assert normalize_db_url("postgres://user:pass@host:5432/db") == "postgresql+psycopg2://user:pass@host:5432/db"
    assert normalize_db_url("postgresql://user:pass@host:5432/db") == "postgresql+psycopg2://user:pass@host:5432/db"
    assert normalize_db_url("sqlite:///data.sqlite3") == "sqlite:///data.sqlite3"


def test_dynamic_engine_switching_sqlite_isolated(tmp_path):
    """Test switching between two isolated SQLite databases using switch_database()."""
    import app.infrastructure.database.engine as db_mod
    from app.infrastructure.database.models import User

    initial_url = db_mod.current_db_url

    db1_path = tmp_path / "db1.sqlite3"
    db2_path = tmp_path / "db2.sqlite3"
    url1 = f"sqlite:///{db1_path}"
    url2 = f"sqlite:///{db2_path}"

    try:
        # Switch to db1
        res1 = db_mod.switch_database(url1)
        assert res1["status"] == "ok"
        assert res1["dialect"] == "sqlite"
        assert db_mod.current_db_url == url1

        # Write to db1 via SessionLocal
        with db_mod.SessionLocal() as session:
            user = User(
                id="user_test_1",
                username="player_one",
                password_hash="hash123",
                email="p1@example.com",
            )
            session.add(user)
            session.commit()

        # Verify record exists in db1
        with db_mod.SessionLocal() as session:
            assert session.query(User).filter_by(username="player_one").count() == 1

        # Switch to db2
        res2 = db_mod.switch_database(url2)
        assert res2["status"] == "ok"
        assert res2["dialect"] == "sqlite"
        assert db_mod.current_db_url == url2

        # Verify db2 is isolated (user does not exist in db2)
        with db_mod.SessionLocal() as session:
            assert session.query(User).filter_by(username="player_one").count() == 0

    finally:
        # Restore initial database
        db_mod.switch_database(initial_url)
        assert db_mod.current_db_url == initial_url


def test_switch_database_failure_preserves_state():
    """Verify that a failed switch_database() call does not alter existing engine or URL."""
    import app.infrastructure.database.engine as db_mod

    initial_url = db_mod.current_db_url
    initial_engine = db_mod.engine

    # Attempt switching to an invalid/unreachable host
    invalid_url = "postgresql+psycopg2://invalid_user:invalid_pass@127.0.0.1:54329/nonexistent_db"
    with pytest.raises(Exception):
        db_mod.switch_database(invalid_url)

    # State must be preserved
    assert db_mod.current_db_url == initial_url
    assert db_mod.engine is initial_engine

    # Connection on preserved engine still works
    with db_mod.SessionLocal() as session:
        res = session.execute(text("SELECT 1")).scalar()
        assert res == 1


def test_live_switch_to_supabase_postgresql_and_back():
    """Test hot-swapping from SQLite to Supabase PostgreSQL and back using switch_database()."""
    values = get_database_env()
    db_url = values.get("DATABASE_URL")
    if not db_url or "postgresql" not in db_url.lower():
        pytest.skip("DATABASE_URL is not configured for PostgreSQL in env")

    import app.infrastructure.database.engine as db_mod

    resolved_url = resolve_postgres_url(db_url)
    initial_url = db_mod.current_db_url

    try:
        # Switch to PostgreSQL
        res = db_mod.switch_database(resolved_url)
        assert res["status"] == "ok"
        assert res["dialect"] == "postgresql"
        assert "postgresql" in db_mod.current_db_url

        # Query live PostgreSQL through newly rebound SessionLocal
        with db_mod.SessionLocal() as session:
            val = session.execute(text("SELECT 42")).scalar()
            assert val == 42

    finally:
        # Switch back to initial URL
        db_mod.switch_database(initial_url)
        assert db_mod.current_db_url == initial_url
        with db_mod.SessionLocal() as session:
            val = session.execute(text("SELECT 1")).scalar()
            assert val == 1

