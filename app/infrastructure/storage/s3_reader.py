"""
S3 Storage Content Reader
-------------------------
Streams and parses question bank chapters from Supabase / AWS S3 buckets:
- DefaultTracks: Default track chapters (root level chapter_*.json)
- AdvancedTracks: Advanced tracks (<TrackFolder>/chapter_*.json)
- FoundationalTracks: Foundational tracks (<TrackFolder>/chapter_*.json)
"""
import re
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
import boto3
from botocore.config import Config

from app.settings import settings

logger = logging.getLogger("organicbattles.s3_reader")

# Mapping for foundational data_folder aliases
FOUNDATIONAL_FOLDER_ALIASES: Dict[str, str] = {
    "foundationalnomenclaturedata": "VocabularyConceptsData",
    "foundationalreactionoutcomesdata": "ReactionOutComeTypesData",
    "foundationalmechanismsdata": "MechanismsIntermediatesData",
    "foundationalstereochemistrydata": "StereochemistryStructureData",
    "foundationalpropertyrankingsdata": "RelativePropertyRankingsData",
    "foundationalspectroscopydata": "SpectroscopyElucidationData",
    "foundationalmultistepsynthesisdata": "MultiStepSynthesisData",
}


def get_s3_client():
    """Create a configured boto3 S3 client using application settings."""
    if not settings.s3_access_key_id or not settings.s3_secret_access_key:
        raise ValueError("S3 credentials (S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY) are not configured.")

    kwargs: Dict[str, Any] = {
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.s3_access_key_id,
        "aws_secret_access_key": settings.s3_secret_access_key,
        "config": Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url

    return boto3.client("s3", **kwargs)


def resolve_track_s3_location(
    track_id: str,
    curriculum: Optional[str] = None,
    data_folder: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Resolve (bucket_name, prefix) for a given track.
    
    Returns:
        (bucket_name, prefix_string)
        e.g. ('DefaultTracks', '') or ('AdvancedTracks', 'MechanismsIntermediatesData/')
    """
    folder_str = (data_folder or "").strip().replace("\\", "/")
    parts = [p for p in folder_str.split("/") if p]
    folder_name = parts[-1] if parts else ""

    # 1. Default track
    if track_id == "default" or (curriculum and curriculum.lower() == "default") or "default" in folder_str.lower():
        return settings.s3_default_tracks_bucket, ""

    # 2. Advanced tracks
    if (curriculum and curriculum.lower() == "advanced") or "advanced" in folder_str.lower():
        bucket = settings.s3_advanced_tracks_bucket
        prefix = f"{folder_name}/" if folder_name else ""
        return bucket, prefix

    # 3. Foundational tracks
    if (curriculum and curriculum.lower() == "foundational") or "foundational" in folder_str.lower():
        bucket = settings.s3_foundational_tracks_bucket
        # Check alias map for foundational folders
        mapped_folder = FOUNDATIONAL_FOLDER_ALIASES.get(folder_name.lower(), folder_name)
        prefix = f"{mapped_folder}/" if mapped_folder else ""
        return bucket, prefix

    # Fallback to Advanced or Default
    return settings.s3_advanced_tracks_bucket, f"{folder_name}/" if folder_name else ""


def extract_chapter_num_from_key(key: str) -> int:
    """Extract integer chapter number from an S3 key like '.../chapter_05.json'."""
    filename = key.split("/")[-1]
    match = re.search(r"chapter_(\d+)", filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 999


def list_track_chapter_keys(
    bucket: str,
    prefix: str = "",
    s3_client=None,
) -> List[str]:
    """
    List and numerically sort all chapter_*.json object keys in the specified bucket and prefix.
    """
    client = s3_client or get_s3_client()
    paginator = client.get_paginator("list_objects_v2")

    chapter_keys: List[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            filename = key.split("/")[-1]
            if filename.lower().startswith("chapter_") and filename.lower().endswith(".json"):
                chapter_keys.append(key)

    chapter_keys.sort(key=extract_chapter_num_from_key)
    return chapter_keys


def get_chapter_json(
    bucket: str,
    key: str,
    s3_client=None,
) -> Dict[str, Any]:
    """
    Download and parse a JSON chapter object directly into memory.
    """
    client = s3_client or get_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    body_bytes = response["Body"].read()
    return json.loads(body_bytes.decode("utf-8"))
