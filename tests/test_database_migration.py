import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.infrastructure.database.models import (
    Base,
    User,
    VerificationCode,
    AuthSession,
    GameSession,
)
from app.infrastructure.database.engine import build_engine
from app.infrastructure.database.migrator import migrate_sqlite_to_postgres, migrate_database
from tests.test_database_connection import get_database_env, resolve_postgres_url


def test_sqlite_to_sqlite_migration_all_tables_and_idempotency(tmp_path):
    """Verify that user, code, auth session, and game session data migrate cleanly between engines."""
    src_path = tmp_path / "source.sqlite3"
    dst_path = tmp_path / "target.sqlite3"
    src_url = f"sqlite:///{src_path}"
    dst_url = f"sqlite:///{dst_path}"

    src_engine = build_engine(src_url)
    dst_engine = build_engine(dst_url)

    # 1. Populate source database
    Base.metadata.create_all(bind=src_engine)
    with Session(src_engine) as src:
        u1 = User(
            id="u_mig_1",
            email="u1@example.com",
            username="wizard_one",
            password_hash="scrypt:abc:123",
            verified=1,
            content_source="adv-vocab",
            avatar_json='{"level": 5}',
            progress_json='{"tracks": {"adv-vocab": {"chapter": 3}}}',
        )
        u2 = User(
            id="u_mig_2",
            email="u2@example.com",
            username="wizard_two",
            password_hash="scrypt:def:456",
            verified=0,
        )
        src.add_all([u1, u2])
        src.commit()

        # Verification codes
        vc1 = VerificationCode(
            id=10,
            user_id="u_mig_1",
            code_hash="hash_code_1",
            expires_at=9999999999,
            used=0,
        )
        src.add(vc1)

        # Auth sessions
        s1 = AuthSession(
            token_hash="sess_hash_1",
            user_id="u_mig_1",
            expires_at=9999999999,
        )
        src.add(s1)

        # Game sessions
        gs1 = GameSession(
            id="gs_mig_1",
            user_id="u_mig_1",
            content_source="adv-vocab",
            chapter=3,
            boss_index=1,
            player_hp=120,
            player_max_hp=150,
            boss_hp=80,
            log_json='["Turn 1: Fireball"]',
            completed_json='["boss_1"]',
        )
        src.add(gs1)
        src.commit()

    # 2. Run migration
    stats = migrate_sqlite_to_postgres(src_engine, dst_engine)
    assert stats["users"] == 2
    assert stats["verification_codes"] == 1
    assert stats["auth_sessions"] == 1
    assert stats["game_sessions"] == 1

    # 3. Verify destination records
    with Session(dst_engine) as dst:
        users = dst.query(User).order_by(User.id).all()
        assert len(users) == 2
        assert users[0].id == "u_mig_1"
        assert users[0].email == "u1@example.com"
        assert users[0].progress_json == '{"tracks": {"adv-vocab": {"chapter": 3}}}'
        assert users[1].username == "wizard_two"

        codes = dst.query(VerificationCode).all()
        assert len(codes) == 1
        assert codes[0].user_id == "u_mig_1"
        assert codes[0].code_hash == "hash_code_1"

        sessions = dst.query(AuthSession).all()
        assert len(sessions) == 1
        assert sessions[0].token_hash == "sess_hash_1"

        games = dst.query(GameSession).all()
        assert len(games) == 1
        assert games[0].id == "gs_mig_1"
        assert games[0].chapter == 3
        assert games[0].boss_hp == 80

    # 4. Idempotency test: Re-running migration should succeed without duplicates
    stats_second = migrate_sqlite_to_postgres(src_engine, dst_engine)
    assert stats_second["users"] == 0  # No new users added
    assert stats_second["verification_codes"] == 0
    assert stats_second["auth_sessions"] == 0
    assert stats_second["game_sessions"] == 0

    with Session(dst_engine) as dst:
        assert dst.query(User).count() == 2
        assert dst.query(VerificationCode).count() == 1
        assert dst.query(AuthSession).count() == 1
        assert dst.query(GameSession).count() == 1

    src_engine.dispose()
    dst_engine.dispose()


def test_sqlite_to_supabase_postgresql_migration(tmp_path):
    """Test copying local records directly into Supabase PostgreSQL."""
    values = get_database_env()
    db_url = values.get("DATABASE_URL")
    if not db_url or "postgresql" not in db_url.lower():
        pytest.skip("PostgreSQL not configured in env file")

    resolved_url = resolve_postgres_url(db_url)
    pg_engine = build_engine(resolved_url)

    src_path = tmp_path / "live_src.sqlite3"
    src_engine = build_engine(f"sqlite:///{src_path}")
    Base.metadata.create_all(bind=src_engine)

    test_user_id = "test_pg_mig_user"
    with Session(src_engine) as src:
        u = User(
            id=test_user_id,
            email="pg_test_mig@example.com",
            username="pg_test_mig_user",
            password_hash="hash_mig",
            verified=1,
        )
        src.add(u)
        src.commit()

    try:
        # Migrate into PostgreSQL
        stats = migrate_sqlite_to_postgres(src_engine, pg_engine)
        assert stats["users"] >= 1

        # Check user in PostgreSQL
        with Session(pg_engine) as dst:
            migrated = dst.query(User).filter_by(id=test_user_id).first()
            assert migrated is not None
            assert migrated.email == "pg_test_mig@example.com"

    finally:
        # Cleanup test user from PostgreSQL to keep database pristine
        with Session(pg_engine) as dst:
            dst.query(User).filter_by(id=test_user_id).delete()
            dst.commit()
        src_engine.dispose()
        pg_engine.dispose()
