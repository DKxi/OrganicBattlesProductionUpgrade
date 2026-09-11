import time
import logging
from typing import List, Optional
from sqlalchemy.orm import Session as DBSession
from app.infrastructure.database.models import ContentRelease, Question

logger = logging.getLogger("organicbattles.releases")


class ReleasesRepository:
    """Repository for managing atomic versioned content releases (OB_content_releases)."""

    def __init__(self, db: DBSession):
        self.db = db

    def get_latest_version(self, track_id: str) -> int:
        """Return highest version number for a track, or 0 if none."""
        rel = (
            self.db.query(ContentRelease)
            .filter(ContentRelease.track_id == track_id)
            .order_by(ContentRelease.version.desc())
            .first()
        )
        return rel.version if rel else 0

    def get_active_release(self, track_id: str) -> Optional[ContentRelease]:
        """Retrieve currently published content release for a track."""
        return (
            self.db.query(ContentRelease)
            .filter(ContentRelease.track_id == track_id, ContentRelease.status == "published")
            .order_by(ContentRelease.version.desc())
            .first()
        )

    def get_release_by_id(self, release_id: str) -> Optional[ContentRelease]:
        return self.db.query(ContentRelease).filter(ContentRelease.id == release_id).first()

    def get_track_releases(self, track_id: str) -> List[ContentRelease]:
        """Return all releases for a track ordered by version descending."""
        return (
            self.db.query(ContentRelease)
            .filter(ContentRelease.track_id == track_id)
            .order_by(ContentRelease.version.desc())
            .all()
        )

    def create_draft_release(self, track_id: str, checksum: Optional[str] = None) -> ContentRelease:
        """Create a new draft content release with an incremented version number."""
        next_ver = self.get_latest_version(track_id) + 1
        release_id = f"{track_id}_v{next_ver}"

        # Clean up any un-published draft with this ID if it exists
        existing = self.get_release_by_id(release_id)
        if existing:
            self.db.delete(existing)
            self.db.flush()

        release = ContentRelease(
            id=release_id,
            track_id=track_id,
            version=next_ver,
            status="draft",
            checksum=checksum,
            created_at=int(time.time()),
            published_at=None,
        )
        self.db.add(release)
        self.db.commit()
        self.db.refresh(release)
        logger.info("Created draft content release %s (v%d) for track %s", release_id, next_ver, track_id)
        return release

    def publish_release(self, release_id: str) -> ContentRelease:
        """
        Atomically publish a release:
        - Sets any previously published releases for this track to 'archived'.
        - Marks this release as 'published' and records published_at timestamp.
        """
        release = self.get_release_by_id(release_id)
        if not release:
            raise ValueError(f"Content release '{release_id}' not found")

        track_id = release.track_id

        # Archive prior active releases for this track
        self.db.query(ContentRelease).filter(
            ContentRelease.track_id == track_id,
            ContentRelease.status == "published",
            ContentRelease.id != release_id,
        ).update({"status": "archived"})

        release.status = "published"
        release.published_at = int(time.time())
        self.db.commit()
        self.db.refresh(release)
        logger.info("Atomically published release %s (v%d) for track %s", release.id, release.version, track_id)
        return release

    def rollback_to_release(self, track_id: str, target_version: int) -> ContentRelease:
        """Rollback active track content to an earlier published or archived release."""
        target = (
            self.db.query(ContentRelease)
            .filter(ContentRelease.track_id == track_id, ContentRelease.version == target_version)
            .first()
        )
        if not target:
            raise ValueError(f"Target release v{target_version} for track '{track_id}' not found")

        # Archive current published releases
        self.db.query(ContentRelease).filter(
            ContentRelease.track_id == track_id,
            ContentRelease.status == "published",
            ContentRelease.id != target.id,
        ).update({"status": "archived"})

        target.status = "published"
        target.published_at = int(time.time())
        self.db.commit()
        self.db.refresh(target)
        logger.info("Rolled back track %s to release %s (v%d)", track_id, target.id, target.version)
        return target

    def ensure_initial_release_for_existing_questions(self, track_id: str) -> Optional[ContentRelease]:
        """If unversioned questions exist, link them to an initial published release v1."""
        active = self.get_active_release(track_id)
        if active:
            return active

        # Check if questions exist without release_id
        unlinked_count = (
            self.db.query(Question)
            .filter(Question.track_id == track_id, Question.release_id.is_(None))
            .count()
        )
        if unlinked_count == 0:
            return None

        rel_id = f"{track_id}_v1"
        rel = self.get_release_by_id(rel_id)
        if not rel:
            rel = ContentRelease(
                id=rel_id,
                track_id=track_id,
                version=1,
                status="published",
                checksum="legacy-initial",
                created_at=int(time.time()),
                published_at=int(time.time()),
            )
            self.db.add(rel)
            self.db.flush()

        self.db.query(Question).filter(
            Question.track_id == track_id, Question.release_id.is_(None)
        ).update({"release_id": rel_id})
        self.db.commit()
        self.db.refresh(rel)
        logger.info("Associated %d existing questions with initial release %s", unlinked_count, rel_id)
        return rel
