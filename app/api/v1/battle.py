import json
import time
import secrets
import random
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_db, get_current_user, get_content_bundle
from app.infrastructure.database.models import User, GameSession
from app.infrastructure.database.repositories import SessionRepository
from app.domain.content.resolver import resolve_content_source
from app.domain.content.loader import JSON_SPELL_IDS_BY_RANK, json_available_spells
from app.domain.combat.spells import SPELL_CATALOG, get_spell
from app.domain.combat.rules import evaluate_combat_turn, decrement_cooldowns, apply_spell_cooldown
from app.api.v1.game import format_game_state

logger = logging.getLogger("organicbattles.battle")
router = APIRouter(tags=["Combat"])



TURN_EXPIRATION_SECONDS = 300  # 5 minutes TTL for active battle turns


class SelectSpellRequest(BaseModel):
    spell_id: str


class AnswerRequest(BaseModel):
    answer: str
    turn_id: str
    session_id: Optional[str] = None
    expected_version: Optional[int] = None


@router.post("/battle/select-spell")
def select_spell(
    body: SelectSpellRequest,
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

    if game_session.player_hp <= 0:
        raise HTTPException(400, "Your aura has faded. Please retry the battle to regroup.")

    if game_session.boss_hp <= 0:
        raise HTTPException(400, "The boss is already defeated. Proceed to the next arena.")

    if game_session.active_spell:
        raise HTTPException(409, "Answer the active question before selecting another spell.")

    spell_id = body.spell_id
    if spell_id not in SPELL_CATALOG:
        raise HTTPException(400, f"Invalid spell '{spell_id}'")

    cooldowns = json.loads(game_session.cooldowns_json) if game_session.cooldowns_json else {}
    if cooldowns.get(spell_id, 0) > time.time():
        raise HTTPException(409, "Spell is cooling down")

    effective = resolve_content_source(current_user.content_source if current_user else game_session.content_source)
    bundle = get_content_bundle(effective)

    chapters = bundle.chapters
    ch_idx = max(0, min(game_session.chapter - 1, len(chapters) - 1))
    bosses = chapters[ch_idx]["bosses"]
    boss_slug = bosses[max(0, min(game_session.boss_index, len(bosses) - 1))][0]

    is_json_like = (effective != "app")
    if is_json_like:
        boss_values = bundle.boss_spell_values.get((game_session.chapter, boss_slug)) or bundle.boss_spell_values.get(boss_slug) or []
        avail_spells = json_available_spells(boss_values)
        if avail_spells and spell_id not in avail_spells:
            raise HTTPException(409, "This spell is not available for the current boss")

    # Pick question sequentially following the chapter & boss (do not randomize)
    bank = (
        bundle.question_boss_bank.get((game_session.chapter, boss_slug))
        or bundle.question_boss_bank.get(boss_slug)
        or bundle.question_bank_by_chapter.get(game_session.chapter)
        or bundle.questions
    )
    cursors = json.loads(game_session.question_cursors_json) if hasattr(game_session, "question_cursors_json") and game_session.question_cursors_json else {}
    cursor_key = f"{game_session.chapter}:{boss_slug}"
    q_idx = cursors.get(cursor_key, 0) % len(bank)
    q_tuple = bank[q_idx]

    expected_version = game_session.version
    new_turn_id = secrets.token_hex(8)
    now_ts = int(time.time())

    # Optimistic lock: ensure active_spell is null and version matches expected_version
    updated_rows = db.query(GameSession).filter(
        GameSession.id == game_session.id,
        GameSession.version == expected_version,
        GameSession.active_spell.is_(None),
    ).update(
        {
            GameSession.active_spell: spell_id,
            GameSession.active_question_json: json.dumps(q_tuple),
            GameSession.turn_id: new_turn_id,
            GameSession.version: GameSession.version + 1,
            GameSession.updated_at: now_ts,
        },
        synchronize_session=False,
    )
    db.commit()

    if updated_rows == 0:
        from app.observability.metrics import metrics_registry
        metrics_registry.record_combat_concurrency_conflict(game_session.id, "concurrent_select_spell")
        raise HTTPException(409, "Conflict selecting spell due to concurrent action. Please refresh state.")

    db.refresh(game_session)

    logger.info(
        "Spell selected: '%s' by user %s vs %s (chapter=%d, turn_id=%s, cursor_q_idx=%d)",
        spell_id,
        current_user.username,
        boss_slug,
        game_session.chapter,
        game_session.turn_id,
        q_idx,
    )

    return format_game_state(game_session, current_user)


@router.post("/battle/answer")
def answer_question(
    body: AnswerRequest,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    target_sid = body.session_id or session_id
    session_repo = SessionRepository(db)
    game_session = session_repo.get_by_id(target_sid) if target_sid else session_repo.get_by_user_id(current_user.id)
    if not game_session:
        raise HTTPException(404, "Session not found")

    if game_session.user_id != current_user.id:
        raise HTTPException(403, "Not authorized to access this session")

    # Validate turn_id presence
    submitted_turn_id = (body.turn_id or "").strip()
    if not submitted_turn_id:
        raise HTTPException(400, "Missing turn_id. A valid server-issued turn_id is required.")

    # Validate active turn state
    if not game_session.active_spell or not game_session.active_question_json:
        raise HTTPException(400, "No active question. Select a spell first.")

    # Validate turn_id matching & consumption
    if not game_session.turn_id:
        from app.observability.metrics import metrics_registry
        metrics_registry.record_combat_concurrency_conflict(game_session.id, "consumed_or_inactive_turn_id")
        raise HTTPException(409, "Turn ID has already been consumed or is not active. Please refresh state.")

    if game_session.turn_id != submitted_turn_id:
        from app.observability.metrics import metrics_registry
        metrics_registry.record_combat_concurrency_conflict(game_session.id, "invalid_or_consumed_turn_id")
        raise HTTPException(409, "Invalid or previously consumed turn ID. Please refresh state.")

    # Validate expiration
    if (time.time() - (game_session.updated_at or 0)) > TURN_EXPIRATION_SECONDS:
        from app.observability.metrics import metrics_registry
        metrics_registry.record_combat_concurrency_conflict(game_session.id, "turn_id_expired")
        raise HTTPException(409, "Turn has expired. Please select a spell again.")

    active_q = json.loads(game_session.active_question_json)
    q_prompt, choices, correct_answer = active_q[0], active_q[1], active_q[2]

    effective = resolve_content_source(current_user.content_source if current_user else game_session.content_source)
    is_json_like = (effective != "app")
    bundle = get_content_bundle(effective)
    explanation = bundle.explanations.get(q_prompt, f"The correct answer is {correct_answer}.")

    # Resolve dynamic spell damage for this question / boss
    chapters = bundle.chapters
    ch_idx = max(0, min(game_session.chapter - 1, len(chapters) - 1))
    bosses = chapters[ch_idx]["bosses"]
    boss_slug = bosses[max(0, min(game_session.boss_index, len(bosses) - 1))][0]
    cursor_key = f"{game_session.chapter}:{boss_slug}"

    if is_json_like:
        boss_values = bundle.boss_spell_values.get((game_session.chapter, boss_slug)) or bundle.boss_spell_values.get(boss_slug) or []
        question_spell_values = (
            bundle.spell_values.get((game_session.chapter, boss_slug, q_prompt))
            or boss_values
            or bundle.spell_values.get(q_prompt)
            or []
        )
        if question_spell_values and game_session.active_spell in JSON_SPELL_IDS_BY_RANK:
            rank_idx = JSON_SPELL_IDS_BY_RANK.index(game_session.active_spell)
            spell_dmg = question_spell_values[rank_idx] if rank_idx < len(question_spell_values) else get_spell(game_session.active_spell).damage
            custom_dmg = {game_session.active_spell: int(spell_dmg)}
        else:
            custom_dmg = None
    else:
        custom_dmg = None

    # Evaluate pure combat turn
    turn_result, new_player_hp, new_boss_hp = evaluate_combat_turn(
        spell_id=game_session.active_spell,
        submitted_answer=body.answer,
        question_prompt=q_prompt,
        correct_answer=correct_answer,
        explanation=explanation,
        current_player_hp=game_session.player_hp,
        current_boss_hp=game_session.boss_hp,
        custom_spell_damage=custom_dmg,
    )

    # Cooldown updates
    cooldowns = json.loads(game_session.cooldowns_json) if game_session.cooldowns_json else {}
    cooldowns = apply_spell_cooldown(cooldowns, game_session.active_spell)

    # Advance question cursor sequentially
    cursors = json.loads(game_session.question_cursors_json) if hasattr(game_session, "question_cursors_json") and game_session.question_cursors_json else {}
    cursors[cursor_key] = cursors.get(cursor_key, 0) + 1

    # Log entries
    log = json.loads(game_session.log_json) if game_session.log_json else []
    spell = get_spell(game_session.active_spell)
    if turn_result.correct:
        log.append(f"Direct hit! {spell.name} dealt {turn_result.damage} damage to the boss.")
        if turn_result.boss_hit:
            log.append(f"Boss counterattacked for {turn_result.boss_counterattack_damage} damage!")
        if turn_result.defeated:
            log.append("Victory! Boss has been defeated!")
    else:
        log.append(f"Spell fizzled! Backfired for {turn_result.self_damage} damage. Correct answer: {correct_answer}")

    if turn_result.defeat:
        log.append("Defeat! Your aura has faded. Regroup and retry the battle.")

    logger.info(
        "Combat turn: user %s answered correct=%s (spell=%s, damage=%d, boss_hp: %d->%d, player_hp: %d->%d)",
        current_user.username,
        turn_result.correct,
        game_session.active_spell,
        turn_result.damage,
        game_session.boss_hp,
        new_boss_hp,
        game_session.player_hp,
        new_player_hp,
    )
    if turn_result.defeated:
        logger.info("Boss DEFEATED: %s beaten by user %s (chapter=%d)", boss_slug, current_user.username, game_session.chapter)
    elif turn_result.defeat:
        logger.warning("Player DEFEATED: %s fell to boss %s (chapter=%d)", current_user.username, boss_slug, game_session.chapter)

    # Optimistic Concurrency Update
    expected_version = body.expected_version if body.expected_version is not None else game_session.version
    if game_session.version != expected_version:
        from app.observability.metrics import metrics_registry
        metrics_registry.record_combat_concurrency_conflict(game_session.id, "optimistic_version_mismatch")
        raise HTTPException(
            status_code=409,
            detail="Combat session was modified by a concurrent turn. Please refresh your state.",
        )
    now_ts = int(time.time())

    updated_rows = db.query(GameSession).filter(
        GameSession.id == game_session.id,
        GameSession.version == expected_version,
    ).update(
        {
            GameSession.player_hp: new_player_hp,
            GameSession.boss_hp: new_boss_hp,
            GameSession.cooldowns_json: json.dumps(cooldowns),
            GameSession.question_cursors_json: json.dumps(cursors),
            GameSession.log_json: json.dumps(log[-10:]),
            GameSession.active_spell: None,
            GameSession.active_question_json: None,
            GameSession.turn_id: None,
            GameSession.version: GameSession.version + 1,
            GameSession.updated_at: now_ts,
        },
        synchronize_session=False,
    )
    db.commit()

    if updated_rows == 0:
        from app.observability.metrics import metrics_registry
        metrics_registry.record_combat_concurrency_conflict(game_session.id, "concurrent_update_race")
        raise HTTPException(
            status_code=409,
            detail="Combat session was modified by a concurrent turn. Please refresh your state.",
        )

    db.refresh(game_session)

    # Format battle response
    state = format_game_state(game_session, current_user)
    return {
        **state,
        "correct": turn_result.correct,
        "damage": turn_result.damage,
        "self_damage": turn_result.self_damage,
        "boss_hit": turn_result.boss_hit,
        "defeated": turn_result.defeated,
        "defeat": turn_result.defeat,
        "correct_answer": turn_result.correct_answer,
        "explanation": turn_result.explanation,
        "question_prompt": turn_result.question_prompt,
    }


@router.post("/battle/next-turn")
def next_turn(
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

    effective = resolve_content_source(current_user.content_source if current_user else game_session.content_source)
    bundle = get_content_bundle(effective)
    chapters = bundle.chapters

    ch_idx = max(0, min(game_session.chapter - 1, len(chapters) - 1))
    bosses = chapters[ch_idx]["bosses"]

    # Record completed boss
    current_boss_slug = bosses[max(0, min(game_session.boss_index, len(bosses) - 1))][0]
    completed = json.loads(game_session.completed_json) if game_session.completed_json else []
    if current_boss_slug not in completed:
        completed.append(current_boss_slug)

    new_chapter = game_session.chapter
    new_boss_index = game_session.boss_index
    new_boss_hp = game_session.boss_hp
    new_player_hp = game_session.player_hp

    # Advance boss or chapter
    if game_session.boss_index + 1 < len(bosses):
        new_boss_index = game_session.boss_index + 1
        next_boss = bosses[new_boss_index]
        new_boss_hp = next_boss[2]
        new_player_hp = game_session.player_max_hp
        log = [f"Approaching Boss {new_boss_index + 1}: {next_boss[1]}."]
        victory = False
    elif game_session.chapter < len(chapters):
        new_chapter = game_session.chapter + 1
        new_boss_index = 0
        next_ch = chapters[new_chapter - 1]
        next_boss = next_ch["bosses"][0]
        new_boss_hp = next_boss[2]
        new_player_hp = game_session.player_max_hp
        log = [f"Entered Chapter {new_chapter}: {next_ch['name']}. Face {next_boss[1]}!"]
        victory = False
    else:
        victory = True
        log = ["Victory! All chapters and bosses have been vanquished!"]

    expected_version = game_session.version
    now_ts = int(time.time())

    updated_rows = db.query(GameSession).filter(
        GameSession.id == game_session.id,
        GameSession.version == expected_version,
    ).update(
        {
            GameSession.chapter: new_chapter,
            GameSession.boss_index: new_boss_index,
            GameSession.boss_hp: new_boss_hp,
            GameSession.player_hp: new_player_hp,
            GameSession.cooldowns_json: "{}",
            GameSession.completed_json: json.dumps(completed),
            GameSession.log_json: json.dumps(log),
            GameSession.active_spell: None,
            GameSession.active_question_json: None,
            GameSession.turn_id: None,
            GameSession.version: GameSession.version + 1,
            GameSession.updated_at: now_ts,
        },
        synchronize_session=False,
    )
    db.commit()

    if updated_rows == 0:
        raise HTTPException(409, "Combat session was updated concurrently. Please refresh state.")

    db.refresh(game_session)

    state = format_game_state(game_session, current_user)
    state["victory"] = victory
    return state


@router.post("/battle/retry")
def retry_battle(
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

    effective = resolve_content_source(current_user.content_source if current_user else game_session.content_source)
    bundle = get_content_bundle(effective)
    chapters = bundle.chapters
    ch_idx = max(0, min(game_session.chapter - 1, len(chapters) - 1))
    boss = chapters[ch_idx]["bosses"][max(0, min(game_session.boss_index, len(chapters[ch_idx]["bosses"]) - 1))]

    expected_version = game_session.version
    now_ts = int(time.time())

    updated_rows = db.query(GameSession).filter(
        GameSession.id == game_session.id,
        GameSession.version == expected_version,
    ).update(
        {
            GameSession.player_hp: game_session.player_max_hp,
            GameSession.boss_hp: boss[2],
            GameSession.active_spell: None,
            GameSession.active_question_json: None,
            GameSession.cooldowns_json: "{}",
            GameSession.log_json: json.dumps([f"Regrouped. Battle with {boss[1]} restarted!"]),
            GameSession.turn_id: None,
            GameSession.version: GameSession.version + 1,
            GameSession.updated_at: now_ts,
        },
        synchronize_session=False,
    )
    db.commit()

    if updated_rows == 0:
        raise HTTPException(409, "Combat session was updated concurrently. Please refresh state.")

    db.refresh(game_session)

    return format_game_state(game_session, current_user)
