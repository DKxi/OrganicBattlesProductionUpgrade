import time
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from app.infrastructure.database.models import PlayerQuestionProgress, AnswerAttempt

logger = logging.getLogger("organicbattles.progress")


class ProgressRepository:
    """Repository managing per-player mastery, spaced repetition (SM-2), and answer attempt logs."""

    def __init__(self, db: DBSession):
        self.db = db

    def record_attempt(
        self,
        user_id: str,
        question_id: int,
        track_id: str,
        boss_slug: str,
        selected_option: str,
        is_correct: bool,
        session_id: Optional[str] = None,
        release_id: Optional[str] = None,
        spell_id: Optional[str] = None,
        damage_dealt: int = 0,
        damage_taken: int = 0,
        time_taken_ms: Optional[int] = None,
    ) -> AnswerAttempt:
        """Record an immutable answer attempt for learning research, analytics, and tracking."""
        now_ts = int(time.time())
        attempt = AnswerAttempt(
            session_id=session_id,
            user_id=user_id,
            question_id=question_id,
            track_id=track_id,
            release_id=release_id,
            boss_slug=boss_slug,
            spell_id=spell_id,
            selected_option=selected_option,
            is_correct=1 if is_correct else 0,
            damage_dealt=damage_dealt,
            damage_taken=damage_taken,
            time_taken_ms=time_taken_ms,
            created_at=now_ts,
        )
        self.db.add(attempt)
        self.db.flush()
        return attempt

    def update_progress(
        self,
        user_id: str,
        question_id: int,
        track_id: str,
        is_correct: bool,
    ) -> PlayerQuestionProgress:
        """
        Update per-player question mastery and spaced repetition delivery state using SM-2 algorithm.
        """
        now_ts = int(time.time())
        progress = (
            self.db.query(PlayerQuestionProgress)
            .filter(
                PlayerQuestionProgress.user_id == user_id,
                PlayerQuestionProgress.question_id == question_id,
            )
            .first()
        )

        if not progress:
            progress = PlayerQuestionProgress(
                user_id=user_id,
                question_id=question_id,
                track_id=track_id,
                mastery_score=0.0,
                ease_factor=2.5,
                interval_days=0.0,
                repetitions=0,
                total_attempts=0,
                correct_attempts=0,
                created_at=now_ts,
                updated_at=now_ts,
            )
            self.db.add(progress)
            self.db.flush()

        progress.total_attempts += 1
        progress.last_attempt_at = now_ts
        progress.updated_at = now_ts

        if is_correct:
            progress.correct_attempts += 1
            if progress.repetitions == 0:
                progress.interval_days = 1.0
            elif progress.repetitions == 1:
                progress.interval_days = 6.0
            else:
                progress.interval_days = round(progress.interval_days * progress.ease_factor, 1)

            progress.repetitions += 1
            progress.ease_factor = min(3.0, progress.ease_factor + 0.1)
            progress.mastery_score = min(1.0, round(progress.mastery_score + 0.25, 2))
        else:
            progress.repetitions = 0
            progress.interval_days = 1.0
            progress.ease_factor = max(1.3, progress.ease_factor - 0.2)
            progress.mastery_score = max(0.0, round(progress.mastery_score - 0.2, 2))

        # Schedule next review
        progress.next_review_at = int(now_ts + (progress.interval_days * 86400))
        return progress

    def get_user_progress_summary(self, user_id: str, track_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate mastery metrics for a user."""
        now_ts = int(time.time())
        query = self.db.query(PlayerQuestionProgress).filter(PlayerQuestionProgress.user_id == user_id)
        if track_id:
            query = query.filter(PlayerQuestionProgress.track_id == track_id)

        rows: List[PlayerQuestionProgress] = query.all()
        total_tracked = len(rows)
        if total_tracked == 0:
            return {
                "total_tracked": 0,
                "mastered_count": 0,
                "due_for_review_count": 0,
                "avg_mastery": 0.0,
                "total_attempts": 0,
                "overall_accuracy": 0.0,
            }

        mastered = sum(1 for r in rows if r.mastery_score >= 0.75)
        due_for_review = sum(1 for r in rows if r.next_review_at and r.next_review_at <= now_ts)
        total_attempts = sum(r.total_attempts for r in rows)
        correct_attempts = sum(r.correct_attempts for r in rows)
        avg_mastery = round(sum(r.mastery_score for r in rows) / total_tracked, 2)
        overall_accuracy = round(correct_attempts / total_attempts, 2) if total_attempts > 0 else 0.0

        return {
            "total_tracked": total_tracked,
            "mastered_count": mastered,
            "due_for_review_count": due_for_review,
            "avg_mastery": avg_mastery,
            "total_attempts": total_attempts,
            "overall_accuracy": overall_accuracy,
        }
