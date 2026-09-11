import time
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session as DBSession

from app.infrastructure.database.models import Boss, BossQuestionAssignment, Question, Track
from app.domain.content.loader import BUILTIN_CHAPTERS

logger = logging.getLogger("organicbattles.bosses")


class BossesRepository:
    """Repository managing boss definitions and boss-question assignment mappings."""

    def __init__(self, db: DBSession):
        self.db = db

    def get_boss(self, boss_id: str) -> Optional[Boss]:
        return self.db.query(Boss).filter(Boss.id == boss_id).first()

    def get_boss_by_slug(self, track_id: str, boss_slug: str) -> Optional[Boss]:
        return (
            self.db.query(Boss)
            .filter(Boss.track_id == track_id, Boss.slug == boss_slug)
            .first()
        )

    def get_bosses_for_track(self, track_id: str, chapter: Optional[int] = None) -> List[Boss]:
        query = self.db.query(Boss).filter(Boss.track_id == track_id)
        if chapter is not None:
            query = query.filter(Boss.chapter == chapter)
        return query.order_by(Boss.chapter.asc(), Boss.order_index.asc()).all()

    def create_or_update_boss(
        self,
        boss_id: str,
        slug: str,
        track_id: str,
        chapter: int,
        order_index: int,
        name: str,
        image_file: str,
        health: int = 100,
        element: Optional[str] = None,
        strategy: Optional[Dict[str, Any]] = None,
    ) -> Boss:
        boss = self.get_boss(boss_id)
        if not boss:
            boss = Boss(
                id=boss_id,
                slug=slug,
                track_id=track_id,
                chapter=chapter,
                order_index=order_index,
                name=name,
                image_file=image_file,
                health=health,
                element=element,
                strategy_json=strategy or {},
            )
            self.db.add(boss)
        else:
            boss.slug = slug
            boss.track_id = track_id
            boss.chapter = chapter
            boss.order_index = order_index
            boss.name = name
            boss.image_file = image_file
            boss.health = health
            boss.element = element
            if strategy is not None:
                boss.strategy_json = strategy
        return boss

    def assign_question_to_boss(
        self,
        boss_id: str,
        question_id: int,
        track_id: str,
        release_id: Optional[str] = None,
        order_index: int = 0,
        weight: float = 1.0,
    ) -> BossQuestionAssignment:
        assignment = (
            self.db.query(BossQuestionAssignment)
            .filter(
                BossQuestionAssignment.boss_id == boss_id,
                BossQuestionAssignment.question_id == question_id,
                BossQuestionAssignment.release_id == release_id,
            )
            .first()
        )
        if not assignment:
            assignment = BossQuestionAssignment(
                boss_id=boss_id,
                question_id=question_id,
                track_id=track_id,
                release_id=release_id,
                order_index=order_index,
                weight=weight,
            )
            self.db.add(assignment)
        else:
            assignment.order_index = order_index
            assignment.weight = weight
        return assignment

    def seed_default_bosses(self, track_id: str = "organic1") -> int:
        """Seed default boss entries and auto-assign questions for the track."""
        seeded = 0
        now_ts = int(time.time())

        # Check if already seeded
        existing_count = self.db.query(Boss).filter(Boss.track_id == track_id).count()
        if existing_count > 0:
            return existing_count

        for ch in BUILTIN_CHAPTERS:
            ch_num = ch["id"]
            for idx, boss_info in enumerate(ch["bosses"]):
                slug = boss_info[0]
                name = boss_info[1]
                img = f"{slug}.png"
                boss_id = f"{track_id}_ch{ch_num}_{slug}"

                boss = Boss(
                    id=boss_id,
                    slug=slug,
                    track_id=track_id,
                    chapter=ch_num,
                    order_index=idx,
                    name=name,
                    image_file=img,
                    health=100,
                    element="Organic",
                    strategy_json={},
                    created_at=now_ts,
                )
                self.db.add(boss)
                seeded += 1

        self.db.flush()

        # Link questions to bosses
        questions = self.db.query(Question).filter(Question.track_id == track_id).all()
        for q in questions:
            boss = self.get_boss_by_slug(track_id, q.boss_slug)
            if boss:
                self.assign_question_to_boss(
                    boss_id=boss.id,
                    question_id=q.id,
                    track_id=track_id,
                    release_id=q.release_id,
                    order_index=q.order_index,
                )

        self.db.commit()
        return seeded
