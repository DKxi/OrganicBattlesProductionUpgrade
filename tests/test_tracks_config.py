from pathlib import Path
from app.settings import settings
from app.domain.content.loader import (
    load_tracks_config,
    get_track_config,
    load_track_bundle,
    load_json_bundle,
)
from app.api.deps import get_content_bundle
from app.domain.content.resolver import resolve_content_source


def test_load_tracks_config():
    config = load_tracks_config(settings.root_dir)
    assert "curricula" in config
    assert "tracks" in config
    assert len(config["curricula"]) >= 2
    assert len(config["tracks"]) == 20

    # Verify curricula
    curricula_ids = {c["id"] for c in config["curricula"]}
    assert "advanced" in curricula_ids
    assert "foundational" in curricula_ids

    # Verify track properties
    for track in config["tracks"]:
        assert "id" in track
        assert "curriculum" in track
        assert "title" in track
        assert "data_folder" in track
        assert "boss_folder" in track
        assert "questions" in track
        assert "chapters" in track
        assert track["curriculum"] in ("advanced", "foundational")


def test_get_track_config():
    track = get_track_config(settings.root_dir, "adv-outcomes")
    assert track is not None
    assert track["title"] == "Reaction Outcomes"
    assert track["curriculum"] == "advanced"
    assert track["chapters"] == 27
    assert track["data_folder"] == "data/tracks/advanced/ReactionOutComeTypesData"
    assert track["boss_folder"] == "data/tracks/advanced/bosses"


def test_default_track_config_and_bundle_loading():
    """Verify default track settings in tracks_config.json and bundle loading from data/tracks/default."""
    track = get_track_config(settings.root_dir, "default")
    assert track is not None
    assert track["id"] == "default"
    assert track["data_folder"] == "data/tracks/default"
    assert track["boss_folder"] == "data/tracks/default/bosses"

    # Verify bundle loads from data/tracks/default
    bundle = load_track_bundle(settings.root_dir, "default")
    assert bundle is not None
    assert bundle.data_dir == settings.root_dir / "data" / "tracks" / "default"
    assert bundle.boss_dir == settings.root_dir / "data" / "tracks" / "default" / "bosses"
    assert len(bundle.chapters) == 27
    assert bundle.source_name == "track:default"

    # Verify first boss Orbital Ogre image exists in default boss folder
    first_ch = bundle.chapters[0]
    first_boss = first_ch["bosses"][0]
    assert first_boss[1] == "Orbital Ogre"
    expected_boss_img = settings.root_dir / "data" / "tracks" / "default" / "bosses" / first_boss[6]
    assert expected_boss_img.is_file(), f"Boss image '{first_boss[6]}' should exist in default boss_folder"


def test_load_track_bundle_advanced_matching_folder():
    """Verify selecting an advanced track loads 27 chapters from matching data_folder and bosses."""
    bundle = load_track_bundle(settings.root_dir, "adv-vocab")
    assert bundle is not None
    assert len(bundle.chapters) == 27
    assert len(bundle.questions) == 1350
    assert bundle.source_name == "track:adv-vocab"

    # Verify matching boss images exist in boss_folder
    first_ch = bundle.chapters[0]
    assert len(first_ch["bosses"]) >= 1
    first_boss = first_ch["bosses"][0]
    assert first_boss[0] == "valence-vanguard"
    boss_img_file = Path(first_boss[6])
    expected_boss_path = settings.root_dir / "data" / "tracks" / "advanced" / "bosses" / boss_img_file.name
    assert expected_boss_path.is_file(), f"Boss image '{boss_img_file.name}' should exist in track boss_folder"


def test_load_track_bundle_fallback_to_data_folder():
    """Verify that any mismatch/missing folder falls back gracefully to default track folder."""
    # 1. Foundational track whose folder does not exist yet
    bundle = load_track_bundle(settings.root_dir, "found-nomenclature")
    assert bundle is not None
    assert len(bundle.chapters) == 27  # loaded from default track
    assert len(bundle.questions) >= 1
    assert bundle.source_name == "track:found-nomenclature"
    assert bundle.data_dir == settings.root_dir / "data" / "tracks" / "default"
    assert bundle.boss_dir == settings.root_dir / "data" / "tracks" / "default" / "bosses"

    # 2. Unknown / non-existent track
    unknown_bundle = load_track_bundle(settings.root_dir, "unknown-track-id")
    assert unknown_bundle is not None
    assert len(unknown_bundle.chapters) == 27
    assert unknown_bundle.source_name == "track:unknown-track-id"

    # 3. Custom invalid folder path
    invalid_bundle = load_track_bundle(settings.root_dir, "adv-vocab", custom_folder="non/existent/path")
    assert invalid_bundle is not None
    assert len(invalid_bundle.chapters) == 27
    assert invalid_bundle.source_name == "track:adv-vocab"


def test_track_content_source_resolution_and_bundle_cache():
    """Verify resolver and deps.get_content_bundle seamlessly handle tracks."""
    effective = resolve_content_source("track:adv-outcomes")
    assert effective == "track:adv-outcomes"

    bundle = get_content_bundle("track:adv-outcomes")
    assert bundle is not None
    assert len(bundle.chapters) == 27
    assert len(bundle.questions) == 1350


def test_serve_boss_image_from_track_boss_folder():
    """Verify boss images from data/tracks/advanced/bosses are served over HTTP."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. Image from advanced bosses folder
    res1 = client.get("/static/assets/bosses/valence-vanguard.png")
    assert res1.status_code == 200
    assert "image" in res1.headers.get("content-type", "")

    res2 = client.get("/bosses/carbocation-colossus.png")
    assert res2.status_code == 200
    assert "image" in res2.headers.get("content-type", "")

    # 2. Image from fallback static folder
    res3 = client.get("/static/assets/bosses/boss-placeholder.svg")
    assert res3.status_code == 200

    # 3. Missing image falls back to placeholder SVG
    res4 = client.get("/static/assets/bosses/completely-unknown-boss.png")
    assert res4.status_code == 200
    assert "svg" in res4.headers.get("content-type", "")


def test_track_available_spells_and_incorrect_answer_explanation():
    """Verify track mode restricts spells to matching ranks and returns explanation on incorrect answer."""
    import uuid
    from fastapi.testclient import TestClient
    from app.main import app
    from app.infrastructure.database.engine import SessionLocal
    from app.infrastructure.database.models import User
    from app.infrastructure.identity.crypto import hash_password

    client = TestClient(app)

    # Check that index.html includes the view-explanation button
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert 'id="view-explanation"' in index_res.text

    # Create user
    user_id = str(uuid.uuid4())
    username = f"track_user_{uuid.uuid4().hex[:6]}"
    with SessionLocal() as db:
        u = User(id=user_id, email=f"{username}@example.com", username=username, password_hash=hash_password("Pass123!"), verified=1)
        db.add(u)
        db.commit()

    login_res = client.post("/api/auth/login", json={"username": username, "password": "Pass123!"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Start game
    game_res = client.post("/api/game/new", headers=headers, json={})
    sid = game_res.json()["session_id"]

    # Select track
    track_res = client.post("/api/game/track", headers=headers, json={"session_id": sid, "track_id": "adv-vocab"})
    assert track_res.status_code == 200
    track_session = track_res.json()["session"]

    # 1. Spells must only have the 3 rank spells active
    spell_damage = track_session["spell_damage"]
    assert len(spell_damage) == 3
    assert set(spell_damage.keys()) == {"fire-spark", "resonance-burst", "mechanism-storm"}

    # 2. Unavailable spell should be rejected with 409
    bad_spell_res = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "acid-shot"})
    assert bad_spell_res.status_code == 409

    # 3. Available spell succeeds
    good_spell_res = client.post("/api/battle/select-spell", headers=headers, json={"session_id": sid, "spell_id": "fire-spark"})
    assert good_spell_res.status_code == 200
    question = good_spell_res.json()["question"]
    assert question["prompt"]

    # 4. Incorrect answer returns full explanation and correct answer
    wrong_answer = "Completely Incorrect Chemistry Distractor"
    ans_res = client.post("/api/battle/answer", headers=headers, json={"session_id": sid, "answer": wrong_answer})
    assert ans_res.status_code == 200
    ans_data = ans_res.json()
    assert ans_data["correct"] is False
    assert ans_data["correct_answer"]
    assert ans_data["explanation"]
    assert len(ans_data["explanation"]) > 10
