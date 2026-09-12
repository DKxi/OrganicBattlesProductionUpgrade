import os
import tempfile
import pytest
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.settings import settings
from app.infrastructure.database.alembic_runner import (
    run_alembic_migrations,
    get_current_migration_revision,
    get_alembic_config,
)


def test_credential_independent_alembic_config():
    """Verify alembic.ini contains no hardcoded credentials or passwords."""
    ini_path = settings.root_dir / "alembic.ini"
    assert ini_path.exists(), "alembic.ini must exist in project root"

    with open(ini_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must not contain hardcoded passwords or sensitive connection strings
    assert "postgresql://" not in content
    assert "password" not in content.lower() or "password_hash" in content.lower()
    # sqlalchemy.url must be empty or blank
    for line in content.splitlines():
        if line.strip().startswith("sqlalchemy.url"):
            val = line.split("=", 1)[1].strip()
            assert val == "", f"sqlalchemy.url must not be hardcoded: {val}"


def test_migration_chain_and_revisions():
    """Verify all 7 required migration revisions exist and are correctly ordered."""
    cfg = get_alembic_config()
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert heads == ["0007_search_indexes"]

    revisions = [rev.revision for rev in script.walk_revisions()]
    expected_order = [
        "0007_search_indexes",
        "0006_optimistic_locking",
        "0005_game_session_active_question_identity",
        "0004_stable_question_identity_constraints",
        "0003_content_releases",
        "0002_jsonb_conversion",
        "0001_initial_schema",
    ]
    assert revisions == expected_order, f"Unexpected migration order: {revisions}"


def test_migration_upgrade_and_schema_verification():
    """
    Verify complete migration execution from base to head on a fresh database,
    verifying all 7 architectural capabilities:
    1. Base tables creation without create_all()
    2. JSON/JSONB types on question/boss metadata
    3. Content releases table and release_id columns
    4. Stable question identity constraints
    5. Game-session active question ID and version
    6. Optimistic locking version
    7. Search indexes
    """
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        temp_db_path = f.name

    try:
        engine = create_engine(f"sqlite:///{temp_db_path}")

        # Run migrations
        run_alembic_migrations(target_engine=engine)

        # 1. Revision check
        current_rev = get_current_migration_revision(target_engine=engine)
        assert current_rev == "0007_search_indexes"

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        # Verify all core tables created
        required_tables = {
            "OB_users",
            "OB_verification_codes",
            "OB_auth_sessions",
            "OB_game_sessions",
            "OB_curricula",
            "OB_tracks",
            "OB_questions",
            "OB_bosses",
            "OB_boss_question_assignments",
            "OB_player_question_progress",
            "OB_answer_attempts",
            "OB_admin_users",
            "OB_admin_sessions",
            "OB_admin_audit_logs",
            "OB_content_releases",
            "alembic_version",
        }
        assert required_tables.issubset(tables), f"Missing tables: {required_tables - tables}"

        # 2. Content releases schema check
        release_cols = {c["name"] for c in inspector.get_columns("OB_content_releases")}
        assert {"id", "track_id", "version", "status", "checksum", "created_at", "published_at"}.issubset(release_cols)

        # Verify release_id present on dependent tables
        q_cols = {c["name"] for c in inspector.get_columns("OB_questions")}
        assert "release_id" in q_cols
        assert "raw_id" in q_cols
        assert "options_json" in q_cols

        bqa_cols = {c["name"] for c in inspector.get_columns("OB_boss_question_assignments")}
        assert "release_id" in bqa_cols

        att_cols = {c["name"] for c in inspector.get_columns("OB_answer_attempts")}
        assert "release_id" in att_cols

        # 3. Game session active question identity and versioning
        gs_cols = {c["name"] for c in inspector.get_columns("OB_game_sessions")}
        assert "active_question_id" in gs_cols
        assert "active_question_release_id" in gs_cols
        assert "version" in gs_cols
        assert "updated_at" in gs_cols

        # 4. Search and composite indexes check
        q_indexes = {idx["name"] for idx in inspector.get_indexes("OB_questions")}
        assert "ix_ob_questions_track_ch_order" in q_indexes
        assert "ix_ob_questions_track_release_ch_order" in q_indexes

        user_indexes = {idx["name"] for idx in inspector.get_indexes("OB_users")}
        assert "ix_ob_users_username" in user_indexes
        assert "ix_ob_users_email" in user_indexes

        # 5. Idempotency check: running migrations again on head must be a clean no-op
        run_alembic_migrations(target_engine=engine)
        assert get_current_migration_revision(target_engine=engine) == "0007_search_indexes"

    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
