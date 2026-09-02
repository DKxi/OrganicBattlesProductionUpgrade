import json
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.settings import settings
from app.main import app
from app.domain.content.loader import (
    load_json_bundle,
    load_track_bundle,
    json_available_spells,
    JSON_SPELL_IDS_BY_RANK,
    _slug,
)
from app.domain.combat.rules import evaluate_combat_turn
from app.infrastructure.database.engine import SessionLocal
from app.infrastructure.database.models import User, GameSession
from app.infrastructure.identity.crypto import hash_password


def test_track_content_bundle_spells_and_health_from_json():
    """
    Verify that ContentBundle loads exact spells, health, and boss metadata from the track JSON files.
    Tests:
    1. Boss name, health, and image loaded per JSON.
    2. Exact damage numbers for each spell loaded into spell_values and boss_spell_values.
    3. json_available_spells accurately maps the rank 1, 2, and 3 damage numbers.
    """
    vocab_dir = settings.root_dir / "data" / "tracks" / "advanced" / "VocabularyConceptsData"
    ch1_file = vocab_dir / "chapter_01.json"
    assert ch1_file.is_file(), "Track chapter_01.json must exist"

    raw_json = json.loads(ch1_file.read_text(encoding="utf-8"))
    json_boss_name = raw_json.get("assigned_boss")
    first_q = raw_json["questions"][0]
    expected_spells = first_q["spells"]
    expected_health = first_q["health"][0]
    expected_image = first_q["images"][0]

    bundle = load_track_bundle(settings.root_dir, "adv-vocab")
    ch1 = bundle.chapters[0]
    first_boss = ch1["bosses"][0]

    # 1. Boss Name, Image, and Max Health from JSON
    assert first_boss[1] == json_boss_name
    assert first_boss[6] == expected_image
    assert first_boss[2] == expected_health, f"Expected boss health {expected_health}, got {first_boss[2]}"

    # 2. Spell damage values loaded into bundle from JSON
    boss_slug = first_boss[0]
    loaded_boss_spells = bundle.boss_spell_values.get((1, boss_slug))
    assert loaded_boss_spells == expected_spells, f"Expected boss spells {expected_spells}, got {loaded_boss_spells}"

    # Verify spell damage values for each question prompt
    for q in raw_json["questions"][:10]:
        q_boss_slug = _slug(q.get("boss") or json_boss_name)
        loaded = bundle.spell_values.get((1, q_boss_slug, q["question"])) or bundle.spell_values.get(q["question"])
        assert loaded == q["spells"], (
            f"Question '{q['question'][:30]}' spell damage mismatch: expected {q['spells']}, got {loaded}"
        )

    # 3. Verify rank damage numbers in json_available_spells match JSON values
    mapped_spells = json_available_spells(expected_spells)
    assert mapped_spells["fire-spark"] == expected_spells[0], f"Rank 1 damage should be {expected_spells[0]}"
    assert mapped_spells["resonance-burst"] == expected_spells[1], f"Rank 2 damage should be {expected_spells[1]}"
    assert mapped_spells["mechanism-storm"] == expected_spells[2], f"Rank 3 damage should be {expected_spells[2]}"


def test_all_27_chapters_spell_damages_match_json():
    """
    Exhaustively verify across all 27 chapters of an advanced track that:
    1. Every chapter's questions and boss define valid spell damage values.
    2. When the bundle is loaded, the boss_spell_values and spell_values for every question
       match the exact damage integers in the chapter JSON file.
    3. json_available_spells produces the exact damage numbers for all 3 active spell ranks.
    """
    vocab_dir = settings.root_dir / "data" / "tracks" / "advanced" / "VocabularyConceptsData"
    bundle = load_track_bundle(settings.root_dir, "adv-vocab")
    assert len(bundle.chapters) == 27, "Must load 27 chapters"

    for ch_num in range(1, 28):
        ch_file = vocab_dir / f"chapter_{ch_num:02d}.json"
        assert ch_file.is_file(), f"Chapter {ch_num} JSON must exist"
        data = json.loads(ch_file.read_text(encoding="utf-8"))

        chapter_boss_name = data.get("assigned_boss")
        boss_slug = _slug(chapter_boss_name)

        first_q = data["questions"][0]
        json_spells = first_q["spells"]
        json_health = first_q["health"][0]

        # Verify boss health in bundle
        bundle_ch = bundle.chapters[ch_num - 1]
        bundle_boss = bundle_ch["bosses"][0]
        assert bundle_boss[2] == json_health, f"Ch {ch_num}: expected HP {json_health}, got {bundle_boss[2]}"

        # Verify boss spell damages in bundle
        boss_spells = bundle.boss_spell_values.get((ch_num, boss_slug))
        assert boss_spells == json_spells, f"Ch {ch_num}: expected boss spells {json_spells}, got {boss_spells}"

        # Verify available spells damage values match JSON exactly
        avail_spells = json_available_spells(boss_spells)
        assert avail_spells["fire-spark"] == json_spells[0], f"Ch {ch_num} Rank 1 damage mismatch"
        assert avail_spells["resonance-burst"] == json_spells[1], f"Ch {ch_num} Rank 2 damage mismatch"
        assert avail_spells["mechanism-storm"] == json_spells[2], f"Ch {ch_num} Rank 3 damage mismatch"

        # Verify every question in this chapter has exact spell damage loaded
        for q_item in data["questions"]:
            prompt = q_item["question"]
            q_boss_slug = _slug(q_item.get("boss") or chapter_boss_name)
            loaded_sp = bundle.spell_values.get((ch_num, q_boss_slug, prompt)) or bundle.spell_values.get(prompt)
            assert loaded_sp == q_item["spells"], f"Ch {ch_num}: question spell damage mismatch"


def test_arbitrary_custom_json_spells_and_health(tmp_path):
    """
    Verify that arbitrary custom spell damage and health numbers in JSON are strictly honored.
    Tests:
    1. Custom health (240) and custom spells ([33, 58, 92]) loaded into bundle.
    2. Available spells dictionary contains exact damages: fire-spark=33, resonance-burst=58, mechanism-storm=92.
    3. Combat turn execution with evaluate_combat_turn deals the EXACT custom damage numbers.
    """
    custom_spells = [33, 58, 92]
    custom_health = 240
    custom_boss = "Entropy Enchanter"
    custom_image = "entropy-enchanter.png"

    sample_chapter = {
        "schema_version": 2.0,
        "chapter": 1,
        "chapter_title": "Thermodynamic Chaos",
        "assigned_boss": custom_boss,
        "questions": [
            {
                "id": "tc_001",
                "chapter": 1,
                "boss": custom_boss,
                "topic": "Entropy",
                "question": "What happens to the entropy of the universe in a spontaneous process?",
                "options": [
                    {"label": "A", "text": "It always increases."},
                    {"label": "B", "text": "It always decreases."},
                    {"label": "C", "text": "It remains exactly zero."},
                    {"label": "D", "text": "It fluctuates unpredictably."}
                ],
                "correct_option": "A",
                "correct_answer": "It always increases.",
                "explanation": "The Second Law of Thermodynamics states that the entropy of the universe increases in any spontaneous process.",
                "spells": custom_spells,
                "health": [custom_health],
                "images": [custom_image]
            }
        ]
    }

    ch1_path = tmp_path / "chapter_01.json"
    ch1_path.write_text(json.dumps(sample_chapter), encoding="utf-8")

    bundle = load_json_bundle(settings.root_dir, data_dir=tmp_path)

    # 1. Verify Health from JSON
    boss_entry = bundle.chapters[0]["bosses"][0]
    assert boss_entry[1] == custom_boss
    assert boss_entry[2] == custom_health
    assert boss_entry[6] == custom_image

    # 2. Verify Spells from JSON
    boss_slug = boss_entry[0]
    assert bundle.boss_spell_values[(1, boss_slug)] == custom_spells
    avail_spells = json_available_spells(custom_spells)
    assert avail_spells == {
        "fire-spark": 33,
        "resonance-burst": 58,
        "mechanism-storm": 92
    }

    # 3. Verify Combat Turn Damage for each custom spell
    spell_damage_tests = [
        ("fire-spark", 33),
        ("resonance-burst", 58),
        ("mechanism-storm", 92),
    ]
    for spell_id, expected_dmg in spell_damage_tests:
        custom_dmg = {spell_id: expected_dmg}
        turn_result, player_hp, boss_hp_after = evaluate_combat_turn(
            spell_id=spell_id,
            submitted_answer="It always increases.",
            question_prompt="What happens to the entropy of the universe in a spontaneous process?",
            correct_answer="It always increases.",
            explanation="The Second Law...",
            current_player_hp=100,
            current_boss_hp=custom_health,
            custom_spell_damage=custom_dmg,
        )
        assert turn_result.correct is True
        assert turn_result.damage == expected_dmg, f"Spell {spell_id} should deal {expected_dmg} DMG, got {turn_result.damage}"
        assert boss_hp_after == custom_health - expected_dmg, f"Boss HP should be {custom_health - expected_dmg}, got {boss_hp_after}"


def test_user_choice_switches_spells_health_and_boss_end_to_end():
    """
    Verify end-to-end through the API that when a user selects a track:
    1. The boss name, health, and image load from that track's JSON.
    2. Available spells and their damage values reflect the JSON spells array [20, 30, 45].
    3. Combat turns with each spell reduce boss health by the exact damage specified in the JSON:
       - fire-spark deals 20 damage
       - resonance-burst deals 30 damage
       - mechanism-storm deals 45 damage
    """
    client = TestClient(app)

    # Register and login user
    username = f"tester_{uuid.uuid4().hex[:6]}"
    user_id = str(uuid.uuid4())
    with SessionLocal() as db:
        u = User(id=user_id, email=f"{username}@example.com", username=username, password_hash=hash_password("Password123!"), verified=1)
        db.add(u)
        db.commit()

    login_res = client.post("/api/auth/login", json={"username": username, "password": "Password123!"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Start game session (defaults to master data/)
    game_res = client.post("/api/game/new", headers=headers, json={})
    assert game_res.status_code == 200
    sid = game_res.json()["session_id"]
    init_boss = game_res.json()["boss"]
    assert init_boss["name"] == "Orbital Ogre"
    assert init_boss["hp"] == 100

    # 2. User selects track 'adv-vocab'
    track_res = client.post("/api/game/track", headers=headers, json={
        "session_id": sid,
        "track_id": "adv-vocab"
    })
    assert track_res.status_code == 200
    track_data = track_res.json()
    new_session = track_data["session"]

    # Boss health must be loaded from adv-vocab chapter_01.json
    assert new_session["boss"]["name"] == "Valence Vanguard"
    assert new_session["boss"]["hp"] == 100
    assert new_session["boss"]["max_hp"] == 100
    assert new_session["boss"]["image"] == "valence-vanguard.png"

    # Spells must only contain the 3 ranks with damages from the JSON [20, 30, 45]
    spell_damage = new_session["spell_damage"]
    assert spell_damage == {
        "fire-spark": 20,
        "resonance-burst": 30,
        "mechanism-storm": 45
    }

    # Load bundle to query correct answers for testing combat damages
    bundle = load_track_bundle(settings.root_dir, "adv-vocab")
    answer_key = {p: c for p, ch, c in bundle.questions}

    # 3. Test combat turn for each of the 3 spells to verify exact damage dealt per the JSON
    current_boss_hp = 100
    spells_to_test = [
        ("fire-spark", 20),
        ("resonance-burst", 30),
        ("mechanism-storm", 45),
    ]

    for spell_id, expected_dmg in spells_to_test:
        sel_res = client.post("/api/battle/select-spell", headers=headers, json={
            "session_id": sid,
            "spell_id": spell_id
        })
        assert sel_res.status_code == 200
        prompt = sel_res.json()["question"]["prompt"]
        correct_answer = answer_key[prompt]

        # Submit correct answer
        ans_res = client.post("/api/battle/answer", headers=headers, json={
            "session_id": sid,
            "answer": correct_answer
        })
        assert ans_res.status_code == 200
        combat_data = ans_res.json()

        assert combat_data["correct"] is True
        assert combat_data["damage"] == expected_dmg, (
            f"Spell {spell_id} should deal {expected_dmg} damage per JSON, got {combat_data['damage']}"
        )
        expected_hp_after = current_boss_hp - expected_dmg
        assert combat_data["boss"]["hp"] == expected_hp_after, (
            f"Boss HP after {spell_id} should be {expected_hp_after}, got {combat_data['boss']['hp']}"
        )
        current_boss_hp = expected_hp_after


def test_custom_data_folder_override_loads_custom_spells_and_health(tmp_path):
    """
    Verify that when user configures a custom data folder with custom JSON:
    1. The game loads the custom boss health and custom spells from that folder.
    2. Available spells dictionary reflects the custom damages: [15, 35, 75].
    3. Combat with each spell deals the exact custom damage numbers defined in the JSON.
    """
    client = TestClient(app)

    username = f"custom_{uuid.uuid4().hex[:6]}"
    user_id = str(uuid.uuid4())
    with SessionLocal() as db:
        u = User(id=user_id, email=f"{username}@example.com", username=username, password_hash=hash_password("Password123!"), verified=1)
        db.add(u)
        db.commit()

    login_res = client.post("/api/auth/login", json={"username": username, "password": "Password123!"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    game_res = client.post("/api/game/new", headers=headers, json={})
    sid = game_res.json()["session_id"]

    # Create custom chapter JSON in tmp_path with custom damages: 15, 35, 75
    custom_chapter = {
        "schema_version": 2.0,
        "chapter": 1,
        "chapter_title": "Custom Mastery Lab",
        "assigned_boss": "Kinetics Kraken",
        "questions": [
            {
                "id": "c_001",
                "chapter": 1,
                "boss": "Kinetics Kraken",
                "topic": "Reaction Rates",
                "question": "What is the rate law for a zero-order reaction?",
                "options": [
                    {"label": "A", "text": "Rate = k"},
                    {"label": "B", "text": "Rate = k[A]"},
                    {"label": "C", "text": "Rate = k[A]^2"},
                    {"label": "D", "text": "Rate = k/[A]"}
                ],
                "correct_option": "A",
                "correct_answer": "Rate = k",
                "explanation": "A zero-order reaction has a constant rate independent of reactant concentration: Rate = k.",
                "spells": [15, 35, 75],
                "health": [160],
                "images": ["kinetics-kraken.png"]
            }
        ]
    }
    (tmp_path / "chapter_01.json").write_text(json.dumps(custom_chapter), encoding="utf-8")

    # Set track with custom data_folder override
    res = client.post("/api/game/track", headers=headers, json={
        "session_id": sid,
        "track_id": "adv-vocab",
        "data_folder": str(tmp_path)
    })
    assert res.status_code == 200
    session_data = res.json()["session"]

    # Verify custom boss health and custom spell damages were loaded from the custom folder
    assert session_data["boss"]["name"] == "Kinetics Kraken"
    assert session_data["boss"]["hp"] == 160
    assert session_data["boss"]["max_hp"] == 160
    assert session_data["spell_damage"] == {
        "fire-spark": 15,
        "resonance-burst": 35,
        "mechanism-storm": 75
    }

    # Test casting all 3 custom spells in combat through the API
    custom_spells_to_test = [
        ("fire-spark", 15),
        ("resonance-burst", 35),
        ("mechanism-storm", 75),
    ]
    current_hp = 160
    for spell_id, expected_dmg in custom_spells_to_test:
        sel = client.post("/api/battle/select-spell", headers=headers, json={
            "session_id": sid,
            "spell_id": spell_id
        })
        assert sel.status_code == 200

        ans = client.post("/api/battle/answer", headers=headers, json={
            "session_id": sid,
            "answer": "Rate = k"
        })
        assert ans.status_code == 200
        ans_data = ans.json()
        assert ans_data["correct"] is True
        assert ans_data["damage"] == expected_dmg, f"Expected {expected_dmg} damage, got {ans_data['damage']}"
        expected_hp = current_hp - expected_dmg
        assert ans_data["boss"]["hp"] == expected_hp, f"Expected boss HP {expected_hp}, got {ans_data['boss']['hp']}"
        current_hp = expected_hp


def test_switch_track_from_advanced_to_foundational_fallback():
    """
    Verify unloading and loading bundles when switching tracks:
    1. User logs in and selects 'adv-vocab' (Advanced track):
       - Loads advanced bundle from data/tracks/advanced/VocabularyConceptsData
       - Loads boss from data/tracks/advanced/bosses (Valence Vanguard)
       - Serves advanced boss image valence-vanguard.png
       - Plays a combat turn against Valence Vanguard
    2. User logs in again and selects 'found-nomenclature' (Foundational track):
       - Since Foundational data_folder and boss_folder do NOT exist on disk,
         the system falls back to:
         * data/ folder for questions/chapters (data_dir == root_dir / 'data')
         * bosses/ folder outside data/ for bosses (boss_dir == root_dir / 'bosses')
       - Active boss becomes Orbital Ogre (HP 100, image orbital-ogre.png)
       - Serves fallback boss image orbital-ogre.png directly from bosses/ folder outside data
       - Plays a combat turn against Orbital Ogre using data/ chapter questions
    """
    client = TestClient(app)

    # 1. User signs up and logs in
    username = f"relogin_{uuid.uuid4().hex[:6]}"
    user_id = str(uuid.uuid4())
    with SessionLocal() as db:
        u = User(id=user_id, email=f"{username}@example.com", username=username, password_hash=hash_password("Password123!"), verified=1)
        db.add(u)
        db.commit()

    login_res1 = client.post("/api/auth/login", json={"username": username, "password": "Password123!"})
    token1 = login_res1.json()["token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Start game session and pick 'adv-vocab' (Advanced track)
    game_res1 = client.post("/api/game/new", headers=headers1, json={})
    sid1 = game_res1.json()["session_id"]
    track_res1 = client.post("/api/game/track", headers=headers1, json={
        "session_id": sid1,
        "track_id": "adv-vocab"
    })
    assert track_res1.status_code == 200
    adv_session = track_res1.json()["session"]
    assert adv_session["mode"] == "track:adv-vocab"
    assert adv_session["boss"]["name"] == "Valence Vanguard"
    assert adv_session["boss"]["image"] == "valence-vanguard.png"

    # Verify advanced boss image is served via static route
    adv_img_res = client.get(f"/static/assets/bosses/{adv_session['boss']['image']}")
    assert adv_img_res.status_code == 200
    assert len(adv_img_res.content) > 0

    # Play a turn in advanced track
    bundle_adv = load_track_bundle(settings.root_dir, "adv-vocab")
    ans_key_adv = {p: c for p, ch, c in bundle_adv.questions}

    sel_res1 = client.post("/api/battle/select-spell", headers=headers1, json={
        "session_id": sid1,
        "spell_id": "fire-spark"
    })
    assert sel_res1.status_code == 200
    prompt1 = sel_res1.json()["question"]["prompt"]
    ans_res1 = client.post("/api/battle/answer", headers=headers1, json={
        "session_id": sid1,
        "answer": ans_key_adv[prompt1]
    })
    assert ans_res1.status_code == 200
    assert ans_res1.json()["correct"] is True
    assert ans_res1.json()["boss"]["name"] == "Valence Vanguard"
    assert ans_res1.json()["boss"]["hp"] == 80  # 100 - 20

    # 2. Complete Chapter 1 so that switching track is permitted
    with SessionLocal() as db:
        s = db.query(GameSession).filter(GameSession.user_id == user_id).first()
        s.chapter = 2
        s.boss_index = 0
        s.boss_hp = 100
        s.active_question_json = None
        s.active_spell = None
        db.commit()

    # User logs in again (new auth session) and starts new game with foundational track
    login_res2 = client.post("/api/auth/login", json={"username": username, "password": "Password123!"})
    token2 = login_res2.json()["token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    game_res2 = client.post("/api/game/new", headers=headers2, json={})
    sid2 = game_res2.json()["session_id"]

    # Select 'found-nomenclature' (Foundational track with non-existent folders)
    track_res2 = client.post("/api/game/track", headers=headers2, json={
        "session_id": sid2,
        "track_id": "found-nomenclature"
    })
    assert track_res2.status_code == 200
    found_session = track_res2.json()["session"]
    assert found_session["mode"] == "track:found-nomenclature"

    # Verifications for fallback to data/ and bosses/ outside data:
    # A. Active boss should be Orbital Ogre from master data/
    assert found_session["boss"]["name"] == "Orbital Ogre"
    assert found_session["boss"]["hp"] == 100
    assert found_session["boss"]["max_hp"] == 100
    assert found_session["boss"]["image"] == "orbital-ogre.png"

    # B. Boss image served from data/tracks/default/bosses
    found_img_res = client.get(f"/static/assets/bosses/{found_session['boss']['image']}")
    assert found_img_res.status_code == 200
    expected_default_img = settings.root_dir / "data" / "tracks" / "default" / "bosses" / "orbital-ogre.png"
    assert len(found_img_res.content) == expected_default_img.stat().st_size

    # C. Domain bundle loader verifies data_dir and boss_dir fallbacks to default track folder directly
    bundle_found = load_track_bundle(settings.root_dir, "found-nomenclature")
    assert bundle_found.data_dir == settings.root_dir / "data" / "tracks" / "default"
    assert bundle_found.boss_dir == settings.root_dir / "data" / "tracks" / "default" / "bosses"
    assert bundle_found.chapters[0]["bosses"][0][1] == "Orbital Ogre"

    # D. Play a turn in the fallback foundational track
    ans_key_found = {p: c for p, ch, c in bundle_found.questions}
    sel_res2 = client.post("/api/battle/select-spell", headers=headers2, json={
        "session_id": sid2,
        "spell_id": "fire-spark"
    })
    assert sel_res2.status_code == 200
    prompt2 = sel_res2.json()["question"]["prompt"]

    ans_res2 = client.post("/api/battle/answer", headers=headers2, json={
        "session_id": sid2,
        "answer": ans_key_found[prompt2]
    })
    assert ans_res2.status_code == 200
    assert ans_res2.json()["correct"] is True
    assert ans_res2.json()["boss"]["name"] == "Orbital Ogre"
    assert ans_res2.json()["boss"]["hp"] == 80  # 100 - 20


def test_default_track_direct_selection_and_combat():
    """
    Verify selecting 'default' track directly through API:
    1. Loads from data/tracks/default and data/tracks/default/bosses.
    2. Serves boss images from data/tracks/default/bosses.
    3. Executes battle turns against Orbital Ogre.
    """
    client = TestClient(app)

    username = f"default_user_{uuid.uuid4().hex[:6]}"
    user_id = str(uuid.uuid4())
    with SessionLocal() as db:
        u = User(id=user_id, email=f"{username}@example.com", username=username, password_hash=hash_password("Password123!"), verified=1)
        db.add(u)
        db.commit()

    login_res = client.post("/api/auth/login", json={"username": username, "password": "Password123!"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    game_res = client.post("/api/game/new", headers=headers, json={})
    sid = game_res.json()["session_id"]

    # Select 'default' track
    track_res = client.post("/api/game/track", headers=headers, json={
        "session_id": sid,
        "track_id": "default"
    })
    assert track_res.status_code == 200
    sess = track_res.json()["session"]
    assert sess["mode"] == "track:default"
    assert sess["boss"]["name"] == "Orbital Ogre"
    assert sess["boss"]["image"] == "orbital-ogre.png"

    # Verify boss image served from data/tracks/default/bosses
    img_res = client.get(f"/static/assets/bosses/{sess['boss']['image']}")
    assert img_res.status_code == 200
    default_img_file = settings.root_dir / "data" / "tracks" / "default" / "bosses" / "orbital-ogre.png"
    assert len(img_res.content) == default_img_file.stat().st_size

    # Play combat turn in default track
    bundle_def = load_track_bundle(settings.root_dir, "default")
    ans_key_def = {p: c for p, ch, c in bundle_def.questions}

    sel_res = client.post("/api/battle/select-spell", headers=headers, json={
        "session_id": sid,
        "spell_id": "fire-spark"
    })
    assert sel_res.status_code == 200
    prompt = sel_res.json()["question"]["prompt"]

    ans_res = client.post("/api/battle/answer", headers=headers, json={
        "session_id": sid,
        "answer": ans_key_def[prompt]
    })
    assert ans_res.status_code == 200
    combat = ans_res.json()
    assert combat["correct"] is True
    assert combat["damage"] == 20
    assert combat["boss"]["hp"] == 80


def test_track_switch_blocked_while_chapter_in_progress():
    """
    Verify that if a player is in the middle of a chapter:
    - Attempting to switch tracks returns HTTP 409 Conflict.
    - An informative message instructs the player to complete the current chapter first.
    - Active session remains unaffected.
    """
    client = TestClient(app)

    username = f"gate_user_{uuid.uuid4().hex[:6]}"
    user_id = str(uuid.uuid4())
    with SessionLocal() as db:
        u = User(id=user_id, email=f"{username}@example.com", username=username, password_hash=hash_password("Password123!"), verified=1)
        db.add(u)
        db.commit()

    token = client.post("/api/auth/login", json={"username": username, "password": "Password123!"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    game_res = client.post("/api/game/new", headers=headers, json={})
    sid = game_res.json()["session_id"]

    # Select 'adv-vocab' track
    client.post("/api/game/track", headers=headers, json={"session_id": sid, "track_id": "adv-vocab"})

    # Deal damage to boss (chapter is now in progress!)
    bundle = load_track_bundle(settings.root_dir, "adv-vocab")
    ans_key = {p: c for p, ch, c in bundle.questions}

    sel_res = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "fire-spark"})
    prompt = sel_res.json()["question"]["prompt"]
    client.post("/api/battle/answer", headers=headers, json={"session_id": sid, "answer": ans_key[prompt]})

    # Attempt to switch to 'default' track while Chapter 1 is in progress
    blocked_res = client.post("/api/game/track", headers=headers, json={"session_id": sid, "track_id": "default"})
    assert blocked_res.status_code == 409
    detail = blocked_res.json()["detail"]
    assert "Please complete Chapter 1" in detail
    assert "Vocabulary & Core Concepts" in detail  # Track title must be present
    assert "track" in detail
    assert "before switching tracks" in detail
    assert "Valence Vanguard" in detail

    # Verify active session is still adv-vocab with damaged boss
    state_res = client.get(f"/api/game/state?session_id={sid}", headers=headers)
    assert state_res.status_code == 200
    current_state = state_res.json()
    assert current_state["mode"] == "track:adv-vocab"
    assert current_state["boss"]["name"] == "Valence Vanguard"
    assert current_state["boss"]["hp"] == 80


def test_per_track_progress_archiving_and_restoration():
    """
    Verify per-track progress persistence:
    1. Advance Chapter 1 on track A -> Chapter 2.
    2. Switch to track B (fresh at Chapter 1).
    3. Advance Chapter 1 on track B -> Chapter 2.
    4. Switch back to track A -> restores Chapter 2.
    5. Switch back to track B -> restores Chapter 2.
    """
    client = TestClient(app)

    username = f"persist_{uuid.uuid4().hex[:6]}"
    user_id = str(uuid.uuid4())
    with SessionLocal() as db:
        u = User(id=user_id, email=f"{username}@example.com", username=username, password_hash=hash_password("Password123!"), verified=1)
        db.add(u)
        db.commit()

    token = client.post("/api/auth/login", json={"username": username, "password": "Password123!"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    game_res = client.post("/api/game/new", headers=headers, json={})
    sid = game_res.json()["session_id"]

    # 1. Start adv-vocab and complete Chapter 1 (simulated by advancing to Chapter 2 at boundary)
    client.post("/api/game/track", headers=headers, json={"session_id": sid, "track_id": "adv-vocab"})
    with SessionLocal() as db:
        s = db.query(GameSession).filter(GameSession.user_id == user_id).first()
        s.chapter = 2
        s.boss_index = 0
        s.boss_hp = 120
        s.active_question_json = None
        s.active_spell = None
        db.commit()

    # 2. Switch to 'default' track at chapter boundary -> succeeds!
    res_def = client.post("/api/game/track", headers=headers, json={"session_id": sid, "track_id": "default"})
    assert res_def.status_code == 200
    sess_def = res_def.json()["session"]
    assert sess_def["mode"] == "track:default"
    assert sess_def["chapter"] == 1  # Brand new track starts at Chapter 1
    assert sess_def["boss"]["name"] == "Orbital Ogre"

    # 3. Advance default track Chapter 1 -> Chapter 2 at boundary
    with SessionLocal() as db:
        s = db.query(GameSession).filter(GameSession.user_id == user_id).first()
        s.chapter = 2
        s.boss_index = 0
        s.boss_hp = 110
        s.active_question_json = None
        s.active_spell = None
        db.commit()

    # 4. Switch back to 'adv-vocab' -> restores saved Chapter 2!
    res_adv_back = client.post("/api/game/track", headers=headers, json={"session_id": sid, "track_id": "adv-vocab"})
    assert res_adv_back.status_code == 200
    sess_adv_back = res_adv_back.json()["session"]
    assert sess_adv_back["mode"] == "track:adv-vocab"
    assert sess_adv_back["chapter"] == 2
    assert sess_adv_back["boss"]["name"] == "Skeletal Sentry"

    # 5. Switch back to 'default' -> restores saved Chapter 2!
    res_def_back = client.post("/api/game/track", headers=headers, json={"session_id": sid, "track_id": "default"})
    assert res_def_back.status_code == 200
    sess_def_back = res_def_back.json()["session"]
    assert sess_def_back["mode"] == "track:default"
    assert sess_def_back["chapter"] == 2
    assert sess_def_back["boss"]["name"] == "Lewis Rune Knight"
