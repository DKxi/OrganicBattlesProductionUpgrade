import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func, desc

from app.api.deps import get_admin_db, auth_admin
from app.infrastructure.database.models import AnswerAttempt, PlayerQuestionProgress, Question, User
from app.infrastructure.database.progress_repo import ProgressRepository

logger = logging.getLogger("organicbattles.analytics")
router = APIRouter(tags=["Admin Learning Analytics & Research"])


@router.get("/admin/analytics/overview")
def get_analytics_overview(
    track_id: Optional[str] = Query(None, description="Optional filter by track"),
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
) -> Dict[str, Any]:
    """Retrieve macro-level learning analytics across player attempts."""
    query = db.query(AnswerAttempt)
    if track_id:
        query = query.filter(AnswerAttempt.track_id == track_id)

    total_attempts = query.count()
    if total_attempts == 0:
        return {
            "total_attempts": 0,
            "correct_attempts": 0,
            "overall_accuracy": 0.0,
            "unique_players": 0,
            "struggling_questions": [],
        }

    correct_attempts = query.filter(AnswerAttempt.is_correct == 1).count()
    overall_accuracy = round(correct_attempts / total_attempts, 2)
    unique_players = query.with_entities(func.count(func.distinct(AnswerAttempt.user_id))).scalar() or 0

    # Identify top 5 questions with highest incorrect attempts
    struggling_stats = (
        db.query(
            AnswerAttempt.question_id,
            func.count(AnswerAttempt.id).label("attempts"),
            func.sum(AnswerAttempt.is_correct).label("correct"),
        )
        .group_by(AnswerAttempt.question_id)
        .having(func.count(AnswerAttempt.id) >= 1)
        .all()
    )

    struggling_questions = []
    for q_id, attempts, corr in struggling_stats:
        acc = round(corr / attempts, 2) if attempts > 0 else 0.0
        if acc < 0.70:
            q_row = db.query(Question.prompt, Question.topic).filter(Question.id == q_id).first()
            struggling_questions.append({
                "question_id": q_id,
                "prompt": q_row[0][:120] if q_row else "Unknown",
                "topic": q_row[1] if q_row else None,
                "total_attempts": attempts,
                "accuracy": acc,
            })

    struggling_questions.sort(key=lambda x: (x["accuracy"], -x["total_attempts"]))

    return {
        "total_attempts": total_attempts,
        "correct_attempts": correct_attempts,
        "overall_accuracy": overall_accuracy,
        "unique_players": unique_players,
        "struggling_questions": struggling_questions[:10],
    }


@router.get("/admin/analytics/questions/{question_id}")
def get_question_analytics(
    question_id: int,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
) -> Dict[str, Any]:
    """Retrieve detailed research analytics and option distribution for a specific question."""
    q_row = db.query(Question).filter(Question.id == question_id).first()
    if not q_row:
        raise HTTPException(404, "Question not found")

    attempts = db.query(AnswerAttempt).filter(AnswerAttempt.question_id == question_id).all()
    total_attempts = len(attempts)

    # Option selection distribution
    option_distribution: Dict[str, int] = {}
    for att in attempts:
        opt = att.selected_option
        option_distribution[opt] = option_distribution.get(opt, 0) + 1

    correct_count = sum(1 for att in attempts if att.is_correct == 1)
    accuracy = round(correct_count / total_attempts, 2) if total_attempts > 0 else 0.0

    return {
        "question_id": question_id,
        "prompt": q_row.prompt,
        "correct_option": q_row.correct_option,
        "correct_answer": q_row.correct_answer,
        "topic": q_row.topic,
        "difficulty": q_row.difficulty,
        "total_attempts": total_attempts,
        "correct_attempts": correct_count,
        "accuracy": accuracy,
        "option_distribution": option_distribution,
    }


@router.get("/admin/analytics/users/{user_id}/mastery")
def get_user_mastery_analytics(
    user_id: str,
    track_id: Optional[str] = Query(None, description="Optional track filter"),
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
) -> Dict[str, Any]:
    """Retrieve per-player mastery and spaced repetition state."""
    repo = ProgressRepository(db)
    summary = repo.get_user_progress_summary(user_id, track_id=track_id)
    return {
        "user_id": user_id,
        "track_id": track_id,
        "summary": summary,
    }
