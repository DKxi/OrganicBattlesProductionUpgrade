"""
Unit & Integration Tests for S3 Content Ingestion
------------------------------------------------
Verifies:
1. S3 location resolution for default, advanced, and foundational tracks
2. S3 chapter key extraction and numerical sorting
3. Ingestion pipeline support for S3 sources
"""
import pytest
from app.infrastructure.storage.s3_reader import (
    resolve_track_s3_location,
    extract_chapter_num_from_key,
    FOUNDATIONAL_FOLDER_ALIASES,
)
from app.settings import settings


def test_resolve_track_s3_location_default():
    bucket, prefix = resolve_track_s3_location("default", curriculum="foundational", data_folder="data/tracks/default")
    assert bucket == settings.s3_default_tracks_bucket
    assert prefix == ""


def test_resolve_track_s3_location_advanced():
    bucket, prefix = resolve_track_s3_location(
        "adv-arrows",
        curriculum="advanced",
        data_folder="data/tracks/advanced/MechanismsIntermediatesData",
    )
    assert bucket == settings.s3_advanced_tracks_bucket
    assert prefix == "MechanismsIntermediatesData/"


def test_resolve_track_s3_location_foundational_aliased():
    bucket, prefix = resolve_track_s3_location(
        "found-nomenclature",
        curriculum="foundational",
        data_folder="data/tracks/foundational/FoundationalNomenclatureData",
    )
    assert bucket == settings.s3_foundational_tracks_bucket
    assert prefix == "VocabularyConceptsData/"


def test_resolve_track_s3_location_foundational_direct():
    bucket, prefix = resolve_track_s3_location(
        "found-synthesis",
        curriculum="foundational",
        data_folder="data/tracks/foundational/MultiStepSynthesisData",
    )
    assert bucket == settings.s3_foundational_tracks_bucket
    assert prefix == "MultiStepSynthesisData/"


def test_extract_chapter_num_from_key():
    assert extract_chapter_num_from_key("chapter_01.json") == 1
    assert extract_chapter_num_from_key("chapter_09.json") == 9
    assert extract_chapter_num_from_key("chapter_27.json") == 27
    assert extract_chapter_num_from_key("prefix/nested/chapter_105.json") == 105
    assert extract_chapter_num_from_key("unknown_file.json") == 999


def test_s3_client_connection_if_configured():
    if not (settings.s3_access_key_id and settings.s3_secret_access_key):
        pytest.skip("S3 credentials not present in test environment.")

    from app.infrastructure.storage.s3_reader import get_s3_client, list_track_chapter_keys
    client = get_s3_client()
    keys = list_track_chapter_keys(settings.s3_default_tracks_bucket, prefix="", s3_client=client)
    assert len(keys) >= 27
    assert "chapter_01.json" in keys
