import json
import time
import secrets
import random
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

router = APIRouter(tags=["Combat"])


class SelectSpellRequest(BaseModel):
    spell_id: str


class AnswerRequest(BaseModel):
    answer: str


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

    if effective == "json":
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

    game_session.active_spell = spell_id
    game_session.active_question_json = json.dumps(q_tuple)
    game_session.turn_id = secrets.token_hex(8)
    game_session.updated_at = int(time.time())
    db.commit()

    return format_game_state(game_session, current_user)


@router.post("/battle/answer")
def answer_question(
    body: AnswerRequest,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    session_repo = SessionRepository(db)
    game_session = session_repo.get_by_id(session_id) if session_id else session_repo.get_by_user_id(current_user.id)
    if not game_session:
        raise HTTPException(404, "Session not found")

    if not game_session.active_spell or not game_session.active_question_json:
        raise HTTPException(400, "No active question. Select a spell first.")

    active_q = json.loads(game_session.active_question_json)
    q_prompt, choices, correct_answer = active_q[0], active_q[1], active_q[2]

    effective = resolve_content_source(current_user.content_source if current_user else game_session.content_source)
    bundle = get_content_bundle(effective)
    explanation = bundle.explanations.get(q_prompt, f"The correct answer is {correct_answer}.")

    # Resolve dynamic spell damage for this question / boss
    chapters = bundle.chapters
    ch_idx = max(0, min(game_session.chapter - 1, len(chapters) - 1))
    bosses = chapters[ch_idx]["bosses"]
    boss_slug = bosses[max(0, min(game_session.boss_index, len(bosses) - 1))][0]
    cursor_key = f"{game_session.chapter}:{boss_slug}"

    if effective == "json":
        boss_values = bundle.boss_spell_values.get((game_session.chapter, boss_slug)) or bundle.boss_spell_values.get(boss_slug) or []
        question_spell_values = bundle.spell_values.get(q_prompt, boss_values) or boss_values
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
    game_session.question_cursors_json = json.dumps(cursors)



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

    # Save back to database
    game_session.player_hp = new_player_hp
    game_session.boss_hp = new_boss_hp
    game_session.cooldowns_json = json.dumps(cooldowns)
    game_session.log_json = json.dumps(log[-10:])
    game_session.active_spell = None
    game_session.active_question_json = None
    game_session.turn_id = None
    game_session.version += 1
    game_session.updated_at = int(time.time())
    db.commit()

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
    game_session.completed_json = json.dumps(completed)

    # Advance boss or chapter
    if game_session.boss_index + 1 < len(bosses):
        game_session.boss_index += 1
        next_boss = bosses[game_session.boss_index]
        game_session.boss_hp = next_boss[2]
        game_session.player_hp = game_session.player_max_hp
        game_session.cooldowns_json = "{}"
        log = [f"Approaching Boss {game_session.boss_index + 1}: {next_boss[1]}."]
        victory = False
    elif game_session.chapter < len(chapters):
        game_session.chapter += 1
        game_session.boss_index = 0
        next_ch = chapters[game_session.chapter - 1]
        next_boss = next_ch["bosses"][0]
        game_session.boss_hp = next_boss[2]
        game_session.player_hp = game_session.player_max_hp
        game_session.cooldowns_json = "{}"
        log = [f"Entered Chapter {game_session.chapter}: {next_ch['name']}. Face {next_boss[1]}!"]
        victory = False
    else:
        victory = True
        log = ["Victory! All chapters and bosses have been vanquished!"]

    game_session.log_json = json.dumps(log)
    game_session.version += 1
    game_session.updated_at = int(time.time())
    db.commit()

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

    effective = resolve_content_source(current_user.content_source if current_user else game_session.content_source)
    bundle = get_content_bundle(effective)
    chapters = bundle.chapters
    ch_idx = max(0, min(game_session.chapter - 1, len(chapters) - 1))
    boss = chapters[ch_idx]["bosses"][max(0, min(game_session.boss_index, len(chapters[ch_idx]["bosses"]) - 1))]

    game_session.player_hp = game_session.player_max_hp
    game_session.boss_hp = boss[2]
    game_session.active_spell = None
    game_session.active_question_json = None
    game_session.cooldowns_json = "{}"
    game_session.log_json = json.dumps([f"Regrouped. Battle with {boss[1]} restarted!"])
    game_session.version += 1
    game_session.updated_at = int(time.time())
    db.commit()

    return format_game_state(game_session, current_user)
