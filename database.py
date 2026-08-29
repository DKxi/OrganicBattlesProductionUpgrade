import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT = Path(__file__).parent
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    db_path = os.getenv("DATABASE_PATH", str(ROOT / "organic_battles.sqlite3"))
    # Ensure correct format for SQLite URL
    DATABASE_URL = f"sqlite:///{db_path}"

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30.0}

# pool_pre_ping=True ensures we discard stale DB connections before using them
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
