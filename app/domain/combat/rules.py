import time
import random
from typing import Dict, Tuple, Optional
from app.domain.combat.entities import TurnResult
from app.domain.combat.spells import get_spell


def grade_answer(submitted_answer: str, correct_answer: str) -> bool:
    """Pure domain rule comparing player's submitted answer with correct answer."""
    return submitted_answer.strip().lower() == correct_answer.strip().lower()


def evaluate_combat_turn(
    spell_id: str,
    submitted_answer: str,
    question_prompt: str,
    correct_answer: str,
    explanation: str,
    current_player_hp: int,
    current_boss_hp: int,
    custom_spell_damage: Optional[Dict[str, int]] = None,
    rng_roll: Optional[float] = None,
    counterattack_damage: Optional[int] = None,
) -> Tuple[TurnResult, int, int]:
    """
    Pure Python combat evaluation.
    Returns: (TurnResult, new_player_hp, new_boss_hp)
    """
    spell = get_spell(spell_id)
    base_damage = custom_spell_damage.get(spell_id, spell.damage) if custom_spell_damage else spell.damage

    is_correct = grade_answer(submitted_answer, correct_answer)

    if rng_roll is None:
        rng_roll = random.random()

    if is_correct:
        damage_dealt = base_damage
        self_damage = 0
        new_boss_hp = max(0, current_boss_hp - damage_dealt)
        defeated = new_boss_hp <= 0

        # Boss counterattacks only if still alive and roll succeeds
        if not defeated and rng_roll < 0.5:
            boss_hit = True
            boss_counter_dmg = counterattack_damage if counterattack_damage is not None else random.randint(10, 25)
            new_player_hp = max(0, current_player_hp - boss_counter_dmg)
        else:
            boss_hit = False
            boss_counter_dmg = 0
            new_player_hp = current_player_hp
    else:
        # Fizzle: spell backfires on player
        damage_dealt = 0
        self_damage = base_damage
        boss_hit = False
        boss_counter_dmg = 0
        new_boss_hp = current_boss_hp
        new_player_hp = max(0, current_player_hp - self_damage)
        defeated = False

    defeat = (new_player_hp <= 0)

    result = TurnResult(
        correct=is_correct,
        damage=damage_dealt,
        self_damage=self_damage,
        boss_hit=boss_hit,
        defeated=defeated,
        defeat=defeat,
        correct_answer=correct_answer,
        explanation=explanation,
        question_prompt=question_prompt,
        player_hp_after=new_player_hp,
        boss_hp_after=new_boss_hp,
        boss_counterattack_damage=boss_counter_dmg,
    )

    return result, new_player_hp, new_boss_hp


def is_spell_on_cooldown(cooldowns: Dict[str, float], spell_id: str, current_time: Optional[float] = None) -> bool:
    """Pure domain rule checking if a spell is on cooldown."""
    now = current_time if current_time is not None else time.time()
    return cooldowns.get(spell_id, 0) > now


def apply_spell_cooldown(cooldowns: Dict[str, float], spell_id: str, current_time: Optional[float] = None) -> Dict[str, float]:
    """Pure domain rule applying timestamp cooldown for newly cast spell."""
    spell = get_spell(spell_id)
    now = current_time if current_time is not None else time.time()
    updated = dict(cooldowns)
    if spell.cooldown > 0:
        updated[spell_id] = now + spell.cooldown
    return updated


def decrement_cooldowns(cooldowns: Dict[str, float]) -> Dict[str, float]:
    """Pure domain rule preserving timestamp cooldowns."""
    return dict(cooldowns)
