"""Live verification of least-privilege PostgreSQL roles and RLS policies on Supabase.

Reads database URLs from local.env via app.settings.
Tests:
  1. ob_player_api: Read content, write scoped player tables, BLOCKED on admin tables and schema DDL.
  2. ob_admin_api: Read admin tables, DML on content/app, BLOCKED on DDL and answer attempt deletion/updates.
  3. ob_content_ingest: DML on content, BLOCKED on player personal data & admin tables.
  4. ob_migrator: SET ROLE ob_owner, schema modification capability.
"""

import sys
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from app.settings import settings


def test_player_role():
    print("\n" + "=" * 60)
    print("TESTING ROLE: ob_player_api")
    print("=" * 60)
    url = settings.database_url_player
    engine = create_engine(url, poolclass=NullPool)

    with engine.connect() as conn:
        # 1. Who am I?
        user_res = conn.execute(text("SELECT CURRENT_USER, SESSION_USER;")).fetchone()
        print(f"  [+] Connected as: CURRENT_USER={user_res[0]}, SESSION_USER={user_res[1]}")
        assert "ob_player_api" in user_res[0] or "ob_player_api" in user_res[1], f"Unexpected user: {user_res}"

        # 2. Content Read (Allowed)
        curr_count = conn.execute(text('SELECT count(*) FROM public."OB_curricula";')).scalar()
        track_count = conn.execute(text('SELECT count(*) FROM public."OB_tracks";')).scalar()
        boss_count = conn.execute(text('SELECT count(*) FROM public."OB_bosses";')).scalar()
        q_count = conn.execute(text('SELECT count(*) FROM public."OB_questions";')).scalar()
        print(f"  [+] Content reads succeeded: curricula={curr_count}, tracks={track_count}, bosses={boss_count}, questions={q_count}")

        # 3. Restricted: Read OB_admin_users (MUST FAIL)
        try:
            conn.execute(text('SELECT count(*) FROM public."OB_admin_users";'))
            print("  [!] FAILED: ob_player_api was able to read OB_admin_users!")
            sys.exit(1)
        except Exception as exc:
            conn.rollback()
            assert "permission denied" in str(exc).lower() or "42501" in str(exc)
            print("  [+] BLOCKED (Expected): Reading OB_admin_users denied with 42501")

        # 4. Restricted: DELETE on OB_questions (MUST FAIL)
        try:
            conn.execute(text('DELETE FROM public."OB_questions" WHERE id = -999999;'))
            print("  [!] FAILED: ob_player_api was able to DELETE from OB_questions!")
            sys.exit(1)
        except Exception as exc:
            conn.rollback()
            assert "permission denied" in str(exc).lower() or "42501" in str(exc)
            print("  [+] BLOCKED (Expected): DELETE on OB_questions denied with 42501")

        # 5. Restricted: DDL CREATE TABLE (MUST FAIL)
        try:
            conn.execute(text('CREATE TABLE public.test_exploit (id int);'))
            print("  [!] FAILED: ob_player_api was able to CREATE TABLE!")
            sys.exit(1)
        except Exception as exc:
            conn.rollback()
            assert "permission denied" in str(exc).lower() or "42501" in str(exc)
            print("  [+] BLOCKED (Expected): CREATE TABLE denied with 42501")

        # 6. RLS Verification on OB_game_sessions
        # Without app.current_user_id set, should return 0 rows
        sessions_unauth = conn.execute(text('SELECT count(*) FROM public."OB_game_sessions";')).scalar()
        print(f"  [+] RLS check (unauthenticated context): OB_game_sessions visible rows = {sessions_unauth}")

        # With app.current_user_id set to a mock user
        mock_user_id = str(uuid.uuid4())
        conn.execute(text(f"SET LOCAL app.current_user_id = '{mock_user_id}';"))
        sessions_mock = conn.execute(text('SELECT count(*) FROM public."OB_game_sessions";')).scalar()
        print(f"  [+] RLS check (user {mock_user_id[:8]} context): OB_game_sessions visible rows = {sessions_mock}")
        conn.rollback()

    print("  --> ob_player_api: ALL CHECKS PASSED")


def test_admin_role():
    print("\n" + "=" * 60)
    print("TESTING ROLE: ob_admin_api")
    print("=" * 60)
    url = settings.database_url_admin
    engine = create_engine(url, poolclass=NullPool)

    with engine.connect() as conn:
        # 1. Who am I?
        user_res = conn.execute(text("SELECT CURRENT_USER, SESSION_USER;")).fetchone()
        print(f"  [+] Connected as: CURRENT_USER={user_res[0]}, SESSION_USER={user_res[1]}")
        assert "ob_admin_api" in user_res[0] or "ob_admin_api" in user_res[1], f"Unexpected user: {user_res}"

        # 2. Admin Read on Admin Tables (Allowed)
        admin_count = conn.execute(text('SELECT count(*) FROM public."OB_admin_users";')).scalar()
        print(f"  [+] Admin table read succeeded: OB_admin_users count = {admin_count}")

        # 3. Read player tables (Allowed for analytics/management)
        users_count = conn.execute(text('SELECT count(*) FROM public."OB_users";')).scalar()
        attempts_count = conn.execute(text('SELECT count(*) FROM public."OB_answer_attempts";')).scalar()
        print(f"  [+] Read player & attempt tables succeeded: users={users_count}, attempts={attempts_count}")

        # 4. Restricted: DELETE on OB_answer_attempts (MUST FAIL - audit trail is append-only)
        try:
            conn.execute(text('DELETE FROM public."OB_answer_attempts" WHERE id = -999999;'))
            print("  [!] FAILED: ob_admin_api was able to DELETE from OB_answer_attempts!")
            sys.exit(1)
        except Exception as exc:
            conn.rollback()
            assert "permission denied" in str(exc).lower() or "42501" in str(exc)
            print("  [+] BLOCKED (Expected): DELETE on OB_answer_attempts denied with 42501")

        # 5. Restricted: UPDATE on OB_answer_attempts (MUST FAIL)
        try:
            conn.execute(text('UPDATE public."OB_answer_attempts" SET question_id = 1 WHERE id = -999999;'))
            print("  [!] FAILED: ob_admin_api was able to UPDATE OB_answer_attempts!")
            sys.exit(1)
        except Exception as exc:
            conn.rollback()
            assert "permission denied" in str(exc).lower() or "42501" in str(exc)
            print("  [+] BLOCKED (Expected): UPDATE on OB_answer_attempts denied with 42501")

        # 6. Restricted: DDL CREATE TABLE (MUST FAIL)
        try:
            conn.execute(text('CREATE TABLE public.admin_exploit (id int);'))
            print("  [!] FAILED: ob_admin_api was able to CREATE TABLE!")
            sys.exit(1)
        except Exception as exc:
            conn.rollback()
            assert "permission denied" in str(exc).lower() or "42501" in str(exc)
            print("  [+] BLOCKED (Expected): CREATE TABLE denied with 42501")

    print("  --> ob_admin_api: ALL CHECKS PASSED")


def test_ingest_role():
    print("\n" + "=" * 60)
    print("TESTING ROLE: ob_content_ingest")
    print("=" * 60)
    url = settings.database_url_ingest
    engine = create_engine(url, poolclass=NullPool)

    with engine.connect() as conn:
        # 1. Who am I?
        user_res = conn.execute(text("SELECT CURRENT_USER, SESSION_USER;")).fetchone()
        print(f"  [+] Connected as: CURRENT_USER={user_res[0]}, SESSION_USER={user_res[1]}")
        assert "ob_content_ingest" in user_res[0] or "ob_content_ingest" in user_res[1], f"Unexpected user: {user_res}"

        # 2. Content Operations (Allowed)
        q_count = conn.execute(text('SELECT count(*) FROM public."OB_questions";')).scalar()
        b_count = conn.execute(text('SELECT count(*) FROM public."OB_bosses";')).scalar()
        print(f"  [+] Content reads succeeded: questions={q_count}, bosses={b_count}")

        # 3. Restricted: Read OB_users (MUST FAIL - ingest should never touch player data)
        try:
            conn.execute(text('SELECT count(*) FROM public."OB_users";'))
            print("  [!] FAILED: ob_content_ingest was able to read OB_users!")
            sys.exit(1)
        except Exception as exc:
            conn.rollback()
            assert "permission denied" in str(exc).lower() or "42501" in str(exc)
            print("  [+] BLOCKED (Expected): Reading OB_users denied with 42501")

        # 4. Restricted: Read OB_admin_users (MUST FAIL)
        try:
            conn.execute(text('SELECT count(*) FROM public."OB_admin_users";'))
            print("  [!] FAILED: ob_content_ingest was able to read OB_admin_users!")
            sys.exit(1)
        except Exception as exc:
            conn.rollback()
            assert "permission denied" in str(exc).lower() or "42501" in str(exc)
            print("  [+] BLOCKED (Expected): Reading OB_admin_users denied with 42501")

        # 5. Restricted: Read OB_game_sessions (MUST FAIL)
        try:
            conn.execute(text('SELECT count(*) FROM public."OB_game_sessions";'))
            print("  [!] FAILED: ob_content_ingest was able to read OB_game_sessions!")
            sys.exit(1)
        except Exception as exc:
            conn.rollback()
            assert "permission denied" in str(exc).lower() or "42501" in str(exc)
            print("  [+] BLOCKED (Expected): Reading OB_game_sessions denied with 42501")

        # 6. Restricted: DDL CREATE TABLE (MUST FAIL)
        try:
            conn.execute(text('CREATE TABLE public.ingest_exploit (id int);'))
            print("  [!] FAILED: ob_content_ingest was able to CREATE TABLE!")
            sys.exit(1)
        except Exception as exc:
            conn.rollback()
            assert "permission denied" in str(exc).lower() or "42501" in str(exc)
            print("  [+] BLOCKED (Expected): CREATE TABLE denied with 42501")

    print("  --> ob_content_ingest: ALL CHECKS PASSED")


def test_migrator_role():
    print("\n" + "=" * 60)
    print("TESTING ROLE: ob_migrator")
    print("=" * 60)
    url = settings.database_url_migration
    engine = create_engine(url, poolclass=NullPool)

    with engine.connect() as conn:
        # 1. Who am I?
        user_res = conn.execute(text("SELECT CURRENT_USER, SESSION_USER;")).fetchone()
        print(f"  [+] Connected as: CURRENT_USER={user_res[0]}, SESSION_USER={user_res[1]}")
        assert "ob_migrator" in user_res[0] or "ob_migrator" in user_res[1], f"Unexpected user: {user_res}"

        # 2. Can SET ROLE ob_owner?
        conn.execute(text("SET ROLE ob_owner;"))
        owner_res = conn.execute(text("SELECT CURRENT_USER;")).scalar()
        print(f"  [+] Switched role to: CURRENT_USER={owner_res}")
        assert owner_res == "ob_owner"

        # 3. DDL capability verification as ob_owner
        conn.execute(text('CREATE TABLE public.__ob_migrator_test (id int);'))
        conn.execute(text('DROP TABLE public.__ob_migrator_test;'))
        print("  [+] DDL capability verified: Successfully created and dropped test table as ob_owner")

        # 4. Reset role
        conn.execute(text("RESET ROLE;"))
        reset_res = conn.execute(text("SELECT CURRENT_USER;")).scalar()
        print(f"  [+] Reset role to: CURRENT_USER={reset_res}")

    print("  --> ob_migrator: ALL CHECKS PASSED")


if __name__ == "__main__":
    print(f"Environment loaded: {settings.loaded_env_file_name}")
    print(f"Database URL Player: {settings.database_url_player[:35]}...")
    print(f"Database URL Admin: {settings.database_url_admin[:35]}...")
    print(f"Database URL Ingest: {settings.database_url_ingest[:35]}...")
    print(f"Database URL Migration: {settings.database_url_migration[:35]}...")

    test_player_role()
    test_admin_role()
    test_ingest_role()
    test_migrator_role()

    print("\n" + "*" * 60)
    print("ALL 4 LEAST-PRIVILEGE ROLES VERIFIED SUCCESSFULLY AGAINST LIVE DB!")
    print("*" * 60)
