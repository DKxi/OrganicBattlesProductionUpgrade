#!/usr/bin/env python3
"""
Batch Ingest Question Banks into PostgreSQL / SQLite.
Preserves strict order_index from JSON arrays to match battle cursor progression.
"""
import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.infrastructure.database.engine import SessionLocal, get_active_engine
from app.infrastructure.database.models import Base, Curriculum, Track, Question
from app.infrastructure.database.tracks_repo import TracksRepository
from app.domain.content.loader import _slug
from app.domain.content.validator import validate_question_payload, QuestionValidationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("organicbattles.ingest")


def sync_tracks_if_needed(db, root_dir: Path):
    """Ensure curricula and tracks exist in the database before ingesting questions."""
    repo = TracksRepository(db)
    cfg = repo.get_tracks_config()
    if not cfg.get("tracks"):
        config_path = root_dir / "data" / "tracks_config.json"
        if config_path.is_file():
            logger.info("Database tracks table is empty. Syncing from %s...", config_path)
            raw_cfg = json.loads(config_path.read_text(encoding="utf-8"))
            repo.save_tracks_config(raw_cfg)


def ingest_questions_data(
    db,
    target_track_id: Optional[str] = None,
    root_dir: Optional[Path] = None,
    batch_size: int = 1000,
) -> Dict[str, Any]:
    """
    Ingest questions from JSON files into the active database session.
    Preserves strict sequential order_index per (track_id, chapter, boss_slug).
    """
    root = root_dir or ROOT_DIR
    sync_tracks_if_needed(db, root)

    query = db.query(Track)
    if target_track_id:
        query = query.filter(Track.id == target_track_id)
    tracks = query.order_by(Track.display_order.asc()).all()

    if not tracks:
        logger.warning("No tracks found to ingest questions for.")
        return {"total_questions": 0, "tracks_processed": 0}

    total_ingested = 0
    tracks_processed = 0

    for track in tracks:
        folder_str = track.data_folder
        track_dir = Path(folder_str) if Path(folder_str).is_absolute() else root / folder_str
        
        # Fallback to data/tracks/default if specified folder doesn't exist
        if not track_dir.is_dir() or not list(track_dir.glob("chapter_*.json")):
            fallback_dir = root / "data" / "tracks" / "default"
            if fallback_dir.is_dir() and list(fallback_dir.glob("chapter_*.json")):
                track_dir = fallback_dir
            else:
                track_dir = root / "data"

        chapter_files = list(track_dir.glob("chapter_*.json"))
        if not chapter_files:
            logger.warning("No chapter_*.json found for track '%s' in %s", track.id, track_dir)
            continue

        # Sort chapter files numerically: extract integer from filename
        def _extract_ch_num(f: Path) -> int:
            stem = f.stem.replace("chapter_", "")
            try:
                return int(stem)
            except ValueError:
                return 999

        chapter_files.sort(key=_extract_ch_num)
        logger.info("Ingesting track '%s' from %s (%d files)...", track.id, track_dir, len(chapter_files))

        from app.infrastructure.database.releases_repo import ReleasesRepository
        from app.infrastructure.cache.shared_cache import shared_track_cache
        db.query(Question).filter(Question.track_id == track.id).delete()
        db.commit()

        releases_repo = ReleasesRepository(db)
        draft_rel = releases_repo.create_draft_release(track.id)

        buffer: List[Dict[str, Any]] = []
        track_q_count = 0
        now_ts = int(time.time())

        for ch_file in chapter_files:
            try:
                payload = json.loads(ch_file.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.error("Failed to parse JSON %s: %s", ch_file, exc)
                continue

            ch_num = int(payload.get("chapter", _extract_ch_num(ch_file)))
            ch_title = payload.get("chapter_title", f"Chapter {ch_num}")
            default_boss = payload.get("assigned_boss", "Organic Chemistry Boss")
            raw_questions = payload.get("questions", [])

            for current_order, q_data in enumerate(raw_questions):
                boss_name = q_data.get("boss") or default_boss
                boss_slug = _slug(boss_name)

                choices = [opt.get("text", "") for opt in q_data.get("options", []) if isinstance(opt, dict)]
                correct_ans = q_data.get("correct_answer", choices[0] if choices else "")

                options_list = q_data.get("options", [])
                spells_list = q_data.get("spells", [20, 30, 45])
                health_list = q_data.get("health", [100])
                images_list = q_data.get("images", [f"{boss_slug}.png"])

                v_opts, v_c_opt, v_c_ans, v_spells, v_health, v_images = validate_question_payload(
                    options=options_list,
                    correct_option=str(q_data.get("correct_option", "A")),
                    correct_answer=str(correct_ans),
                    spells=spells_list,
                    health=health_list,
                    images=images_list,
                )

                buffer.append({
                    "track_id": track.id,
                    "release_id": draft_rel.id,
                    "raw_id": str(q_data.get("id", f"ch{ch_num:02d}_q{current_order:03d}")),
                    "chapter": ch_num,
                    "chapter_title": ch_title,
                    "boss_name": boss_name,
                    "boss_slug": boss_slug,
                    "order_index": current_order,  # STRICT SEQUENTIAL ORDER
                    "topic": q_data.get("topic", "Organic Chemistry"),
                    "difficulty": q_data.get("difficulty", "Medium"),
                    "question_type": q_data.get("question_type", "Multiple Choice"),
                    "prompt": q_data.get("question", ""),
                    "options_json": v_opts,
                    "correct_option": v_c_opt,
                    "correct_answer": v_c_ans,
                    "explanation": str(q_data.get("explanation", "Review the concept carefully.")),
                    "spells_json": v_spells,
                    "health_json": v_health,
                    "images_json": v_images,
                    "created_at": now_ts,
                    "updated_at": now_ts,
                })

                if len(buffer) >= batch_size:
                    db.bulk_insert_mappings(Question, buffer)
                    db.commit()
                    track_q_count += len(buffer)
                    buffer.clear()

        if buffer:
            db.bulk_insert_mappings(Question, buffer)
            db.commit()
            track_q_count += len(buffer)
            buffer.clear()

        # Validate count before atomic activation
        if track_q_count > 0:
            releases_repo.publish_release(draft_rel.id)
            track.questions = track_q_count
            track.chapters = len(chapter_files)
            db.commit()
            shared_track_cache.invalidate_track(track.id)
            logger.info("Track '%s' atomically activated under release %s (%d questions).", track.id, draft_rel.id, track_q_count)
        else:
            logger.warning("Track '%s' yielded 0 questions; draft %s discarded.", track.id, draft_rel.id)

        total_ingested += track_q_count
        tracks_processed += 1

    logger.info("Total ingested across %d tracks: %d questions.", tracks_processed, total_ingested)
    return {"total_questions": total_ingested, "tracks_processed": tracks_processed}


def main():
    parser = argparse.ArgumentParser(description="Batch Ingest Question Banks to Database")
    parser.add_argument("--track", type=str, default=None, help="Optional track ID to ingest (default: all)")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch insert size (default: 1000)")
    args = parser.parse_args()

    engine = get_active_engine()
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        stats = ingest_questions_data(db, target_track_id=args.track, batch_size=args.batch_size)
        print(f"Ingestion complete: {stats['total_questions']} questions across {stats['tracks_processed']} tracks.")


if __name__ == "__main__":
    main()
