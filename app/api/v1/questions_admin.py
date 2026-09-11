import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_db, auth_admin
from app.infrastructure.database.models import Question, Track
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
    question_ids: List[int] = Field(..., min_length=1, description="Ordered list of question primary key IDs")


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

    db.commit()
    db.refresh(q)

    # Invalidate in-memory bundle cache for this track
    invalidate_bundle_cache(q.track_id)

    return {
        "status": "ok",
        "message": f"Question {question_id} updated successfully",
        "question_id": q.id,
        "track_id": q.track_id,
    }


@router.post("/admin/tracks/{track_id}/chapters/{chapter}/reorder")
def admin_reorder_questions(
    track_id: str,
    chapter: int,
    body: ReorderQuestionsRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    """
    Reorder questions within a specific track chapter.
    Assigns sequential order_index (0, 1, 2, ...) to preserve exact delivery order.
    Uses two-phase update to prevent intermediate unique constraint collisions.
    """
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(404, f"Track '{track_id}' not found")

    # Phase 1: Set temporary negative order_index
    for temp_idx, q_id in enumerate(body.question_ids):
        db.query(Question).filter(
            Question.id == q_id, Question.track_id == track_id, Question.chapter == chapter
        ).update({"order_index": -(temp_idx + 100000)})
    db.commit()

    # Phase 2: Set final sequential order_index
    updated_count = 0
    for new_idx, q_id in enumerate(body.question_ids):
        affected = (
            db.query(Question)
            .filter(Question.id == q_id, Question.track_id == track_id, Question.chapter == chapter)
            .update({"order_index": new_idx})
        )
        updated_count += affected

    db.commit()
    invalidate_bundle_cache(track_id)

    return {
        "status": "ok",
        "track_id": track_id,
        "chapter": chapter,
        "reordered_count": updated_count,
    }


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
