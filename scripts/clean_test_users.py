#!/usr/bin/env python3
"""
Clean test users and their cascading records (auth_sessions, game_sessions, verification_codes)
from OB_users table in SQLite and PostgreSQL.
Preserves real non-test accounts (e.g., w84nbk).
"""
import sys
import argparse
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import text
from app.infrastructure.database.engine import build_engine, normalize_db_url
from app.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("organicbattles.cleanup")


def clean_test_users(db_url: str) -> int:
    """Remove test users and associated child rows from the target database."""
    normalized = normalize_db_url(db_url)
    engine = build_engine(normalized)
    deleted_count = 0

    with engine.begin() as conn:
        # Fetch test user IDs
        # Test users are those with test patterns in username/email, or not the genuine account
        query = text("""
            SELECT id, username, email FROM "OB_users"
            WHERE LOWER(username) LIKE 'test%'
               OR LOWER(username) LIKE 'tester_%'
               OR LOWER(username) LIKE 'user%'
               OR LOWER(username) LIKE 'custom_%'
               OR LOWER(username) LIKE 'relogin_%'
               OR LOWER(username) LIKE 'dup_%'
               OR LOWER(username) LIKE 'wizard_%'
               OR LOWER(username) LIKE 'renamed%'
               OR LOWER(username) LIKE 'default_user_%'
               OR LOWER(username) LIKE 'gate_user_%'
               OR LOWER(username) LIKE 'persist_%'
               OR LOWER(username) LIKE 'track_user_%'
               OR LOWER(username) LIKE 'sys_test%'
               OR LOWER(email) LIKE '%@alchemical.edu'
               OR LOWER(email) LIKE '%@example.com'
        """)
        test_users = conn.execute(query).fetchall()
        logger.info("Identified %d test users to remove.", len(test_users))

        if not test_users:
            return 0

        user_ids = [u[0] for u in test_users]

        # Clean child records for these user IDs
        # 1. Verification codes
        del_codes = conn.execute(
            text('DELETE FROM "OB_verification_codes" WHERE user_id = ANY(:uids)') if engine.dialect.name == "postgresql"
            else text(f'DELETE FROM "OB_verification_codes" WHERE user_id IN ({",".join([repr(u) for u in user_ids])})')
            , {"uids": user_ids} if engine.dialect.name == "postgresql" else {}
        )
        logger.info("Deleted %s rows from OB_verification_codes", del_codes.rowcount)

        # 2. Auth sessions
        del_auth = conn.execute(
            text('DELETE FROM "OB_auth_sessions" WHERE user_id = ANY(:uids)') if engine.dialect.name == "postgresql"
            else text(f'DELETE FROM "OB_auth_sessions" WHERE user_id IN ({",".join([repr(u) for u in user_ids])})')
            , {"uids": user_ids} if engine.dialect.name == "postgresql" else {}
        )
        logger.info("Deleted %s rows from OB_auth_sessions", del_auth.rowcount)

        # 3. Game sessions
        del_game = conn.execute(
            text('DELETE FROM "OB_game_sessions" WHERE user_id = ANY(:uids)') if engine.dialect.name == "postgresql"
            else text(f'DELETE FROM "OB_game_sessions" WHERE user_id IN ({",".join([repr(u) for u in user_ids])})')
            , {"uids": user_ids} if engine.dialect.name == "postgresql" else {}
        )
        logger.info("Deleted %s rows from OB_game_sessions", del_game.rowcount)

        # 4. Users
        del_users = conn.execute(
            text('DELETE FROM "OB_users" WHERE id = ANY(:uids)') if engine.dialect.name == "postgresql"
            else text(f'DELETE FROM "OB_users" WHERE id IN ({",".join([repr(u) for u in user_ids])})')
            , {"uids": user_ids} if engine.dialect.name == "postgresql" else {}
        )
        deleted_count = del_users.rowcount
        logger.info("Deleted %d test user accounts from OB_users.", deleted_count)

        # Print remaining users
        remaining = conn.execute(text('SELECT id, username, email FROM "OB_users";')).fetchall()
        logger.info("Remaining accounts in OB_users (%d): %s", len(remaining), remaining)

    return deleted_count


def main():
    parser = argparse.ArgumentParser(description="Remove test users from OB_users.")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL")
    args = parser.parse_args()

    target_url = args.db_url or settings.database_url
    print(f"Target Database: {target_url.split('@')[-1] if '@' in target_url else target_url}")
    deleted = clean_test_users(target_url)
    print(f"Cleaned {deleted} test users successfully.")


if __name__ == "__main__":
    main()
