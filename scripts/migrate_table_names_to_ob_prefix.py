#!/usr/bin/env python3
"""
CLI script to migrate relational database tables to use 'OB_' prefix.
Renames:
  curricula          -> OB_curricula
  tracks             -> OB_tracks
  questions          -> OB_questions
  users              -> OB_users
  verification_codes -> OB_verification_codes
  auth_sessions      -> OB_auth_sessions
  game_sessions      -> OB_game_sessions
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
logger = logging.getLogger("organicbattles.table_migration")

TABLE_RENAMES = [
    ("curricula", "OB_curricula"),
    ("tracks", "OB_tracks"),
    ("questions", "OB_questions"),
    ("users", "OB_users"),
    ("verification_codes", "OB_verification_codes"),
    ("auth_sessions", "OB_auth_sessions"),
    ("game_sessions", "OB_game_sessions"),
]


def migrate_tables_to_ob_prefix(db_url: str) -> int:
    """Inspect and rename legacy tables to OB_ prefix."""
    normalized = normalize_db_url(db_url)
    engine = build_engine(normalized)
    renamed_count = 0

    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            existing_tables = {
                row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            }
        else:
            existing_tables = {
                row[0] for row in conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                ).fetchall()
            }

        logger.info("Existing database tables: %s", sorted(list(existing_tables)))

        for old_table, new_table in TABLE_RENAMES:
            if old_table in existing_tables and new_table not in existing_tables:
                logger.info("Renaming '%s' -> '%s'...", old_table, new_table)
                conn.execute(text(f'ALTER TABLE "{old_table}" RENAME TO "{new_table}"'))
                renamed_count += 1
            elif new_table in existing_tables:
                logger.info("Table '%s' already exists.", new_table)
            else:
                logger.info("Table '%s' not present, skipping.", old_table)

    logger.info("Table migration complete. %d tables renamed to 'OB_' prefix.", renamed_count)
    return renamed_count


def main():
    parser = argparse.ArgumentParser(description="Rename database tables to OB_ prefix.")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL")
    args = parser.parse_args()

    target_url = args.db_url or settings.database_url
    print(f"Target Database: {target_url.split('@')[-1] if '@' in target_url else target_url}")
    renamed = migrate_tables_to_ob_prefix(target_url)
    print(f"Renamed {renamed} tables to OB_ prefix successfully.")


if __name__ == "__main__":
    main()
