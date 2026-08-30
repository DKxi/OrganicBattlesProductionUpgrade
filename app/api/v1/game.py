import json
import time
import secrets
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_db, get_current_user, get_content_bundle
from app.infrastructure.database.models import User, GameSession
from app.infrastructure.database.repositories import SessionRepository
from app.domain.content.resolver import resolve_content_source
from app.domain.content.loader import json_available_spells
from app.domain.combat.spells import SPELL_CATALOG

router = APIRouter(tags=["Game Session"])


class FinalizeAvatarRequest(BaseModel):
    character: Optional[str] = None
    body: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    skin: Optional[str] = None
    hair: Optional[Any] = None
    outfit: Optional[str] = None
    accessory: Optional[str] = None
    aura: Optional[str] = None


def format_game_state(game_session: GameSession, user: User) -> Dict[str, Any]:
    effective = resolve_content_source(user.content_source if user else game_session.content_source)
    bundle = get_content_bundle(effective)
    chapters = bundle.chapters

    ch_idx = max(0, min(game_session.chapter - 1, len(chapters) - 1))
    ch_data = chapters[ch_idx]
    bosses = ch_data["bosses"]
    b_idx = max(0, min(game_session.boss_index, len(bosses) - 1))
    boss = bosses[b_idx]

    try:
        active_q = json.loads(game_session.active_question_json) if game_session.active_question_json else None
    except Exception:
        active_q = None

    now = time.time()
    try:
        raw_cd = json.loads(game_session.cooldowns_json) if game_session.cooldowns_json else {}
    except Exception:
        raw_cd = {}
    cooldowns = {
        k: max(0.0, round(v - now, 1)) if isinstance(v, (int, float)) and v > now else 0
        for k, v in raw_cd.items()
    }
    for k in SPELL_CATALOG:
        cooldowns.setdefault(k, 0)


    try:
        completed = json.loads(game_session.completed_json) if game_session.completed_json else []
    except Exception:
        completed = []

    try:
        rewards = json.loads(game_session.rewards_json) if hasattr(game_session, "rewards_json") and game_session.rewards_json else []
    except Exception:
        rewards = []

    try:
        log = json.loads(game_session.log_json) if game_session.log_json else []
    except Exception:
        log = []

    try:
        avatar = json.loads(user.avatar_json) if user and user.avatar_json else None
    except Exception:
        avatar = None

    boss_img = (
        (len(boss) > 6 and boss[6])
        or bundle.boss_images.get(boss[0])
        or bundle.boss_images.get(boss[1])
        or f"{boss[0]}.png"
    )

    try:
        cursors = json.loads(game_session.question_cursors_json) if hasattr(game_session, "question_cursors_json") and game_session.question_cursors_json else {}
    except Exception:
        cursors = {}

    bank = (
        bundle.question_boss_bank.get((game_session.chapter, boss[0]))
        or bundle.question_boss_bank.get(boss[0])
        or bundle.question_bank_by_chapter.get(game_session.chapter)
        or bundle.questions
    )
    q_idx = cursors.get(f"{game_session.chapter}:{boss[0]}", 0)
    cur_q = active_q or (bank[q_idx % len(bank)] if bank else None)
    q_prompt = cur_q[0] if cur_q else ""

    boss_values = bundle.boss_spell_values.get((game_session.chapter, boss[0])) or bundle.boss_spell_values.get(boss[0]) or []
    question_spell_values = bundle.spell_values.get(q_prompt, boss_values) if q_prompt else boss_values
    question_spell_damage = json_available_spells(question_spell_values) if (effective == "json" and question_spell_values) else {}

    if effective == "json" and question_spell_damage:
        spell_damage = question_spell_damage
    else:
        spell_damage = {k: v.damage for k, v in SPELL_CATALOG.items()}



    return {
        "session_id": game_session.id,
        "username": user.username if user else "Alchemist",
        "chapter": game_session.chapter,
        "chapter_name": ch_data["name"],
        "chapter_color": ch_data["color"],
        "boss": {
            "id": boss[0],
            "name": boss[1],
            "hp": game_session.boss_hp,
            "max_hp": boss[2],
            "image": boss_img,
        },
        "player": {
            "hp": game_session.player_hp,
            "max_hp": game_session.player_max_hp,
        },
        "question": {"prompt": active_q[0], "choices": active_q[1]} if active_q else None,
        "active_spell": game_session.active_spell,
        "cooldowns": cooldowns,
        "log": log,
        "mode": effective,
        "spell_damage": spell_damage,
        "avatar": avatar,
        "finalized": avatar is not None,
        "completed": completed,
        "rewards": rewards,
    }



@router.post("/game/new")
def new_game(
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    session_repo = SessionRepository(db)
    game_session = session_repo.get_by_user_id(current_user.id)

    effective = resolve_content_source(current_user.content_source)
    bundle = get_content_bundle(effective)
    first_boss = bundle.chapters[0]["bosses"][0]

    if not game_session:
        game_session = GameSession(
            id=secrets.token_hex(16),
            user_id=current_user.id,
            chapter=1,
            boss_index=0,
            player_hp=150,
            player_max_hp=150,
            boss_hp=first_boss[2],
            active_spell=None,
            active_question_json=None,
            cooldowns_json="{}",
            log_json=json.dumps([f"Welcome to Chapter 1: {bundle.chapters[0]['name']}. Defeat {first_boss[1]}."]),
            completed_json="[]",
            content_source=current_user.content_source,
            turn_id=None,
            version=1,
            updated_at=int(time.time()),
        )
        db.add(game_session)
        db.commit()
        db.refresh(game_session)

    return format_game_state(game_session, current_user)


@router.get("/game/state")
@router.get("/progression")
def get_state(
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    session_repo = SessionRepository(db)
    game_session = session_repo.get_by_id(session_id) if session_id else session_repo.get_by_user_id(current_user.id)

    if not game_session:
        raise HTTPException(404, "Session not found")
    if game_session.user_id != current_user.id:
        raise HTTPException(403, "Not authorized to access this session")

    return format_game_state(game_session, current_user)


@router.post("/avatar/finalize")
def finalize_avatar(
    body: FinalizeAvatarRequest,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    session_repo = SessionRepository(db)
    game_session = session_repo.get_by_id(session_id) if session_id else session_repo.get_by_user_id(current_user.id)

    if not game_session:
        effective = resolve_content_source(current_user.content_source)
        bundle = get_content_bundle(effective)
        first_boss = bundle.chapters[0]["bosses"][0]
        game_session = GameSession(
            id=session_id or secrets.token_hex(16),
            user_id=current_user.id,
            chapter=1,
            boss_index=0,
            player_hp=150,
            player_max_hp=150,
            boss_hp=first_boss[2],
            active_spell=None,
            active_question_json=None,
            cooldowns_json="{}",
            log_json=json.dumps([f"Welcome to Chapter 1: {bundle.chapters[0]['name']}. Defeat {first_boss[1]}."]),
            completed_json="[]",
            content_source=current_user.content_source,
            turn_id=None,
            version=1,
            updated_at=int(time.time()),
        )
        db.add(game_session)
        db.commit()
        db.refresh(game_session)

    avatar_dict = body.model_dump(exclude_none=True)
    if "config" not in avatar_dict or avatar_dict["config"] is None:
        avatar_dict["config"] = {}
    if "character" not in avatar_dict or not avatar_dict["character"]:
        avatar_dict["character"] = "organic-apprentice"
    if "body" not in avatar_dict or not avatar_dict["body"]:
        avatar_dict["body"] = "arc"

    current_user.avatar_json = json.dumps(avatar_dict)
    db.commit()

    return format_game_state(game_session, current_user)
