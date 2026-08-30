import json
import time
from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession
from app.infrastructure.database.models import GameSession, User
from app.domain.progression.entities import Session, Avatar
from app.domain.content.resolver import resolve_content_source
from app.api.deps import get_content_bundle


def get_session_by_id(db: DBSession, session_id: str) -> Session:
    """Retrieve an active Session from the database by session ID."""
    db_record = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="Session not found")

    user_record = db.query(User).filter(User.id == db_record.user_id).first()
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found")

    user_content_source = user_record.content_source or db_record.content_source
    s = Session(db_record.user_id, user_record.username, content_source=user_content_source)
    s.id = db_record.id
    s.chapter = db_record.chapter
    s.boss_index = db_record.boss_index
    s.player_hp = db_record.player_hp
    s.player_max_hp = db_record.player_max_hp
    s.boss_hp = db_record.boss_hp
    s.active_spell = db_record.active_spell
    s.turn_id = db_record.turn_id

    # Restore complex JSON fields
    if db_record.active_question_json:
        s.active_question = tuple(json.loads(db_record.active_question_json))
    else:
        s.active_question = None

    s.cooldowns = json.loads(db_record.cooldowns_json) if db_record.cooldowns_json else {}
    s.log = json.loads(db_record.log_json) if db_record.log_json else []
    s.completed = set(json.loads(db_record.completed_json)) if db_record.completed_json else set()
    s.rewards = json.loads(db_record.rewards_json) if db_record.rewards_json else []

    # Restore question cursors (tuple key conversion)
    raw_cursors = json.loads(db_record.question_cursors_json) if db_record.question_cursors_json else {}
    s.question_cursors = {}
    for key, val in raw_cursors.items():
        chapter_str, boss = key.split(":", 1)
        s.question_cursors[(int(chapter_str), boss)] = int(val)

    # Restore avatar and finalized from user model
    if user_record.avatar_json:
        try:
            s.avatar = Avatar.model_validate(json.loads(user_record.avatar_json))
            s.finalized = True
        except Exception:
            s.avatar = None
            s.finalized = False
    else:
        s.avatar = None
        s.finalized = False

    # Track DB version for optimistic locking
    s._db_version = db_record.version
    return s


def get_or_create_session(db: DBSession, user_id: str, username: str) -> Session:
    """Get the active Session for a user, or create one if it doesn't exist."""
    db_record = db.query(GameSession).filter(GameSession.user_id == user_id).first()
    if not db_record:
        import uuid
        session_id = str(uuid.uuid4())

        user = db.query(User).filter(User.id == user_id).first()
        user_content_source = user.content_source if user else None
        effective_mode = resolve_content_source(user_content_source)
        bundle = get_content_bundle(effective_mode)
        chapters = bundle.chapters

        chapter = 1
        boss_index = 0
        player_hp = 150
        player_max_hp = 150
        boss_hp = chapters[0]["bosses"][0][2] if (chapters and chapters[0].get("bosses")) else 0
        active_question_json = None
        active_spell = None
        turn_id = None
        cooldowns_json = "{}"
        log_json = "[]"
        completed_json = "[]"
        rewards_json = "[]"
        question_cursors_json = "{}"

        if user and user.progress_json:
            try:
                progress = json.loads(user.progress_json)
                chapter = max(1, min(int(progress.get("chapter", 1)), len(chapters)))
                bosses_in_ch = chapters[chapter - 1]["bosses"]
                boss_index = max(0, min(int(progress.get("boss_index", 0)), len(bosses_in_ch) - 1))
                player_hp = int(progress.get("player_hp", 150))
                player_max_hp = int(progress.get("player_max_hp", 150))
                boss_hp = int(progress.get("boss_hp", bosses_in_ch[boss_index][2]))
                active_question_json = json.dumps(progress.get("active_question")) if progress.get("active_question") else None
                active_spell = progress.get("active_spell")
                turn_id = progress.get("turn_id")
                cooldowns_json = json.dumps(progress.get("cooldowns", {}))
                log_json = json.dumps(progress.get("log", []))
                completed_json = json.dumps(progress.get("completed", []))
                rewards_json = json.dumps(progress.get("rewards", []))
                question_cursors_json = json.dumps(progress.get("question_cursors", {}))
            except Exception:
                pass

        db_record = GameSession(
            id=session_id,
            user_id=user_id,
            content_source=user_content_source,
            chapter=chapter,
            boss_index=boss_index,
            player_hp=player_hp,
            player_max_hp=player_max_hp,
            boss_hp=boss_hp,
            active_question_json=active_question_json,
            active_spell=active_spell,
            turn_id=turn_id,
            cooldowns_json=cooldowns_json,
            log_json=log_json,
            completed_json=completed_json,
            rewards_json=rewards_json,
            question_cursors_json=question_cursors_json,
            version=1,
            updated_at=int(time.time()),
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

    return get_session_by_id(db, db_record.id)


def save_session(db: DBSession, s: Session) -> None:
    """Persist the changes in a Session object back to the database, enforcing optimistic locks."""
    db_record = db.query(GameSession).filter(GameSession.id == s.id).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="Session record not found in DB")

    # Optimistic locking check
    if hasattr(s, "_db_version") and db_record.version != s._db_version:
        raise HTTPException(status_code=409, detail="Conflict: Session modified by another request. Please try again.")

    db_record.content_source = s.content_source
    db_record.chapter = s.chapter
    db_record.boss_index = s.boss_index
    db_record.player_hp = s.player_hp
    db_record.player_max_hp = s.player_max_hp
    db_record.boss_hp = s.boss_hp
    db_record.active_spell = s.active_spell
    db_record.turn_id = s.turn_id

    # Serialize complex fields
    db_record.active_question_json = json.dumps(list(s.active_question)) if s.active_question else None
    db_record.cooldowns_json = json.dumps(s.cooldowns)
    db_record.log_json = json.dumps(s.log[-20:])
    db_record.completed_json = json.dumps(list(s.completed))
    db_record.rewards_json = json.dumps(s.rewards)

    # Serialize question cursors
    cursors_dict = {f"{chapter}:{boss}": cursor for (chapter, boss), cursor in s.question_cursors.items()}
    db_record.question_cursors_json = json.dumps(cursors_dict)

    # Keep user.progress_json and avatar_json updated as well
    user_record = db.query(User).filter(User.id == s.user_id).first()
    if user_record:
        if s.avatar:
            user_record.avatar_json = s.avatar.model_dump_json()
        progress = {
            "chapter": s.chapter,
            "boss_index": s.boss_index,
            "player_hp": s.player_hp,
            "player_max_hp": s.player_max_hp,
            "boss_hp": s.boss_hp,
            "active_question": list(s.active_question) if s.active_question else None,
            "active_spell": s.active_spell,
            "turn_id": s.turn_id,
            "cooldowns": s.cooldowns,
            "log": s.log[-20:],
            "completed": list(s.completed),
            "rewards": s.rewards,
            "question_cursors": {f"{chapter}:{boss}": cursor for (chapter, boss), cursor in s.question_cursors.items()},
        }
        user_record.progress_json = json.dumps(progress)

    # Increment version for concurrency safety
    db_record.version += 1
    db_record.updated_at = int(time.time())

    db.commit()
    db.refresh(db_record)
    s._db_version = db_record.version
