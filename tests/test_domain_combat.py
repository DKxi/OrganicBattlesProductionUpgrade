import pytest
from app.domain.combat.rules import evaluate_combat_turn, grade_answer, decrement_cooldowns, apply_spell_cooldown
from app.domain.combat.spells import get_spell, SPELL_CATALOG
from app.domain.content.resolver import resolve_content_source


def test_grade_answer_exact_and_case_insensitive():
    assert grade_answer("sp3", "sp3") is True
    assert grade_answer("SP3", "sp3") is True
    assert grade_answer("  sp3  ", "sp3") is True
    assert grade_answer("sp2", "sp3") is False


def test_spell_catalog_integrity():
    assert len(SPELL_CATALOG) == 9
    fire_spark = get_spell("fire-spark")
    assert fire_spark.damage == 20
    assert fire_spark.cooldown == 1.5
    assert fire_spark.tier == "basic"

    mechanism_storm = get_spell("mechanism-storm")
    assert mechanism_storm.damage == 45
    assert mechanism_storm.cooldown == 10.0
    assert mechanism_storm.tier == "strong"



def test_combat_turn_correct_answer_deterministic():
    # Pure unit test with deterministic roll (rng_roll = 0.9 -> no counterattack)
    result, new_player_hp, new_boss_hp = evaluate_combat_turn(
        spell_id="fire-spark",
        submitted_answer="sp3",
        question_prompt="Identify hybridization of carbon in methane:",
        correct_answer="sp3",
        explanation="Carbon in methane forms 4 sigma bonds.",
        current_player_hp=150,
        current_boss_hp=100,
        rng_roll=0.9,
    )

    assert result.correct is True
    assert result.damage == 20
    assert result.self_damage == 0
    assert result.boss_hit is False  # Counterattack missed
    assert result.defeated is False
    assert new_boss_hp == 80
    assert new_player_hp == 150


def test_combat_turn_correct_with_counterattack_deterministic():
    # Pure unit test with deterministic counterattack (rng_roll = 0.1 -> counterattack hits)
    result, new_player_hp, new_boss_hp = evaluate_combat_turn(
        spell_id="fire-spark",
        submitted_answer="sp3",
        question_prompt="Identify hybridization of carbon in methane:",
        correct_answer="sp3",
        explanation="Carbon in methane forms 4 sigma bonds.",
        current_player_hp=150,
        current_boss_hp=100,
        rng_roll=0.1,
        counterattack_damage=15,
    )

    assert result.correct is True
    assert result.damage == 20
    assert result.boss_hit is True
    assert result.boss_counterattack_damage == 15
    assert new_boss_hp == 80
    assert new_player_hp == 135


def test_combat_turn_fizzle_backfires_on_player():
    # Incorrect answer deals 0 to boss, full spell power to player
    result, new_player_hp, new_boss_hp = evaluate_combat_turn(
        spell_id="mechanism-storm",
        submitted_answer="wrong",
        question_prompt="Identify hybridization of carbon in methane:",
        correct_answer="sp3",
        explanation="Carbon in methane forms 4 sigma bonds.",
        current_player_hp=150,
        current_boss_hp=100,
    )

    assert result.correct is False
    assert result.damage == 0
    assert result.self_damage == 45
    assert result.boss_hit is False
    assert new_boss_hp == 100
    assert new_player_hp == 105
    assert result.correct_answer == "sp3"


def test_cooldown_management_pure_domain():
    from app.domain.combat.rules import is_spell_on_cooldown, apply_spell_cooldown
    fixed_time = 1000.0
    cooldowns = {}
    assert is_spell_on_cooldown(cooldowns, "resonance-burst", current_time=fixed_time) is False

    # Apply cooldown (5.0s)
    cooldowns = apply_spell_cooldown(cooldowns, "resonance-burst", current_time=fixed_time)
    assert cooldowns["resonance-burst"] == 1005.0
    assert is_spell_on_cooldown(cooldowns, "resonance-burst", current_time=1002.0) is True
    assert is_spell_on_cooldown(cooldowns, "resonance-burst", current_time=1006.0) is False



def test_content_source_priority_resolution_pure():
    # Priority 1: env override
    import os
    os.environ["GAME_CONTENT_SOURCE"] = "json"
    assert resolve_content_source("app") == "json"
    assert resolve_content_source(None) == "json"

    del os.environ["GAME_CONTENT_SOURCE"]
    # Priority 2: user database setting
    assert resolve_content_source("json") == "json"
    assert resolve_content_source("app") == "app"

    # Priority 3: default is json (Klein chapters)
    assert resolve_content_source(None) == "json"
    assert resolve_content_source("invalid") == "json"

