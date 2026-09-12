import time
import logging
from typing import List, Optional, Dict, Any, Tuple
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
            boss = (
                self.db.query(Boss)
                .filter(Boss.track_id == track_id, Boss.chapter == chapter, Boss.order_index == order_index)
                .first()
            )
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

    def sync_bosses_from_questions(
        self,
        track_id: Optional[str] = None,
        release_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Scan questions in database and synchronize OB_bosses and OB_boss_question_assignments.
        Extracts unique (track_id, chapter, boss_slug), determines chapter-level ordering,
        creates/updates Boss records, and assigns questions to each corresponding boss.
        """
        query = self.db.query(Question)
        if track_id:
            query = query.filter(Question.track_id == track_id)
        if release_id:
            query = query.filter(Question.release_id == release_id)

        questions = query.order_by(
            Question.track_id.asc(),
            Question.chapter.asc(),
            Question.order_index.asc(),
        ).all()

        if not questions:
            return {"bosses": 0, "assignments": 0}

        from collections import OrderedDict
        track_chapter_groups: Dict[Tuple[str, int], List[Question]] = OrderedDict()
        for q in questions:
            key = (q.track_id, q.chapter)
            track_chapter_groups.setdefault(key, []).append(q)

        bosses_synced = 0
        assignments_synced = 0

        for (t_id, ch_num), ch_questions in track_chapter_groups.items():
            # Find distinct bosses in this chapter preserving order of appearance
            seen_bosses: Dict[str, Question] = OrderedDict()
            for q in ch_questions:
                slug = q.boss_slug or "boss"
                if slug not in seen_bosses:
                    seen_bosses[slug] = q

            for b_idx, (slug, sample_q) in enumerate(seen_bosses.items()):
                boss_id = f"{t_id}_ch{ch_num}_{slug}"
                b_name = sample_q.boss_name or slug.replace("-", " ").title()

                health_val = 100
                if sample_q.health_json:
                    if isinstance(sample_q.health_json, list) and sample_q.health_json:
                        health_val = int(sample_q.health_json[0])
                    elif isinstance(sample_q.health_json, (int, float)):
                        health_val = int(sample_q.health_json)

                image_val = f"{slug}.png"
                if sample_q.images_json:
                    if isinstance(sample_q.images_json, list) and sample_q.images_json:
                        image_val = str(sample_q.images_json[0])
                    elif isinstance(sample_q.images_json, str):
                        image_val = sample_q.images_json

                boss = self.create_or_update_boss(
                    boss_id=boss_id,
                    slug=slug,
                    track_id=t_id,
                    chapter=ch_num,
                    order_index=b_idx,
                    name=b_name,
                    image_file=image_val,
                    health=health_val,
                    element=sample_q.topic or "Organic",
                    strategy={"chapter_title": sample_q.chapter_title},
                )
                bosses_synced += 1

            self.db.flush()

            # Assign questions to bosses
            for q in ch_questions:
                slug = q.boss_slug or "boss"
                boss = self.get_boss_by_slug(t_id, slug)
                if boss:
                    self.assign_question_to_boss(
                        boss_id=boss.id,
                        question_id=q.id,
                        track_id=t_id,
                        release_id=q.release_id,
                        order_index=q.order_index,
                    )
                    assignments_synced += 1

        self.db.commit()
        return {"bosses": bosses_synced, "assignments": assignments_synced}

    def seed_default_bosses(self, track_id: str = "default") -> int:
        """Seed default boss entries and auto-assign questions for the track."""
        # Check if questions exist to sync directly from database
        q_count = self.db.query(Question).filter(Question.track_id == track_id).count()
        if q_count > 0:
            stats = self.sync_bosses_from_questions(track_id=track_id)
            return stats["bosses"]

        # Check if already seeded
        existing_count = self.db.query(Boss).filter(Boss.track_id == track_id).count()
        if existing_count > 0:
            return existing_count

        now_ts = int(time.time())
        seeded = 0
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

        self.db.commit()
        return seeded
