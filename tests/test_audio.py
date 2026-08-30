import re
from pathlib import Path
from starlette.testclient import TestClient
from app.main import app
from app.domain.combat.rules import evaluate_combat_turn


def test_audio_script_is_served():
    """Verify that audio.js is served properly as static asset."""
    client = TestClient(app)
    response = client.get("/static/js/audio.js")
    assert response.status_code == 200
    assert "SoundEngine" in response.text
    assert "soundEngine" in response.text


def test_audio_engine_methods_exist():
    """Verify that all required sound triggers and controls exist in static/js/audio.js."""
    audio_path = Path(__file__).parent.parent / "static" / "js" / "audio.js"
    assert audio_path.exists(), "audio.js must exist in static/js/"
    content = audio_path.read_text(encoding="utf-8")

    # Essential control methods
    assert "toggleMute()" in content or "toggleMute" in content
    assert "setMuted(" in content
    assert "isMuted()" in content
    assert "setVolume(" in content
    assert "getVolume()" in content

    # Essential SFX methods
    required_sfx = [
        "playClick",
        "playSpellCast",
        "playBossHit",
        "playPlayerHit",
        "playSpellFizzle",
        "playBossMiss",
        "playVictory",
        "playDefeat",
    ]
    for sfx in required_sfx:
        assert sfx in content, f"audio.js must implement {sfx}()"


def test_index_template_has_audio_mute_button():
    """Verify that index.html includes the audio toggle button."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="mute"' in response.text
    assert "AUDIO" in response.text


def test_main_js_imports_and_wires_audio():
    """Verify that main.js imports soundEngine and wires audio events."""
    main_js_path = Path(__file__).parent.parent / "static" / "js" / "main.js"
    content = main_js_path.read_text(encoding="utf-8")

    assert "import { soundEngine } from './audio.js" in content
    assert "soundEngine.playDefeat()" in content
    assert "soundEngine.playVictory()" in content
    assert "soundEngine.playSpellFizzle()" in content
    assert "soundEngine.playBossHit()" in content
    assert "soundEngine.toggleMute()" in content


def test_combat_outcomes_map_to_audio_triggers():
    """Verify domain combat returns flags that map deterministically to sound triggers."""
    # 1. Direct Hit with counterattack
    res_hit, _, _ = evaluate_combat_turn(
        spell_id="fire-spark",
        submitted_answer="correct",
        question_prompt="Test prompt",
        correct_answer="correct",
        explanation="Explanation",
        current_player_hp=150,
        current_boss_hp=100,
        rng_roll=0.1,  # counterattack lands
    )
    assert res_hit.correct is True
    assert res_hit.damage > 0
    assert res_hit.boss_hit is True  # Maps to playBossHit + playPlayerHit

    # 2. Direct Hit with boss miss
    res_miss, _, _ = evaluate_combat_turn(
        spell_id="fire-spark",
        submitted_answer="correct",
        question_prompt="Test prompt",
        correct_answer="correct",
        explanation="Explanation",
        current_player_hp=150,
        current_boss_hp=100,
        rng_roll=0.9,  # counterattack misses
    )
    assert res_miss.correct is True
    assert res_miss.boss_hit is False  # Maps to playBossHit + playBossMiss

    # 3. Fizzle / Backfire
    res_fizzle, _, _ = evaluate_combat_turn(
        spell_id="fire-spark",
        submitted_answer="wrong",
        question_prompt="Test prompt",
        correct_answer="correct",
        explanation="Explanation",
        current_player_hp=150,
        current_boss_hp=100,
    )
    assert res_fizzle.correct is False
    assert res_fizzle.self_damage > 0  # Maps to playSpellFizzle + playPlayerHit

    # 4. Defeat
    res_defeat, _, _ = evaluate_combat_turn(
        spell_id="fire-spark",
        submitted_answer="wrong",
        question_prompt="Test prompt",
        correct_answer="correct",
        explanation="Explanation",
        current_player_hp=10,
        current_boss_hp=100,
    )
    assert res_defeat.defeat is True  # Maps to playDefeat

    # 5. Victory
    res_victory, _, _ = evaluate_combat_turn(
        spell_id="fire-spark",
        submitted_answer="correct",
        question_prompt="Test prompt",
        correct_answer="correct",
        explanation="Explanation",
        current_player_hp=150,
        current_boss_hp=15,
    )
    assert res_victory.defeated is True  # Maps to playVictory
