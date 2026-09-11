#!/usr/bin/env python3
"""
Deployment Cache Warming Script for Organic Battles.
Preloads and caches popular tracks so users experience instantaneous cold-start loads.
"""
import sys
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.settings import settings
from app.infrastructure.cache.shared_cache import shared_track_cache


def main():
    parser = argparse.ArgumentParser(description="Warm cache for popular tracks")
    parser.add_argument(
        "--tracks",
        type=str,
        default=settings.popular_tracks_to_warm or "default,adv-vocab,found-nomenclature",
        help="Comma-separated list of track IDs to warm",
    )
    args = parser.parse_args()

    track_ids = [t.strip() for t in args.tracks.split(",") if t.strip()]
    print(f"🔥 Warming track cache for tracks: {track_ids}...")
    results = shared_track_cache.warm_tracks(settings.root_dir, track_ids)
    for tid, res in results.items():
        print(f"   ✓ {tid}: {res['status']} (release: {res.get('release_id')}, duration: {res.get('duration_ms', 0)}ms)")
    print("✨ Cache warming complete. Current cache telemetry:")
    print(shared_track_cache.stats())


if __name__ == "__main__":
    main()
