import json
import logging
import time
from typing import Optional, List, Dict, Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_db, auth_admin
from app.infrastructure.database.models import Question, Track
from app.infrastructure.database.releases_repo import ReleasesRepository
from app.infrastructure.cache.shared_cache import shared_track_cache
from app.domain.content.loader import invalidate_bundle_cache

from app.domain.content.validator import validate_question_payload, QuestionValidationError

logger = logging.getLogger("organicbattles.questions_admin")
router = APIRouter(tags=["Admin Questions Management"])


def _to_json_obj(val: Any, default: Any) -> Any:
    if val is None:
        return default
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return default
    return default


class QuestionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: Optional[str] = None
    options: Optional[List[Dict[str, str]]] = None
    correct_option: Optional[str] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    spells: Optional[List[int]] = None
    health: Optional[List[int]] = None
    images: Optional[List[str]] = None


class ReorderQuestionsRequest(BaseModel):
    boss_slug: Optional[str] = Field(None, description="Optional boss slug to scope the reorder operation")
    question_ids: Optional[List[int]] = Field(None, description="Complete ordered permutation of question IDs for this scope")
    move_question_id: Optional[int] = Field(None, description="ID of question to move")
    target_question_id: Optional[int] = Field(None, description="ID of reference question to move before/after")
    position: Optional[Literal["before", "after"]] = Field(None, description="Placement relative to target ('before' or 'after')")


class IngestQuestionsRequest(BaseModel):
    track_id: Optional[str] = None
    batch_size: int = 1000


@router.get("/admin/tracks/{track_id}/questions")
def admin_get_track_questions(
    track_id: str,
    chapter: Optional[int] = Query(None, description="Filter by chapter number"),
    boss_slug: Optional[str] = Query(None, description="Filter by boss slug"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    search: Optional[str] = Query(None, description="Search prompt or topic"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    """Retrieve paginated questions for a specific track, ordered sequentially."""
    query = db.query(Question).filter(Question.track_id == track_id)

    if chapter is not None:
        query = query.filter(Question.chapter == chapter)
    if boss_slug:
        query = query.filter(Question.boss_slug == boss_slug)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            (Question.prompt.ilike(search_filter)) | (Question.topic.ilike(search_filter))
        )

    total = query.count()
    items = (
        query.order_by(Question.chapter.asc(), Question.order_index.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    formatted_items = []
    for q in items:
        opts = _to_json_obj(q.options_json, [])
        spells = _to_json_obj(q.spells_json, [])

        formatted_items.append({
            "id": q.id,
            "track_id": q.track_id,
            "raw_id": q.raw_id,
            "chapter": q.chapter,
            "chapter_title": q.chapter_title,
            "boss_name": q.boss_name,
            "boss_slug": q.boss_slug,
            "order_index": q.order_index,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "question_type": q.question_type,
            "prompt": q.prompt,
            "options": opts,
            "correct_option": q.correct_option,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "spells": spells,
        })

    return {
        "track_id": track_id,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit else 1,
        "items": formatted_items,
    }


@router.get("/admin/questions/{question_id}")
def admin_get_question_by_id(
    question_id: int,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    """Retrieve full details of a single question."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(404, f"Question with ID {question_id} not found")

    return {
        "id": q.id,
        "track_id": q.track_id,
        "raw_id": q.raw_id,
        "chapter": q.chapter,
        "chapter_title": q.chapter_title,
        "boss_name": q.boss_name,
        "boss_slug": q.boss_slug,
        "order_index": q.order_index,
        "topic": q.topic,
        "difficulty": q.difficulty,
        "question_type": q.question_type,
        "prompt": q.prompt,
        "options": _to_json_obj(q.options_json, []),
        "correct_option": q.correct_option,
        "correct_answer": q.correct_answer,
        "explanation": q.explanation,
        "spells": _to_json_obj(q.spells_json, []),
        "health": _to_json_obj(q.health_json, []),
        "images": _to_json_obj(q.images_json, []),
    }


@router.put("/admin/questions/{question_id}")
def admin_update_question(
    question_id: int,
    body: QuestionUpdateRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    """Update question text, choices, explanations, or spell values."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(404, f"Question with ID {question_id} not found")

    current_options = _to_json_obj(q.options_json, [])
    current_spells = _to_json_obj(q.spells_json, [20, 30, 45])
    current_health = _to_json_obj(q.health_json, [100])
    current_images = _to_json_obj(q.images_json, [])

    candidate_options = body.options if body.options is not None else current_options
    candidate_correct_opt = body.correct_option if body.correct_option is not None else q.correct_option
    candidate_correct_ans = body.correct_answer if body.correct_answer is not None else q.correct_answer
    candidate_spells = body.spells if body.spells is not None else current_spells
    candidate_health = body.health if body.health is not None else current_health
    candidate_images = body.images if body.images is not None else current_images

    try:
        v_opts, v_c_opt, v_c_ans, v_spells, v_health, v_images = validate_question_payload(
            options=candidate_options,
            correct_option=candidate_correct_opt,
            correct_answer=candidate_correct_ans,
            spells=candidate_spells,
            health=candidate_health,
            images=candidate_images,
        )
    except QuestionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if body.prompt is not None:
        q.prompt = body.prompt.strip()
    q.options_json = v_opts
    q.correct_option = v_c_opt
    q.correct_answer = v_c_ans
    q.spells_json = v_spells
    q.health_json = v_health
    q.images_json = v_images

    if body.explanation is not None:
        q.explanation = body.explanation
    if body.topic is not None:
        q.topic = body.topic
    if body.difficulty is not None:
        q.difficulty = body.difficulty

    q.updated_at = int(time.time())
    db.commit()
    db.refresh(q)

    # Invalidate caches for this track
    shared_track_cache.invalidate_track(q.track_id)
    invalidate_bundle_cache(q.track_id)

    return {
        "status": "ok",
        "message": f"Question {question_id} updated successfully",
        "question_id": q.id,
        "track_id": q.track_id,
    }


def _execute_reorder(
    track_id: str,
    chapter: int,
    boss_slug: Optional[str],
    body: ReorderQuestionsRequest,
    db: DBSession,
) -> dict:
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(404, f"Track '{track_id}' not found")

    effective_boss_slug = boss_slug or body.boss_slug

    q_filter = [Question.track_id == track_id, Question.chapter == chapter]
    if effective_boss_slug:
        q_filter.append(Question.boss_slug == effective_boss_slug)

    existing_questions = (
        db.query(Question)
        .filter(*q_filter)
        .order_by(Question.order_index.asc(), Question.id.asc())
        .all()
    )

    if not existing_questions:
        scope_desc = f"track '{track_id}', chapter {chapter}" + (f", boss '{effective_boss_slug}'" if effective_boss_slug else "")
        raise HTTPException(404, f"No questions found for {scope_desc}")

    existing_id_list = [q.id for q in existing_questions]
    existing_id_set = set(existing_id_list)

    final_ordered_ids: List[int] = []

    if body.move_question_id is not None or body.target_question_id is not None or body.position is not None:
        if body.move_question_id is None or body.target_question_id is None or body.position is None:
            raise HTTPException(400, "move_question_id, target_question_id, and position ('before' or 'after') must all be provided for move operations.")

        if body.move_question_id not in existing_id_set:
            raise HTTPException(400, f"move_question_id {body.move_question_id} not found in scoped questions")
        if body.target_question_id not in existing_id_set:
            raise HTTPException(400, f"target_question_id {body.target_question_id} not found in scoped questions")
        if body.move_question_id == body.target_question_id:
            raise HTTPException(400, "move_question_id and target_question_id must be different")

        working_ids = [qid for qid in existing_id_list if qid != body.move_question_id]
        target_idx = working_ids.index(body.target_question_id)
        insert_idx = target_idx if body.position == "before" else target_idx + 1
        working_ids.insert(insert_idx, body.move_question_id)
        final_ordered_ids = working_ids

    elif body.question_ids is not None:
        if len(body.question_ids) != len(set(body.question_ids)):
            raise HTTPException(400, "Duplicate question IDs are not permitted in reorder request")

        submitted_set = set(body.question_ids)
        unknown_ids = submitted_set - existing_id_set
        if unknown_ids:
            raise HTTPException(400, f"Unknown question ID(s) for this scope: {sorted(list(unknown_ids))}")

        missing_ids = existing_id_set - submitted_set
        if missing_ids:
            raise HTTPException(
                400,
                f"Incomplete question ID set. Expected complete permutation of {len(existing_id_set)} questions for this scope, missing: {sorted(list(missing_ids))}"
            )

        final_ordered_ids = body.question_ids
    else:
        raise HTTPException(400, "Must provide either 'question_ids' (complete set) or 'move_question_id', 'target_question_id', and 'position'.")

    base_order = min(q.order_index for q in existing_questions)
    now_ts = int(time.time())

    try:
        releases_repo = ReleasesRepository(db)
        draft_rel = releases_repo.create_draft_release(track_id, commit=False)

        # Temporary positive offset within transaction to prevent unique constraint collisions
        temp_offset = 1000000 + base_order
        for idx, q_id in enumerate(final_ordered_ids):
            db.query(Question).filter(Question.id == q_id).update({
                "order_index": temp_offset + idx,
            }, synchronize_session=False)

        db.flush()

        # Final sequential order_index, new release_id, and updated_at
        for new_idx, q_id in enumerate(final_ordered_ids):
            db.query(Question).filter(Question.id == q_id).update({
                "order_index": base_order + new_idx,
                "release_id": draft_rel.id,
                "updated_at": now_ts,
            }, synchronize_session=False)

        # Update remaining track questions to new release
        db.query(Question).filter(
            Question.track_id == track_id,
            ~Question.id.in_(final_ordered_ids),
        ).update({
            "release_id": draft_rel.id,
        }, synchronize_session=False)

        # Publish release
        releases_repo.publish_release(draft_rel.id, commit=False)

        # Single transaction commit
        db.commit()

    except Exception as exc:
        db.rollback()
        logger.error("Failed to reorder questions in track '%s', chapter %d: %s", track_id, chapter, exc)
        raise HTTPException(500, f"Reorder operation failed and was rolled back: {exc}")

    # Invalidate distributed cluster cache and local cache only after commit
    shared_track_cache.invalidate_track(track_id)
    invalidate_bundle_cache(track_id)

    return {
        "status": "ok",
        "track_id": track_id,
        "chapter": chapter,
        "boss_slug": effective_boss_slug,
        "reordered_count": len(final_ordered_ids),
        "release_id": draft_rel.id,
        "new_version": draft_rel.version,
    }


@router.post("/admin/tracks/{track_id}/chapters/{chapter}/bosses/{boss_slug}/reorder")
def admin_reorder_questions_by_boss(
    track_id: str,
    chapter: int,
    boss_slug: str,
    body: ReorderQuestionsRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    """
    Reorder questions scoped to a specific track, chapter, and boss.
    Requires either a complete ordered set or an explicit move-before/after operation.
    """
    return _execute_reorder(
        track_id=track_id,
        chapter=chapter,
        boss_slug=boss_slug,
        body=body,
        db=db,
    )


@router.post("/admin/tracks/{track_id}/chapters/{chapter}/reorder")
def admin_reorder_questions(
    track_id: str,
    chapter: int,
    body: ReorderQuestionsRequest,
    boss_slug: Optional[str] = Query(None, description="Optional boss slug to scope reorder"),
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    """
    Reorder questions within a specific track chapter (and optionally boss).
    Assigns sequential order_index in a single transaction with atomic release publishing.
    """
    return _execute_reorder(
        track_id=track_id,
        chapter=chapter,
        boss_slug=boss_slug,
        body=body,
        db=db,
    )


@router.post("/admin/questions/ingest")
def admin_ingest_questions(
    body: IngestQuestionsRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    """
    Trigger batch re-ingestion of question banks from JSON into the database.
    """
    from scripts.ingest_questions_to_postgres import ingest_questions_data
    from app.settings import settings

    stats = ingest_questions_data(
        db=db,
        target_track_id=body.track_id,
        root_dir=settings.root_dir,
        batch_size=body.batch_size,
    )
    invalidate_bundle_cache(body.track_id)

    return {
        "status": "ok",
        "total_questions": stats["total_questions"],
        "tracks_processed": stats["tracks_processed"],
    }
