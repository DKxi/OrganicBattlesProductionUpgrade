import inspect
import pytest
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.settings import settings
from app.infrastructure.database.engine import (
    player_engine,
    admin_engine,
    PlayerSessionLocal,
    AdminSessionLocal,
    get_player_db,
    get_admin_db,
    get_db,
    set_session_user_context,
)


def test_least_privilege_sql_script_structure():
    """Verify scripts/setup_supabase_least_privilege_roles.sql contains all required role grants and RLS."""
    sql_path = settings.root_dir / "scripts" / "setup_supabase_least_privilege_roles.sql"
    assert sql_path.is_file(), "setup_supabase_least_privilege_roles.sql must exist"
    sql = sql_path.read_text(encoding="utf-8")

    # Step 1: 5 roles defined
    assert "CREATE ROLE ob_owner NOLOGIN" in sql
    assert "CREATE ROLE ob_player_api LOGIN" in sql
    assert "CREATE ROLE ob_admin_api LOGIN" in sql
    assert "CREATE ROLE ob_content_ingest LOGIN" in sql
    assert "CREATE ROLE ob_migrator LOGIN" in sql
    assert "GRANT ob_owner TO ob_migrator;" in sql
    assert "GRANT CREATE ON SCHEMA public TO ob_owner;" in sql

    # Step 2: Revoke inherited access
    assert "REVOKE ALL ON TABLE" in sql
    assert "FROM public, anon, authenticated, ob_player_api, ob_admin_api, ob_content_ingest;" in sql

    # Step 3: Player route privileges (read content, scoped DML on player data, no admin access)
    assert 'GRANT SELECT ON TABLE \n    public."OB_curricula"' in sql or 'public."OB_curricula"' in sql
    assert 'TO ob_player_api;' in sql
    assert 'OB_admin_users' not in sql.split('STEP 3:')[1].split('STEP 4:')[0]
    assert 'DELETE ON TABLE public."OB_questions"' not in sql.split('STEP 3:')[1].split('STEP 4:')[0]

    # Step 4: Admin route privileges (all tables read, DML on application & content, answer attempts append-only)
    assert 'TO ob_admin_api;' in sql
    admin_step = sql.split('STEP 4:')[1].split('STEP 5:')[0]
    assert 'GRANT INSERT, UPDATE, DELETE ON TABLE' in admin_step
    assert 'OB_answer_attempts' not in admin_step.split('GRANT INSERT, UPDATE, DELETE')[1].split('TO ob_admin_api;')[0]

    # Step 5: Ingest privileges (content DML only, no player/admin tables)
    ingest_step = sql.split('STEP 5:')[1].split('STEP 6:')[0]
    assert 'TO ob_content_ingest;' in ingest_step
    ingest_grants = ingest_step.split('GRANT SELECT, INSERT, UPDATE, DELETE')[1].split('TO ob_content_ingest;')[0]
    assert 'OB_users' not in ingest_grants
    assert 'OB_admin_users' not in ingest_grants
    assert 'ALTER TABLE public."OB_questions" OWNER TO ob_owner;' in ingest_step

    # Step 6: RLS on player tables
    rls_step = sql.split('STEP 6:')[1]
    for tbl in ["OB_game_sessions", "OB_users", "OB_auth_sessions", "OB_player_question_progress", "OB_answer_attempts", "OB_verification_codes"]:
        assert f'ALTER TABLE public."{tbl}" ENABLE ROW LEVEL SECURITY;' in rls_step
        assert f'ALTER TABLE public."{tbl}" FORCE ROW LEVEL SECURITY;' in rls_step
    assert "current_setting('app.current_user_id', true)" in rls_step
    assert "TO ob_player_api" in rls_step
    assert "TO ob_admin_api" in rls_step


def test_settings_role_specific_database_urls(monkeypatch):
    """Verify Settings resolves independent database URLs for player, admin, ingest, and migration."""
    assert hasattr(settings, "database_url_player")
    assert hasattr(settings, "database_url_admin")
    assert hasattr(settings, "database_url_ingest")
    assert hasattr(settings, "database_url_migration")

    # Verify environment overrides take effect
    monkeypatch.setenv("DATABASE_URL_PLAYER", "postgresql+psycopg2://ob_player_api:secret@host:5432/postgres")
    monkeypatch.setenv("DATABASE_URL_ADMIN", "postgresql+psycopg2://ob_admin_api:secret@host:5432/postgres")
    monkeypatch.setenv("DATABASE_URL_INGEST", "postgresql+psycopg2://ob_content_ingest:secret@host:5432/postgres")
    monkeypatch.setenv("DATABASE_URL_MIGRATION", "postgresql+psycopg2://ob_migrator:secret@host:5432/postgres")

    from app.settings import Settings
    s = Settings()
    assert "ob_player_api" in s.database_url_player
    assert "ob_admin_api" in s.database_url_admin
    assert "ob_content_ingest" in s.database_url_ingest
    assert "ob_migrator" in s.database_url_migration


def test_engine_splitting_and_session_factories():
    """Verify distinct engine instances and session factories for player and admin access."""
    assert player_engine is not None
    assert admin_engine is not None

    with PlayerSessionLocal() as p_session:
        assert isinstance(p_session, Session)
    with AdminSessionLocal() as a_session:
        assert isinstance(a_session, Session)

    # Dependencies yield sessions
    p_gen = get_player_db()
    db_p = next(p_gen)
    assert isinstance(db_p, Session)
    try:
        next(p_gen)
    except StopIteration:
        pass

    a_gen = get_admin_db()
    db_a = next(a_gen)
    assert isinstance(db_a, Session)
    try:
        next(a_gen)
    except StopIteration:
        pass


def test_set_session_user_context():
    """Verify set_session_user_context executes cleanly without exceptions."""
    with PlayerSessionLocal() as db:
        # On SQLite, safely passes; on PostgreSQL sets transaction-local setting
        set_session_user_context(db, "test_user_uuid_123")


def test_fastapi_startup_has_no_ddl():
    """Verify FastAPI application factory create_app() does not invoke ensure_db_schema or create_all."""
    import app.main as main_mod
    source = inspect.getsource(main_mod.create_app)
    assert "ensure_db_schema" not in source
    assert "create_all" not in source


def test_ingest_script_reads_ingest_url_and_uses_nullpool():
    """Verify scripts/ingest_questions_to_postgres.py connects with database_url_ingest and NullPool."""
    ingest_path = settings.root_dir / "scripts" / "ingest_questions_to_postgres.py"
    content = ingest_path.read_text(encoding="utf-8")
    assert "database_url_ingest" in content
    assert "NullPool" in content
    assert "create_all" not in content


def test_alembic_runner_uses_migration_url_and_nullpool():
    """Verify app/infrastructure/database/alembic_runner.py uses database_url_migration and NullPool."""
    runner_path = settings.root_dir / "app" / "infrastructure" / "database" / "alembic_runner.py"
    content = runner_path.read_text(encoding="utf-8")
    assert "database_url_migration" in content
    assert "NullPool" in content
    assert "SET ROLE ob_owner" in content


def test_dependency_boundaries_across_routers():
    """Verify admin routers depend on get_admin_db and player routers depend on get_player_db."""
    import app.api.v1.admin as admin_mod
    import app.api.v1.questions_admin as q_admin_mod
    import app.api.v1.analytics_admin as an_admin_mod
    import app.api.v1.auth as auth_mod
    import app.api.v1.users as users_mod
    import app.api.v1.game as game_mod
    import app.api.v1.battle as battle_mod

    # Admin routers
    assert "get_admin_db" in inspect.getsource(admin_mod)
    assert "get_admin_db" in inspect.getsource(q_admin_mod)
    assert "get_admin_db" in inspect.getsource(an_admin_mod)

    # Player routers
    for mod in [auth_mod, users_mod, game_mod, battle_mod]:
        src = inspect.getsource(mod)
        assert "get_player_db" in src or "get_db" in src
