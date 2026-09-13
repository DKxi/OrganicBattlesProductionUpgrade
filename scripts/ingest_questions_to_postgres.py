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

from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker
from app.settings import settings
from app.infrastructure.database.engine import build_engine, SessionLocal
from app.infrastructure.database.models import Base, Curriculum, Track, Question
from app.infrastructure.database.tracks_repo import TracksRepository
from app.domain.content.loader import _slug
from app.domain.content.validator import validate_question_payload, QuestionValidationError
from app.infrastructure.storage.s3_reader import (
    get_s3_client,
    resolve_track_s3_location,
    list_track_chapter_keys,
    get_chapter_json,
    extract_chapter_num_from_key,
)

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
    source: str = "auto",
) -> Dict[str, Any]:
    """
    Ingest questions from S3 buckets (or local JSON fallback) into the active database session.
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

    # Determine whether S3 is active
    use_s3 = False
    s3_client = None
    if source in ("s3", "auto"):
        if settings.s3_access_key_id and settings.s3_secret_access_key:
            try:
                s3_client = get_s3_client()
                use_s3 = True
                logger.info("S3 storage client initialized (Endpoint: %s, Region: %s).", settings.s3_endpoint_url or "AWS", settings.s3_region)
            except Exception as s3_err:
                logger.warning("Could not initialize S3 client (%s). Falling back to local files.", s3_err)
                if source == "s3":
                    raise

    total_ingested = 0
    tracks_processed = 0

    for track in tracks:
        chapter_payloads: List[Dict[str, Any]] = []
        source_desc = "unknown"

        if use_s3 and s3_client is not None:
            bucket, prefix = resolve_track_s3_location(track.id, curriculum=track.curriculum_id, data_folder=track.data_folder)
            try:
                keys = list_track_chapter_keys(bucket, prefix=prefix, s3_client=s3_client)
                if keys:
                    source_desc = f"s3://{bucket}/{prefix} ({len(keys)} chapters)"
                    logger.info("Fetching track '%s' chapters from %s...", track.id, source_desc)
                    for k in keys:
                        payload = get_chapter_json(bucket, k, s3_client=s3_client)
                        if "chapter" not in payload:
                            payload["chapter"] = extract_chapter_num_from_key(k)
                        chapter_payloads.append(payload)
            except Exception as s3_fetch_err:
                logger.warning("Error fetching track '%s' from S3 (%s). Checking local fallback...", track.id, s3_fetch_err)

        if not chapter_payloads:
            # Fallback to local data folder
            folder_str = track.data_folder or ""
            track_dir = Path(folder_str) if Path(folder_str).is_absolute() else root / folder_str
            
            # Fallback to data/tracks/default if specified folder doesn't exist
            if not track_dir.is_dir() or not list(track_dir.glob("chapter_*.json")):
                fallback_dir = root / "data" / "tracks" / "default"
                if fallback_dir.is_dir() and list(fallback_dir.glob("chapter_*.json")):
                    track_dir = fallback_dir
                else:
                    track_dir = root / "data"

            local_files = list(track_dir.glob("chapter_*.json"))
            if local_files:
                def _extract_ch_num(f: Path) -> int:
                    stem = f.stem.replace("chapter_", "")
                    try:
                        return int(stem)
                    except ValueError:
                        return 999

                local_files.sort(key=_extract_ch_num)
                source_desc = f"local file://{track_dir} ({len(local_files)} files)"
                logger.info("Fetching track '%s' chapters from %s...", track.id, source_desc)
                for f in local_files:
                    try:
                        p = json.loads(f.read_text(encoding="utf-8"))
                        if "chapter" not in p:
                            p["chapter"] = _extract_ch_num(f)
                        chapter_payloads.append(p)
                    except Exception as exc:
                        logger.error("Failed to parse JSON %s: %s", f, exc)

        if not chapter_payloads:
            logger.warning("No chapters found for track '%s' across S3 and local storage.", track.id)
            continue

        # Sort chapter payloads by chapter number
        chapter_payloads.sort(key=lambda p: int(p.get("chapter", 999)))
        logger.info("Ingesting track '%s' from %s...", track.id, source_desc)

        from app.infrastructure.database.releases_repo import ReleasesRepository
        from app.infrastructure.cache.shared_cache import shared_track_cache
        db.query(Question).filter(Question.track_id == track.id).delete(synchronize_session=False)
        db.commit()

        releases_repo = ReleasesRepository(db)
        draft_rel = releases_repo.create_draft_release(track.id)

        buffer: List[Dict[str, Any]] = []
        track_q_count = 0
        now_ts = int(time.time())

        for payload in chapter_payloads:
            ch_num = int(payload.get("chapter", 1))
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
            track.chapters = len(chapter_payloads)
            db.commit()
            shared_track_cache.invalidate_track(track.id)
            logger.info("Track '%s' atomically activated under release %s (%d questions).", track.id, draft_rel.id, track_q_count)

            # Synchronize OB_bosses and OB_boss_question_assignments
            from app.infrastructure.database.bosses_repo import BossesRepository
            bosses_repo = BossesRepository(db)
            b_stats = bosses_repo.sync_bosses_from_questions(track_id=track.id, release_id=draft_rel.id)
            logger.info("Track '%s': synchronized %d bosses and %d assignments in OB_bosses.", track.id, b_stats["bosses"], b_stats["assignments"])
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
    parser.add_argument("--source", type=str, choices=["auto", "s3", "local"], default="auto", help="Content source: auto, s3, or local (default: auto)")
    args = parser.parse_args()

    ingest_url = settings.database_url_ingest or settings.database_url
    logger.info("Connecting to database for ingestion via role ob_content_ingest (%s)...", ingest_url.split("@")[-1] if "@" in ingest_url else ingest_url)
    engine = build_engine(ingest_url, poolclass=NullPool)
    IngestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    try:
        with IngestSession() as db:
            stats = ingest_questions_data(
                db,
                target_track_id=args.track,
                batch_size=args.batch_size,
                source=args.source,
            )
            print(f"Ingestion complete: {stats['total_questions']} questions across {stats['tracks_processed']} tracks.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
