import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session as DBSession
from app.infrastructure.database.models import Curriculum, Track

logger = logging.getLogger("organicbattles.tracks")


class TracksRepository:
    """Repository for curriculum and track configurations stored in relational database."""

    def __init__(self, db: DBSession):
        self.db = db

    def get_tracks_config(self) -> Dict[str, Any]:
        """Return complete curricula and tracks structure conforming to tracks_config.json."""
        curricula = self.db.query(Curriculum).order_by(Curriculum.display_order, Curriculum.id).all()
        tracks = self.db.query(Track).order_by(Track.display_order, Track.id).all()

        curricula_list = []
        for c in curricula:
            item = {"id": c.id, "name": c.name}
            if c.code:
                item["code"] = c.code
            if c.total_questions:
                item["total_questions"] = c.total_questions
            if c.chapters:
                item["chapters"] = c.chapters
            if c.bosses:
                item["bosses"] = c.bosses
            curricula_list.append(item)

        tracks_list = []
        for t in tracks:
            tracks_list.append({
                "id": t.id,
                "curriculum": t.curriculum_id,
                "title": t.title,
                "detail": t.detail or "",
                "boss_folder": t.boss_folder or "",
                "questions": t.questions,
                "chapters": t.chapters,
                "accent": t.accent,
                "data_folder": t.data_folder,
            })

        return {
            "curricula": curricula_list,
            "tracks": tracks_list,
        }

    def get_all_curricula(self) -> List[Curriculum]:
        """Retrieve all curriculum records."""
        return self.db.query(Curriculum).order_by(Curriculum.display_order, Curriculum.id).all()

    def get_all_tracks(self) -> List[Track]:
        """Retrieve all track records."""
        return self.db.query(Track).order_by(Track.display_order, Track.id).all()

    def get_track(self, track_id: str) -> Optional[Track]:
        """Retrieve a specific track by its unique ID."""
        return self.db.query(Track).filter(Track.id == track_id).first()

    def get_track_dict(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific track formatted as a dictionary."""
        t = self.get_track(track_id)
        if not t:
            return None
        return {
            "id": t.id,
            "curriculum": t.curriculum_id,
            "title": t.title,
            "detail": t.detail or "",
            "boss_folder": t.boss_folder or "",
            "questions": t.questions,
            "chapters": t.chapters,
            "accent": t.accent,
            "data_folder": t.data_folder,
        }

    def update_track_folders(
        self,
        track_id: Optional[str],
        data_folder: str,
        boss_folder: Optional[str] = None,
    ) -> bool:
        """
        Update the data_folder and boss_folder of a single track or all tracks.
        Returns True if any track was updated.
        """
        query = self.db.query(Track)
        if track_id:
            query = query.filter(Track.id == track_id)

        tracks = query.all()
        if not tracks:
            return False

        for t in tracks:
            t.data_folder = data_folder
            if boss_folder is not None:
                t.boss_folder = boss_folder

        self.db.commit()
        return True

    def create_or_update_curriculum(self, data: Dict[str, Any], order: int = 0) -> Curriculum:
        """Insert or update a curriculum record."""
        curriculum_id = data["id"]
        c = self.db.query(Curriculum).filter(Curriculum.id == curriculum_id).first()
        if not c:
            c = Curriculum(
                id=curriculum_id,
                name=data["name"],
                code=data.get("code"),
                total_questions=data.get("total_questions", 0),
                chapters=data.get("chapters", 0),
                bosses=data.get("bosses", 0),
                display_order=order,
            )
            self.db.add(c)
        else:
            c.name = data.get("name", c.name)
            c.code = data.get("code", c.code)
            c.total_questions = data.get("total_questions", c.total_questions)
            c.chapters = data.get("chapters", c.chapters)
            c.bosses = data.get("bosses", c.bosses)
            c.display_order = order
        self.db.commit()
        self.db.refresh(c)
        return c

    def create_or_update_track(self, data: Dict[str, Any], order: int = 0) -> Track:
        """Insert or update a track record."""
        track_id = data["id"]
        t = self.db.query(Track).filter(Track.id == track_id).first()
        curriculum_id = data.get("curriculum_id") or data.get("curriculum")
        if not t:
            t = Track(
                id=track_id,
                curriculum_id=curriculum_id,
                title=data["title"],
                detail=data.get("detail"),
                data_folder=data["data_folder"],
                boss_folder=data.get("boss_folder"),
                questions=data.get("questions", 0),
                chapters=data.get("chapters", 0),
                accent=data.get("accent", "amber"),
                display_order=order,
            )
            self.db.add(t)
        else:
            if curriculum_id:
                t.curriculum_id = curriculum_id
            t.title = data.get("title", t.title)
            t.detail = data.get("detail", t.detail)
            t.data_folder = data.get("data_folder", t.data_folder)
            t.boss_folder = data.get("boss_folder", t.boss_folder)
            t.questions = data.get("questions", t.questions)
            t.chapters = data.get("chapters", t.chapters)
            t.accent = data.get("accent", t.accent)
            t.display_order = order
        self.db.commit()
        self.db.refresh(t)
        return t

    def seed_if_empty(self, seed_file_path: Path) -> bool:
        """
        If the curricula and tracks tables are empty, populate them from tracks_config.json.
        Returns True if seeded, False if tables already contain data.
        """
        curricula_count = self.db.query(Curriculum).count()
        tracks_count = self.db.query(Track).count()
        if curricula_count > 0 and tracks_count > 0:
            return False

        if not seed_file_path.is_file():
            logger.warning("Tracks seed file %s does not exist.", seed_file_path)
            return False

        try:
            cfg = json.loads(seed_file_path.read_text(encoding="utf-8"))
            for idx, c_data in enumerate(cfg.get("curricula", [])):
                self.create_or_update_curriculum(c_data, order=idx)

            for idx, t_data in enumerate(cfg.get("tracks", [])):
                self.create_or_update_track(t_data, order=idx)

            logger.info("Seeded %d curricula and %d tracks into database.", len(cfg.get("curricula", [])), len(cfg.get("tracks", [])))
            return True
        except Exception as exc:
            logger.error("Error seeding tracks config into database: %s", exc)
            self.db.rollback()
            return False
