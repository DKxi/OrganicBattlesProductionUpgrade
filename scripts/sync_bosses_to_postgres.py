#!/usr/bin/env python3
"""
Sync Bosses and Question Assignments to Database
------------------------------------------------
Scans ingested questions in OB_questions and populates:
1. OB_bosses: Unique boss entities with slug, name, health, element, chapter, and sequential order_index.
2. OB_boss_question_assignments: Relational question-to-boss mappings.

Uses role ob_content_ingest (or DATABASE_URL_INGEST) with NullPool.
"""
import sys
import argparse
import logging
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.settings import settings
from app.infrastructure.database.engine import build_engine
from app.infrastructure.database.bosses_repo import BossesRepository
from app.infrastructure.database.models import Track

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("organicbattles.sync_bosses")


def sync_bosses(target_track_id: str = None) -> dict:
    ingest_url = settings.database_url_ingest or settings.database_url
    logger.info("Connecting to database via %s...", ingest_url.split("@")[-1] if "@" in ingest_url else ingest_url)
    engine = build_engine(ingest_url, poolclass=NullPool)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    total_bosses = 0
    total_assignments = 0
    tracks_processed = 0

    try:
        with Session() as db:
            bosses_repo = BossesRepository(db)

            if target_track_id:
                track_ids = [target_track_id]
            else:
                db_tracks = db.query(Track).order_by(Track.id.asc()).all()
                track_ids = [t.id for t in db_tracks] if db_tracks else ["default"]

            for t_id in track_ids:
                logger.info("Synchronizing bosses for track '%s'...", t_id)
                res = bosses_repo.sync_bosses_from_questions(track_id=t_id)
                logger.info("Track '%s': %d bosses, %d question assignments synced.", t_id, res["bosses"], res["assignments"])
                total_bosses += res["bosses"]
                total_assignments += res["assignments"]
                tracks_processed += 1

        return {
            "tracks_processed": tracks_processed,
            "total_bosses": total_bosses,
            "total_assignments": total_assignments,
        }
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Synchronize OB_bosses and question assignments from OB_questions")
    parser.add_argument("--track", type=str, default=None, help="Optional track ID (default: all tracks in DB)")
    args = parser.parse_args()

    stats = sync_bosses(target_track_id=args.track)
    print("\n" + "=" * 60)
    print("BOSS SYNCHRONIZATION COMPLETE")
    print(f"Tracks Processed: {stats['tracks_processed']}")
    print(f"Total Bosses in OB_bosses: {stats['total_bosses']}")
    print(f"Total Assignments in OB_boss_question_assignments: {stats['total_assignments']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
