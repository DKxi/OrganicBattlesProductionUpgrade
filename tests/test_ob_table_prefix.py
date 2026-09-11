"""
Unit and integration tests verifying all database table names and foreign keys use the 'OB_' prefix.
"""
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.infrastructure.database.models import (
    Base,
    User,
    VerificationCode,
    AuthSession,
    GameSession,
    Curriculum,
    Track,
    Question,
    ContentRelease,
    Boss,
    BossQuestionAssignment,
    PlayerQuestionProgress,
    AnswerAttempt,
    AdminUser,
    AdminSession,
    AdminAuditLog,
)
from app.infrastructure.database.engine import _migrate_legacy_table_names, SessionLocal


EXPECTED_OB_TABLES = {
    "OB_users",
    "OB_verification_codes",
    "OB_auth_sessions",
    "OB_game_sessions",
    "OB_curricula",
    "OB_tracks",
    "OB_questions",
    "OB_content_releases",
    "OB_bosses",
    "OB_boss_question_assignments",
    "OB_player_question_progress",
    "OB_answer_attempts",
    "OB_admin_users",
    "OB_admin_sessions",
    "OB_admin_audit_logs",
}


def test_all_models_have_ob_prefix():
    """Verify all declarative models have __tablename__ prefixed with 'OB_'."""
    models = [
        User,
        VerificationCode,
        AuthSession,
        GameSession,
        Curriculum,
        Track,
        Question,
        ContentRelease,
        Boss,
        BossQuestionAssignment,
        PlayerQuestionProgress,
        AnswerAttempt,
        AdminUser,
        AdminSession,
        AdminAuditLog,
    ]
    for model in models:
        table_name = model.__tablename__
        assert table_name.startswith("OB_"), f"Model {model.__name__} has un-prefixed table name: {table_name}"
        assert table_name in EXPECTED_OB_TABLES

    # Check Base metadata table collection
    assert set(Base.metadata.tables.keys()) == EXPECTED_OB_TABLES



def test_foreign_key_references_use_ob_prefix():
    """Verify all ForeignKey definitions reference tables with 'OB_' prefix."""
    for table_name, table in Base.metadata.tables.items():
        assert table_name.startswith("OB_")
        for fk in table.foreign_keys:
            target_table = fk.column.table.name
            assert target_table.startswith("OB_"), f"ForeignKey in {table_name} targets un-prefixed table {target_table}"


def test_auto_migration_renames_legacy_tables(tmp_path):
    """Verify _migrate_legacy_table_names renames old tables to OB_ without data loss."""
    test_db = tmp_path / "legacy_test.sqlite3"
    eng = create_engine(f"sqlite:///{test_db}")

    # 1. Create legacy un-prefixed tables
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT, email TEXT);"))
        conn.execute(text("INSERT INTO users (id, username, email) VALUES ('u1', 'test_user', 'u1@example.com');"))
        conn.execute(text("CREATE TABLE tracks (id TEXT PRIMARY KEY, title TEXT);"))
        conn.execute(text("INSERT INTO tracks (id, title) VALUES ('track_1', 'Intro Track');"))

    # 2. Run rename migration
    _migrate_legacy_table_names(eng)

    # 3. Assert tables were renamed and data preserved
    with eng.begin() as conn:
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        assert "OB_users" in tables
        assert "users" not in tables
        assert "OB_tracks" in tables
        assert "tracks" not in tables

        user_row = conn.execute(text("SELECT id, username FROM OB_users WHERE id='u1'")).fetchone()
        assert user_row[0] == "u1"
        assert user_row[1] == "test_user"

    eng.dispose()


def test_active_database_has_only_ob_tables():
    """Verify that the active database contains OB_ tables and no un-prefixed tables."""
    from app.infrastructure.database.engine import engine
    with engine.connect() as conn:
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        assert EXPECTED_OB_TABLES.issubset(tables)
        # Ensure no legacy un-prefixed versions exist
        legacy_tables = {"users", "verification_codes", "auth_sessions", "game_sessions", "curricula", "tracks", "questions"}
        for leg in legacy_tables:
            assert leg not in tables, f"Legacy table {leg} should not exist in active database"

    with SessionLocal() as db:
        track_count = db.query(Track).count()
        curricula_count = db.query(Curriculum).count()
        assert track_count == 20
        assert curricula_count >= 2


def test_workspace_sqlite_database_has_only_ob_tables():
    """Verify that organic_battles.sqlite3 has all 7 tables with OB_ prefix and rows preserved."""
    import sqlite3
    root_db = Path("organic_battles.sqlite3")
    if root_db.is_file():
        conn = sqlite3.connect(str(root_db))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        assert EXPECTED_OB_TABLES.issubset(tables)
        for leg in ["users", "verification_codes", "auth_sessions", "game_sessions", "curricula", "tracks", "questions"]:
            assert leg not in tables

        cursor.execute("SELECT COUNT(*) FROM OB_questions;")
        q_count = cursor.fetchone()[0]
        assert q_count >= 27000
        conn.close()
