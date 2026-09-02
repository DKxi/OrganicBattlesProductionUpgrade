import json
from pathlib import Path
import pytest
from app.domain.content.loader import load_json_bundle
from app.settings import settings


def test_boss_strategy_integrity_across_all_27_chapters():
    """Verify that all 27 chapter JSON files define a valid boss_strategy that matches their question dataset."""
    data_dir = settings.root_dir / "data" / "tracks" / "default"
    if not data_dir.exists():
        data_dir = settings.root_dir / "data"
    manifest_path = data_dir / "manifest.json"
    assert manifest_path.exists(), "data/manifest.json must exist"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chapter_entries = manifest.get("chapters", [])
    assert len(chapter_entries) == 27, "Manifest must list all 27 chapters"

    for entry in chapter_entries:
        chapter_path = data_dir / entry["file"]
        assert chapter_path.exists(), f"Chapter file {entry['file']} must exist"

        data = json.loads(chapter_path.read_text(encoding="utf-8"))
        chapter_num = int(data.get("chapter", 0))
        assert "boss_strategy" in data, f"Chapter {chapter_num} missing boss_strategy object"

        strategy = data["boss_strategy"]
        assert "description" in strategy
        assert "progression" in strategy
        assert "distribution" in strategy

        distribution = strategy["distribution"]
        assert len(distribution) == 5, f"Chapter {chapter_num} strategy must define 5 bosses"

        questions = data.get("questions", [])
        assert len(questions) == 50, f"Chapter {chapter_num} must have 50 total questions"

        for b_index, b_info in enumerate(distribution):
            boss_name = b_info["boss"]
            b_qs = [q for q in questions if q.get("boss") == boss_name]

            # 1. Total questions per boss must match strategy
            assert len(b_qs) == b_info["total"], f"Chapter {chapter_num} {boss_name}: expected {b_info['total']} questions, found {len(b_qs)}"
            assert b_info["total"] == 10

            # 2. Difficulty distribution must match strategy
            easy_qs = [q for q in b_qs if q.get("difficulty") == "easy"]
            med_qs = [q for q in b_qs if q.get("difficulty") == "medium"]
            hard_qs = [q for q in b_qs if q.get("difficulty") == "hard"]

            assert len(easy_qs) == b_info["easy"], f"Chapter {chapter_num} {boss_name}: expected {b_info['easy']} easy, got {len(easy_qs)}"
            assert len(med_qs) == b_info["medium"], f"Chapter {chapter_num} {boss_name}: expected {b_info['medium']} medium, got {len(med_qs)}"
            assert len(hard_qs) == b_info["hard"], f"Chapter {chapter_num} {boss_name}: expected {b_info['hard']} hard, got {len(hard_qs)}"

            # 3. Strategy progression rule: easy decreases by 1, med is 4, hard increases by 1
            assert b_info["easy"] == 6 - b_index
            assert b_info["medium"] == 4
            assert b_info["hard"] == b_index


def test_gameplay_boss_health_and_spells_follow_strategy():
    """Verify that ContentBundle correctly loads boss HP and spell tiers from boss_strategy."""
    bundle = load_json_bundle(settings.root_dir)
    assert len(bundle.chapters) == 27

    for ch in bundle.chapters:
        ch_id = ch["id"]
        bosses = ch["bosses"]
        assert len(bosses) == 5, f"Chapter {ch_id} must have 5 bosses loaded"

        # Expected progressive health: 100, 200, 300, 400, 500
        expected_healths = [100, 200, 300, 400, 500]
        # Expected progressive spell tiers
        expected_spells = [
            [20, 30, 45],
            [25, 35, 50],
            [30, 40, 55],
            [35, 45, 60],
            [40, 50, 65],
        ]

        for b_idx, boss_tuple in enumerate(bosses):
            boss_slug, boss_name, boss_hp, boss_dmg, boss_kind, boss_lore, boss_img = boss_tuple

            # Verify HP matches strategy
            assert boss_hp == expected_healths[b_idx], f"Chapter {ch_id} boss {boss_name} HP {boss_hp} != expected {expected_healths[b_idx]}"

            # Verify question bank contains 10 questions for this boss
            q_bank = bundle.question_boss_bank.get((ch_id, boss_slug), [])
            assert len(q_bank) == 10, f"Chapter {ch_id} boss {boss_name} question count {len(q_bank)} != 10"

            # Verify boss spell damages match strategy
            sp_vals = bundle.boss_spell_values.get((ch_id, boss_slug), [])
            assert sp_vals == expected_spells[b_idx], f"Chapter {ch_id} boss {boss_name} spell damage {sp_vals} != {expected_spells[b_idx]}"


def test_boss_image_resolution_and_fallback_support():
    """Verify that boss assets resolve to valid png files or fallback to boss-placeholder.svg."""
    bundle = load_json_bundle(settings.root_dir)
    boss_dir = settings.root_dir / "static" / "assets" / "bosses"
    assert boss_dir.is_dir(), "static/assets/bosses directory must exist"
    placeholder = boss_dir / "boss-placeholder.svg"
    assert placeholder.exists(), "boss-placeholder.svg must exist for fallback rendering"

    # Verify that first 15 chapters have dedicated PNG assets
    found_assets = 0
    for ch in bundle.chapters[:15]:
        for boss_tuple in ch["bosses"]:
            img_name = boss_tuple[6]
            img_path = boss_dir / img_name
            if img_path.exists():
                found_assets += 1

    assert found_assets >= 70, f"Expected at least 70 unique boss PNGs, found {found_assets}"

