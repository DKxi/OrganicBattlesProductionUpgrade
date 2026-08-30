import json
import time
import secrets
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Response, Depends, HTTPException, Header, Cookie
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.settings import settings
from app.api.deps import get_db, auth_admin, limiter, get_content_bundle
from app.infrastructure.database.models import User, GameSession
from app.infrastructure.identity.crypto import code_hash, hash_password
from app.infrastructure.cache.memory import set_admin_token, revoke_admin_token
from app.domain.content.resolver import resolve_content_source

router = APIRouter(tags=["Admin Management"])


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminUserConfigRequest(BaseModel):
    content_source: Optional[str] = None


class AdminUserCredentialsRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class SessionResetRequest(BaseModel):

    chapter: int = Field(..., ge=1, description="Target chapter to reset battle session to")


@router.post("/admin/login")
@limiter.limit("10/minute")
def admin_login(request: Request, body: AdminLoginRequest, response: Response):
    if body.username != settings.admin_username or body.password != settings.admin_password:
        raise HTTPException(401, "Incorrect admin username or password")

    token = secrets.token_urlsafe(40)
    thash = code_hash(token)
    set_admin_token(thash, settings.admin_session_ttl_hours * 3600)

    response.set_cookie(
        "admin_token",
        token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=settings.admin_session_ttl_hours * 3600,
    )
    return {"token": token, "username": settings.admin_username, "status": "ok"}


@router.get("/admin/status")
def admin_status(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_db)):
    total_users = db.query(User).count()
    total_sessions = db.query(GameSession).count()
    return {
        "status": "ok",
        "admin_user": admin_info["username"],
        "env_content_source": settings.game_content_source,
        "default_mode": "app",
        "total_users": total_users,
        "total_sessions": total_sessions,
    }


@router.get("/admin/users")
def admin_get_users(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    sessions = {s.user_id: s for s in db.query(GameSession).all()}
    result = []
    for u in users:
        sess = sessions.get(u.id)
        effective = resolve_content_source(u.content_source)
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "verified": bool(u.verified),
            "content_source": u.content_source,
            "effective_mode": effective,
            "chapter": sess.chapter if sess else 1,
            "boss_index": sess.boss_index if sess else 0,
            "player_hp": sess.player_hp if sess else 150,
            "created_at": u.created_at,
        })
    return {"users": result, "total": len(result)}


@router.post("/admin/users/{user_id}/config")
def admin_update_user_config(
    user_id: str,
    body: AdminUserConfigRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    if body.content_source is not None:
        target = body.content_source.strip().lower() if body.content_source else None
        if target and target not in ("app", "json"):
            raise HTTPException(400, "content_source must be 'app', 'json', or null")
        user.content_source = target

        # Synchronize game session if present
        game_session = db.query(GameSession).filter(GameSession.user_id == user.id).first()
        if game_session:
            game_session.content_source = target
            game_session.active_question_json = None
            game_session.active_spell = None
            effective = resolve_content_source(target)
            bundle = get_content_bundle(effective)
            chapters = bundle.chapters
            if game_session.chapter > len(chapters):
                game_session.chapter = 1
                game_session.boss_index = 0
                game_session.boss_hp = chapters[0]["bosses"][0][2]
            else:
                bosses = chapters[game_session.chapter - 1]["bosses"]
                if game_session.boss_index >= len(bosses):
                    game_session.boss_index = 0
                    game_session.boss_hp = bosses[0][2]
                else:
                    game_session.boss_hp = bosses[game_session.boss_index][2]

    db.commit()
    db.refresh(user)

    effective = resolve_content_source(user.content_source)
    return {
        "status": "ok",
        "user_id": user.id,
        "username": user.username,
        "content_source": user.content_source,
        "effective_mode": effective,
        "env_override": bool(settings.game_content_source),
    }


@router.post("/admin/users/{user_id}/credentials")
def admin_update_user_credentials(
    user_id: str,
    body: AdminUserCredentialsRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    updated_fields = []

    # 1. Update Username if requested
    if body.username is not None and body.username.strip():
        new_username = body.username.strip()
        if len(new_username) < 3 or len(new_username) > 24:
            raise HTTPException(400, "Username must be between 3 and 24 characters")
        existing = db.query(User).filter(User.username == new_username, User.id != user.id).first()
        if existing:
            raise HTTPException(400, f"Username '{new_username}' is already taken")
        user.username = new_username
        updated_fields.append("username")

    # 2. Update Password if requested
    if body.password is not None and body.password.strip():
        new_password = body.password.strip()
        if len(new_password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters long")
        user.password_hash = hash_password(new_password)
        updated_fields.append("password")

    if not updated_fields:
        raise HTTPException(400, "No credentials provided to update")

    db.commit()
    db.refresh(user)

    return {
        "status": "ok",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "updated": updated_fields,
        "message": f"Successfully updated {', '.join(updated_fields)} for {user.email}",
    }



@router.get("/admin/sessions")
def admin_get_sessions(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_db)):
    game_sessions = db.query(GameSession).order_by(GameSession.updated_at.desc()).all()
    users = {u.id: u for u in db.query(User).all()}
    result = []
    for s in game_sessions:
        u = users.get(s.user_id)
        effective = resolve_content_source(u.content_source if u else s.content_source)
        bundle = get_content_bundle(effective)
        chapters = bundle.chapters
        ch_idx = max(0, min(s.chapter - 1, len(chapters) - 1))
        ch_data = chapters[ch_idx]
        bosses = ch_data["bosses"]
        b_idx = max(0, min(s.boss_index, len(bosses) - 1))
        boss = bosses[b_idx]
        try:
            completed_list = json.loads(s.completed_json)
        except Exception:
            completed_list = []

        result.append({
            "session_id": s.id,
            "user_id": s.user_id,
            "username": u.username if u else "Unknown User",
            "email": u.email if u else "Unknown",
            "content_source": s.content_source,
            "effective_mode": effective,
            "chapter": s.chapter,
            "chapter_name": ch_data["name"],
            "boss_index": s.boss_index,
            "boss_name": boss[1],
            "boss_hp": s.boss_hp,
            "boss_max_hp": boss[2],
            "player_hp": s.player_hp,
            "player_max_hp": s.player_max_hp,
            "completed_count": len(completed_list),
            "updated_at": s.updated_at,
            "available_chapters": [{"id": ch["id"], "name": ch["name"]} for ch in chapters],
        })
    return {"sessions": result, "total": len(result)}


@router.post("/admin/sessions/{session_id}/reset")
def admin_reset_session(
    session_id: str,
    body: SessionResetRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    game_session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not game_session:
        raise HTTPException(404, "Session not found")

    user = db.query(User).filter(User.id == game_session.user_id).first()
    effective = resolve_content_source(user.content_source if user else game_session.content_source)
    bundle = get_content_bundle(effective)
    chapters = bundle.chapters

    if body.chapter < 1 or body.chapter > len(chapters):
        raise HTTPException(400, f"Chapter must be between 1 and {len(chapters)}")

    target_chapter = body.chapter
    first_boss = chapters[target_chapter - 1]["bosses"][0]

    game_session.chapter = target_chapter
    game_session.boss_index = 0
    game_session.boss_hp = first_boss[2]
    game_session.player_hp = game_session.player_max_hp
    game_session.active_question_json = None
    game_session.active_spell = None
    game_session.turn_id = None
    game_session.cooldowns_json = "{}"
    game_session.log_json = json.dumps([f"Battle reset by Administrator to Chapter {target_chapter} ({first_boss[1]})."])
    game_session.version += 1
    game_session.updated_at = int(time.time())

    if user:
        try:
            progress = json.loads(user.progress_json) if user.progress_json else {}
        except Exception:
            progress = {}
        progress.update({
            "chapter": target_chapter,
            "boss_index": 0,
            "boss_hp": first_boss[2],
            "player_hp": game_session.player_max_hp,
            "active_question": None,
            "active_spell": None,
            "turn_id": None,
            "cooldowns": {},
            "log": [f"Battle reset by Administrator to Chapter {target_chapter} ({first_boss[1]})."],
        })
        user.progress_json = json.dumps(progress)

    db.commit()
    db.refresh(game_session)

    return {
        "status": "ok",
        "message": f"Session reset to Chapter {target_chapter} ({first_boss[1]})",
        "session_id": game_session.id,
        "chapter": game_session.chapter,
        "boss_index": game_session.boss_index,
        "boss_name": first_boss[1],
        "boss_hp": game_session.boss_hp,
        "player_hp": game_session.player_hp,
    }


@router.delete("/admin/sessions/{session_id}")
@router.post("/admin/sessions/{session_id}/delete")
def admin_delete_session(
    session_id: str,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
):
    game_session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not game_session:
        raise HTTPException(404, "Session not found")

    user = db.query(User).filter(User.id == game_session.user_id).first()
    if user:
        user.progress_json = None

    db.delete(game_session)
    db.commit()

    return {"status": "ok", "message": "Session deleted successfully", "session_id": session_id}


@router.post("/admin/logout")
def admin_logout(
    response: Response,
    authorization: Optional[str] = Header(default=None),
    admin_token: Optional[str] = Cookie(default=None),
):
    raw = admin_token or (authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None)
    if raw:
        thash = code_hash(raw)
        revoke_admin_token(thash)
    response.delete_cookie("admin_token")
    return {"status": "ok"}
