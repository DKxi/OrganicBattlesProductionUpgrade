from pathlib import Path
from app.settings import settings
from app.domain.content.loader import (
    load_tracks_config,
    get_track_config,
    load_track_bundle,
    load_json_bundle,
)


def test_load_tracks_config():
    config = load_tracks_config(settings.root_dir)
    assert "curricula" in config
    assert "tracks" in config
    assert len(config["curricula"]) >= 2
    assert len(config["tracks"]) == 19

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
        assert "questions" in track
        assert "chapters" in track
        assert track["curriculum"] in ("advanced", "foundational")


def test_get_track_config():
    track = get_track_config(settings.root_dir, "adv-outcomes")
    assert track is not None
    assert track["title"] == "Reaction Outcomes"
    assert track["curriculum"] == "advanced"
    assert track["chapters"] == 27
    assert track["data_folder"] == "data/tracks/ReactionOutComeTypesData"


def test_load_track_bundle_fallback():
    # If custom folder does not exist yet, fallback to default data bundle
    bundle = load_track_bundle(settings.root_dir, "adv-outcomes")
    assert bundle is not None
    assert len(bundle.chapters) >= 1
    assert len(bundle.questions) >= 1
    assert bundle.source_name.startswith("track:adv-outcomes")
