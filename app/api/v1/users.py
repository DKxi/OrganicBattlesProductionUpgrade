from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_db, get_current_user, get_content_bundle
from app.infrastructure.database.models import User, GameSession
from app.infrastructure.database.repositories import UserRepository
from app.domain.content.resolver import resolve_content_source

router = APIRouter(tags=["User Configuration"])


class ModeSwitchRequest(BaseModel):
    mode: Optional[str] = None
    content_source: Optional[str] = None


@router.post("/user/mode")
@router.post("/user/content-source")
def update_user_mode(
    body: ModeSwitchRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    target = body.mode or body.content_source
    if not target or target.strip().lower() not in ("app", "json"):
        raise HTTPException(400, "Content mode must be 'app' or 'json'")

    target_mode = target.strip().lower()

    user_repo = UserRepository(db)
    user_repo.update_content_source(current_user.id, target_mode)

    # Sync active game session
    game_session = db.query(GameSession).filter(GameSession.user_id == current_user.id).first()
    if game_session:
        game_session.content_source = target_mode
        game_session.active_question_json = None
        game_session.active_spell = None
        effective = resolve_content_source(target_mode)
        bundle = get_content_bundle(effective)
        chapters = bundle.chapters
        if game_session.chapter > len(chapters):
            game_session.chapter = 1
            game_session.boss_index = 0
            game_session.boss_hp = chapters[0]["bosses"][0][2]
        else:
            bosses = chapters[game_session.chapter - 1]["bosses"]
            if game_session.boss_index >= len(bosses):
                game_session.boss_index = 0
                game_session.boss_hp = bosses[0][2]
            else:
                game_session.boss_hp = bosses[game_session.boss_index][2]

        db.commit()

    effective = resolve_content_source(target_mode)
    bundle = get_content_bundle(effective)
    chapters = bundle.chapters
    ch_idx = max(0, min((game_session.chapter if game_session else 1) - 1, len(chapters) - 1))
    ch_data = chapters[ch_idx]
    boss = ch_data["bosses"][max(0, min((game_session.boss_index if game_session else 0), len(ch_data["bosses"]) - 1))]

    return {
        "status": "ok",
        "content_source": target_mode,
        "effective_mode": effective,
        "state": {
            "chapter": game_session.chapter if game_session else 1,
            "chapter_name": ch_data["name"],
            "boss": {"name": boss[1], "hp": game_session.boss_hp if game_session else boss[2]},
            "mode": effective,
        },
    }
