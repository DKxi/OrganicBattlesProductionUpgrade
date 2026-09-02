import time
from typing import Optional, Dict, Any
from fastapi import Request, Depends, HTTPException, Header, Cookie
from sqlalchemy.orm import Session as DBSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.settings import settings
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import User
from app.infrastructure.database.repositories import UserRepository, AuthRepository
from app.infrastructure.identity.crypto import code_hash
from app.infrastructure.cache.memory import get_admin_token_expiry
from app.domain.content.entities import ContentBundle
from app.domain.content.loader import load_app_bundle, load_json_bundle, load_track_bundle
from app.domain.content.resolver import resolve_content_source

import os
import sys

# Initialize rate limiter (disabled automatically during pytest test runs)
limiter = Limiter(
    key_func=get_remote_address,
    enabled=False if ("pytest" in sys.modules or os.getenv("TESTING") == "1" or os.getenv("PYTEST_CURRENT_TEST")) else True,
)

# Preload bundles in memory
APP_DATA: ContentBundle = load_app_bundle()
JSON_DATA: ContentBundle = load_json_bundle(settings.root_dir)
TRACK_BUNDLES: Dict[str, ContentBundle] = {}


def get_content_bundle(mode: str) -> ContentBundle:
    """Retrieve preloaded content bundle, including dynamic track bundles."""
    if mode.startswith("track:"):
        track_id = mode.split(":", 1)[1]
        if track_id not in TRACK_BUNDLES:
            TRACK_BUNDLES[track_id] = load_track_bundle(settings.root_dir, track_id)
        return TRACK_BUNDLES[track_id]
    if mode == "default" or mode.startswith("adv-") or mode.startswith("found-"):
        track_id = mode
        if track_id not in TRACK_BUNDLES:
            TRACK_BUNDLES[track_id] = load_track_bundle(settings.root_dir, track_id)
        return TRACK_BUNDLES[track_id]
    return JSON_DATA if mode == "json" else APP_DATA


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    session_token: Optional[str] = Cookie(default=None),
    db: DBSession = Depends(get_db),
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

    return user


def auth_admin(
    authorization: Optional[str] = Header(default=None),
    admin_token: Optional[str] = Cookie(default=None),
    session_token: Optional[str] = Cookie(default=None),
) -> Dict[str, Any]:
    """Validate administrator access."""
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
    expiry = get_admin_token_expiry(thash)
    if not expiry or expiry < time.time():
        raise HTTPException(401, "Admin session expired or invalid")

    return {"username": settings.admin_username, "is_admin": True}
