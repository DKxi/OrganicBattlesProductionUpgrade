import time
from typing import Optional, Dict, Any
from fastapi import Request, Depends, HTTPException, Header, Cookie
from sqlalchemy.orm import Session as DBSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.settings import settings
from app.infrastructure.database.engine import get_db, get_player_db, get_admin_db, set_session_user_context
from app.infrastructure.database.models import User
from app.infrastructure.database.repositories import UserRepository, AuthRepository
from app.infrastructure.identity.crypto import code_hash
from app.infrastructure.cache.memory import get_admin_token_expiry
from app.domain.content.entities import ContentBundle
from app.domain.content.loader import load_app_bundle, load_json_bundle, load_track_bundle
from app.domain.content.resolver import resolve_content_source

import os
import sys

from app.infrastructure.cache.track_cache import BoundedTrackCache

# Initialize rate limiter (distributed via Redis when REDIS_URL is configured, in-memory otherwise; disabled in tests)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url if settings.redis_url else "memory://",
    enabled=False if ("pytest" in sys.modules or os.getenv("TESTING") == "1" or os.getenv("PYTEST_CURRENT_TEST")) else True,
)

# Preload bundles in memory
APP_DATA: ContentBundle = load_app_bundle()
JSON_DATA: ContentBundle = load_json_bundle(settings.root_dir)
TRACK_BUNDLES: BoundedTrackCache = BoundedTrackCache(
    max_size=settings.max_cached_tracks,
    ttl_seconds=settings.track_cache_ttl_seconds,
)


from app.infrastructure.cache.shared_cache import shared_track_cache


def get_content_bundle(mode: str) -> ContentBundle:
    """Retrieve preloaded content bundle, including dynamic track bundles with bounded versioned caching."""
    if mode.startswith("track:") or mode == "default" or mode.startswith("adv-") or mode.startswith("found-"):
        raw_track = mode[6:] if mode.startswith("track:") else mode
        if ":" in raw_track:
            parts = raw_track.split(":", 1)
            track_id = parts[0]
            source_identity = parts[1]
        else:
            track_id = raw_track
            source_identity = "db"

        # Check in-memory process dictionary first
        cache_lookup_key = f"{track_id}:{source_identity}" if source_identity != "db" else track_id
        if cache_lookup_key in TRACK_BUNDLES:
            return TRACK_BUNDLES[cache_lookup_key]

        # 1. Resolve active release version for this track
        rel_id = shared_track_cache.get_content_version(track_id) if source_identity == "db" else "custom"

        # 2. Check shared/bounded cache by (track_id, source_identity, release_id)
        bundle = shared_track_cache.get(track_id, rel_id, source_identity=source_identity)
        if bundle is not None:
            return bundle

        # 3. Cache miss: acquire per-track rebuild lock (prevents concurrent duplicate builds)
        lock = shared_track_cache.get_track_rebuild_lock(track_id, source_identity=source_identity)
        with lock:
            # Double check if another worker/thread completed the build
            bundle = shared_track_cache.get(track_id, rel_id, source_identity=source_identity)
            if bundle is not None:
                return bundle

            start_t = time.time()
            bundle = load_track_bundle(settings.root_dir, track_id)
            duration_ms = (time.time() - start_t) * 1000.0

            shared_track_cache.set(
                track_id,
                rel_id,
                bundle,
                load_duration_ms=duration_ms,
                source_identity=source_identity,
            )
            TRACK_BUNDLES[cache_lookup_key] = bundle

        return bundle
    return JSON_DATA if mode == "json" else APP_DATA


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    session_token: Optional[str] = Cookie(default=None),
    db: DBSession = Depends(get_player_db),
) -> User:
    """Validate user authentication via Bearer token or HttpOnly session_token cookie."""
    raw = None
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
    elif session_token:
        raw = session_token

    if not raw:
        raise HTTPException(401, "Authentication required")

    thash = code_hash(raw)
    auth_repo = AuthRepository(db)
    session_row = auth_repo.get_session(thash)
    if not session_row:
        raise HTTPException(401, "Session expired or invalid")

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(session_row.user_id)
    if not user:
        raise HTTPException(401, "User not found")

    # Establish transaction-local RLS player context
    set_session_user_context(db, user.id)
    return user


def auth_admin(
    authorization: Optional[str] = Header(default=None),
    admin_token: Optional[str] = Cookie(default=None),
    session_token: Optional[str] = Cookie(default=None),
    db: DBSession = Depends(get_admin_db),
) -> Dict[str, Any]:
    """Validate administrator access against database-stored admin users and sessions."""
    raw = None
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
    elif admin_token:
        raw = admin_token
    elif session_token:
        raw = session_token

    if not raw:
        raise HTTPException(401, "Admin authentication required")

    thash = code_hash(raw)
    from app.infrastructure.database.admin_repo import AdminRepository
    admin_repo = AdminRepository(db)
    admin_session = admin_repo.get_session(thash)

    if not admin_session:
        # Fallback to in-memory check for backwards compatibility if needed
        expiry = get_admin_token_expiry(thash)
        if not expiry or expiry < time.time():
            raise HTTPException(401, "Admin session expired or invalid")
        admin = admin_repo.get_by_username("admin")
        if admin:
            return {
                "id": admin.id,
                "admin_id": admin.id,
                "username": admin.username,
                "role": admin.role,
                "is_admin": True,
            }
        return {
            "id": "admin_default",
            "admin_id": "admin_default",
            "username": "admin",
            "role": "superadmin",
            "is_admin": True,
        }

    admin_user = admin_repo.get_by_id(admin_session.admin_user_id)
    if not admin_user or not admin_user.is_active:
        raise HTTPException(401, "Admin account disabled or not found")

    admin_repo.update_session_activity(thash)

    return {
        "id": admin_user.id,
        "admin_id": admin_user.id,
        "username": admin_user.username,
        "role": admin_user.role,
        "is_admin": True,
    }

