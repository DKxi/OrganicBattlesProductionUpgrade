import os
import sqlite3
import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as DBSession
from app.settings import settings
from app.infrastructure.database.models import Base

logger = logging.getLogger("organicbattles.database")

# Database engine initialization
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_db_schema() -> None:
    """Ensure database tables exist and SQLite columns are up to date."""
    Base.metadata.create_all(bind=engine)

    if settings.database_url.startswith("sqlite"):
        db_file = settings.database_url.replace("sqlite:///", "")
        if db_file and os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(users)")
                user_cols = [row[1] for row in cursor.fetchall()]
                if "content_source" not in user_cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN content_source TEXT")
                if "progress_json" not in user_cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN progress_json TEXT")

                cursor.execute("PRAGMA table_info(game_sessions)")
                sess_cols = [row[1] for row in cursor.fetchall()]
                if "content_source" not in sess_cols:
                    cursor.execute("ALTER TABLE game_sessions ADD COLUMN content_source TEXT")
                if "turn_id" not in sess_cols:
                    cursor.execute("ALTER TABLE game_sessions ADD COLUMN turn_id TEXT")
                conn.commit()
                conn.close()
            except Exception as e:
                logger.warning("Auto schema migration note: %s", e)


def get_db() -> Generator[DBSession, None, None]:
    """FastAPI dependency yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
