import os
import re
import json
import time
import secrets
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, Response, Depends, HTTPException, Header, Cookie, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.settings import settings
from app.api.deps import get_admin_db, auth_admin, limiter, get_content_bundle
from app.infrastructure.database.models import User, GameSession, Base
from app.infrastructure.identity.crypto import code_hash, hash_password
from app.infrastructure.cache.memory import set_admin_token, revoke_admin_token
from app.domain.content.resolver import resolve_content_source
from app.domain.content.loader import load_tracks_config, get_track_config
import app.infrastructure.database.engine as db_engine
from app.infrastructure.database.engine import switch_database, build_engine
from app.infrastructure.database.migrator import migrate_sqlite_to_postgres

logger = logging.getLogger("organicbattles.admin")
router = APIRouter(tags=["Admin Management"])

USERNAME_REGEX = r"^[A-Za-z0-9_.-]{3,24}$"


class AdminLoginRequest(BaseModel):
    username: str
    password: str
    client_type: Optional[str] = None


class AdminUserConfigRequest(BaseModel):
    content_source: Optional[str] = None


class AdminUserCredentialsRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


class SessionResetRequest(BaseModel):
    chapter: Optional[int] = None
    boss_index: Optional[int] = None


class DatabaseSwitchRequest(BaseModel):
    dialect: str
    connection_url: Optional[str] = None
    migrate_data: bool = False


class FolderSwitchRequest(BaseModel):
    data_folder: str
    boss_folder: Optional[str] = None
    track_id: Optional[str] = None  # None for default/all, or specific track


class LoggingConfigRequest(BaseModel):
    levels: Dict[str, str]  # e.g. {"root": "INFO", "organicbattles.api": "DEBUG"}


class TrackUpdateRequest(BaseModel):
    title: Optional[str] = None
    detail: Optional[str] = None
    data_folder: Optional[str] = None
    boss_folder: Optional[str] = None
    questions: Optional[int] = None
    chapters: Optional[int] = None
    accent: Optional[str] = None


@router.post("/admin/login")
@limiter.limit("10/minute")
def admin_login(
    request: Request,
    body: AdminLoginRequest,
    response: Response,
    db: DBSession = Depends(get_admin_db),
):
    from app.infrastructure.database.admin_repo import AdminRepository
    admin_repo = AdminRepository(db)
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    admin_user = admin_repo.verify_admin_credentials(body.username, body.password)
    if not admin_user:
        logger.warning("[ADMIN_AUTH_FAIL] Admin authentication failed for username '%s' from IP %s", body.username, client_ip)
        raise HTTPException(401, "Incorrect admin username or password")

    token = secrets.token_urlsafe(40)
    thash = code_hash(token)
    ttl_seconds = settings.admin_session_ttl_hours * 3600

    admin_repo.create_session(
        admin_user_id=admin_user.id,
        token_hash=thash,
        ttl_seconds=ttl_seconds,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    set_admin_token(thash, ttl_seconds)

    admin_repo.log_action(
        admin_user_id=admin_user.id,
        admin_username=admin_user.username,
        action="LOGIN",
        target_type="auth",
        target_id=admin_user.id,
        details={"ip": client_ip, "user_agent": user_agent},
        ip_address=client_ip,
    )

    response.set_cookie(
        "admin_token",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=ttl_seconds,
    )
    logger.info("[ADMIN_AUTH] Admin user '%s' (ID: %s) authenticated successfully from IP %s", admin_user.username, admin_user.id, client_ip)

    is_browser = (
        body.client_type == "browser"
        or request.headers.get("x-client-type") == "browser"
        or request.headers.get("sec-fetch-dest") is not None
        or request.headers.get("sec-fetch-mode") is not None
        or "Mozilla" in user_agent
    )

    resp = {
        "username": admin_user.username,
        "admin_id": admin_user.id,
        "status": "ok",
    }
    if not is_browser:
        resp["token"] = token
    return resp



@router.get("/admin/status")
def admin_status(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_admin_db)):
    total_users = db.query(User).count()
    total_sessions = db.query(GameSession).count()
    return {
        "status": "ok",
        "admin_user": admin_info["username"],
        "total_users": total_users,
        "total_sessions": total_sessions,
    }


@router.get("/admin/users")
def admin_get_users(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_admin_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    sessions = {s.user_id: s for s in db.query(GameSession).all()}
    result = []
    for u in users:
        sess = sessions.get(u.id)
        effective = resolve_content_source(u.content_source if u.content_source else (sess.content_source if sess else None))
        track_id = effective.replace("track:", "")
        track_cfg = get_track_config(settings.root_dir, track_id)
        track_name = track_cfg.get("title", track_id.title()) if track_cfg else track_id.title()
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "verified": bool(u.verified),
            "content_source": u.content_source,
            "track_id": track_id,
            "track_name": track_name,
            "effective_mode": effective,
            "chapter": sess.chapter if sess else 1,
            "boss_index": sess.boss_index if sess else 0,
            "player_hp": sess.player_hp if sess else 150,
            "session_id": sess.id if sess else None,
            "created_at": u.created_at,
        })
    return {"users": result, "total": len(result)}


@router.post("/admin/users/{user_id}/verify")
def admin_toggle_user_verification(
    user_id: str,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
):
    """Toggle verified status for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.verified = 0 if user.verified else 1
    db.commit()
    db.refresh(user)

    admin_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
    admin_username = admin_info.get("username", "admin")
    logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) toggled verification for user '%s' (ID: %s) to %s", admin_username, admin_id, user.username, user.id, user.verified)
    from app.infrastructure.database.admin_repo import AdminRepository
    AdminRepository(db).log_action(
        admin_user_id=admin_id,
        admin_username=admin_username,
        action="TOGGLE_VERIFICATION",
        target_type="user",
        target_id=user.id,
        details={"username": user.username, "verified": bool(user.verified)},
    )

    return {
        "status": "ok",
        "user_id": user.id,
        "username": user.username,
        "verified": bool(user.verified),
        "message": f"User '{user.username}' is now {'verified' if user.verified else 'unverified'}",
    }


@router.post("/admin/users/{user_id}/config")
def admin_update_user_config(
    user_id: str,
    body: AdminUserConfigRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    if body.content_source is not None:
        target = body.content_source.strip().lower() if body.content_source else None
        if target and target not in ("app", "json") and not target.startswith("track:"):
            raise HTTPException(400, "content_source must be 'app', 'json', or a valid track ID")
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

    admin_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
    admin_username = admin_info.get("username", "admin")
    logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) updated config for user '%s' (ID: %s) to %s", admin_username, admin_id, user.username, user.id, user.content_source)

    effective = resolve_content_source(user.content_source)
    track_id = effective.replace("track:", "")
    track_cfg = get_track_config(settings.root_dir, track_id)
    track_name = track_cfg.get("title", track_id.title()) if track_cfg else track_id.title()
    return {
        "status": "ok",
        "user_id": user.id,
        "username": user.username,
        "content_source": user.content_source,
        "track_id": track_id,
        "track_name": track_name,
        "effective_mode": effective,
    }


@router.post("/admin/users/{user_id}/credentials")
def admin_update_user_credentials(
    user_id: str,
    body: AdminUserCredentialsRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    updated_fields = []

    # 1. Update Username if requested
    if body.username is not None and body.username.strip():
        new_username = body.username.strip()
        if not re.match(USERNAME_REGEX, new_username):
            raise HTTPException(400, "Username must be between 3 and 24 characters and only contain letters, numbers, underscores, dots, or hyphens.")
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

    admin_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
    admin_username = admin_info.get("username", "admin")
    logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) updated credentials for user '%s' (ID: %s): %s", admin_username, admin_id, user.username, user.id, updated_fields)
    from app.infrastructure.database.admin_repo import AdminRepository
    AdminRepository(db).log_action(
        admin_user_id=admin_id,
        admin_username=admin_username,
        action="UPDATE_USER_CREDENTIALS",
        target_type="user",
        target_id=user.id,
        details={"username": user.username, "updated_fields": updated_fields},
    )


    return {
        "status": "ok",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "updated": updated_fields,
        "message": f"Successfully updated {', '.join(updated_fields)} for {user.email}",
    }



@router.get("/admin/sessions")
def admin_get_sessions(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_admin_db)):
    game_sessions = db.query(GameSession).order_by(GameSession.updated_at.desc()).all()
    users = {u.id: u for u in db.query(User).all()}
    result = []
    for s in game_sessions:
        u = users.get(s.user_id)
        effective = resolve_content_source(u.content_source if u else s.content_source)
        track_id = effective.replace("track:", "")
        track_cfg = get_track_config(settings.root_dir, track_id)
        track_name = track_cfg.get("title", track_id.title()) if track_cfg else track_id.title()
        bundle = get_content_bundle(effective)
        chapters = bundle.chapters
        ch_idx = max(0, min(s.chapter - 1, len(chapters) - 1))
        ch_data = chapters[ch_idx]
        bosses = ch_data["bosses"]
        b_idx = max(0, min(s.boss_index, len(bosses) - 1))
        boss = bosses[b_idx]
        try:
            completed_list = json.loads(s.completed_json) if s.completed_json else []
        except Exception:
            completed_list = []

        try:
            log_list = json.loads(s.log_json) if s.log_json else []
        except Exception:
            log_list = []

        try:
            cooldowns_dict = json.loads(s.cooldowns_json) if s.cooldowns_json else {}
        except Exception:
            cooldowns_dict = {}

        result.append({
            "session_id": s.id,
            "user_id": s.user_id,
            "username": u.username if u else "Unknown User",
            "email": u.email if u else "Unknown",
            "content_source": s.content_source,
            "track_id": track_id,
            "track_name": track_name,
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
            "turn_id": s.turn_id,
            "version": s.version,
            "has_active_question": bool(s.active_question_json),
            "active_spell": s.active_spell,
            "log": log_list,
            "cooldowns": cooldowns_dict,
            "updated_at": s.updated_at,
            "available_chapters": [{"id": ch["id"], "name": ch["name"]} for ch in chapters],
        })
    return {"sessions": result, "total": len(result)}


@router.post("/admin/sessions/{session_id}/reset")
def admin_reset_session(
    session_id: str,
    body: SessionResetRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
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

    admin_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
    admin_username = admin_info.get("username", "admin")
    logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) reset session '%s' to Chapter %d (%s)", admin_username, admin_id, session_id, target_chapter, first_boss[1])
    from app.infrastructure.database.admin_repo import AdminRepository
    AdminRepository(db).log_action(
        admin_user_id=admin_id,
        admin_username=admin_username,
        action="RESET_SESSION",
        target_type="session",
        target_id=session_id,
        details={"chapter": target_chapter, "boss": first_boss[1], "user_id": game_session.user_id},
    )

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
    db: DBSession = Depends(get_admin_db),
):
    game_session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not game_session:
        raise HTTPException(404, "Session not found")

    user = db.query(User).filter(User.id == game_session.user_id).first()
    if user:
        user.progress_json = None

    admin_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
    admin_username = admin_info.get("username", "admin")
    logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) deleted session '%s'", admin_username, admin_id, session_id)
    from app.infrastructure.database.admin_repo import AdminRepository
    AdminRepository(db).log_action(
        admin_user_id=admin_id,
        admin_username=admin_username,
        action="DELETE_SESSION",
        target_type="session",
        target_id=session_id,
        details={"user_id": game_session.user_id},
    )

    db.delete(game_session)
    db.commit()

    return {"status": "ok", "message": "Session deleted successfully", "session_id": session_id}


@router.get("/admin/system/config")
def get_system_config(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_admin_db)):
    """Return active database dialect and all track folder mappings from database."""
    cur_url = db_engine.current_db_url
    dialect = "postgresql" if "postgresql" in cur_url else "sqlite"
    display_url = cur_url.split("@")[-1] if "@" in cur_url else cur_url
    if "@" in cur_url:
        display_url = f"postgresql://***:***@{display_url}"

    from app.infrastructure.database.tracks_repo import TracksRepository
    from app.infrastructure.cache.shared_cache import shared_track_cache
    from app.infrastructure.database.engine import get_pool_config_summary
    from app.observability.metrics import metrics_registry
    tracks_cfg = TracksRepository(db).get_tracks_config()

    max_cluster_conns = (
        (settings.db_pool_size or 5) + (settings.db_max_overflow or 10)
    ) * (settings.web_concurrency * settings.app_replicas)

    runtime_env = {
        "environment": settings.environment,
        "debug": os.getenv("DEBUG", "false").lower() in ("1", "true", "yes"),
        "cookie_secure": settings.cookie_secure,
        "allow_json_fallback": settings.allow_json_fallback,
        "loaded_env_file": settings.loaded_env_file_name or "in-memory defaults",
        "web_concurrency": settings.web_concurrency,
        "app_replicas": settings.app_replicas,
        "max_cluster_connections": max_cluster_conns,
        "db_max_connections_limit": settings.db_max_connections_limit,
    }

    return {
        "active_database": {
            "dialect": dialect,
            "url": display_url,
        },
        "database_pool": get_pool_config_summary(),
        "runtime_environment": runtime_env,
        "tracks": tracks_cfg.get("tracks", []),
        "curricula": tracks_cfg.get("curricula", []),
        "track_cache": shared_track_cache.stats(),
        "health": shared_track_cache.get_health_metrics(),
        "metrics": metrics_registry.get_system_metrics(),
    }


@router.get("/admin/system/metrics")
def get_system_metrics(admin_info: dict = Depends(auth_admin)):
    """Return all 9 dimensions of observability and performance metrics."""
    from app.observability.metrics import metrics_registry
    return metrics_registry.get_system_metrics()


@router.get("/admin/system/health")
def get_system_health(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_admin_db)):
    """Comprehensive health and readiness diagnostic endpoint for the Admin Health Tab."""
    import time
    import shutil
    import platform
    from sqlalchemy import text
    from app.infrastructure.database.engine import get_pool_config_summary
    from app.infrastructure.cache.shared_cache import shared_track_cache

    # 1. Measure DB Ping
    ping_start = time.perf_counter()
    db_connected = False
    db_error = None
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception as e:
        db_error = str(e)
    ping_ms = round((time.perf_counter() - ping_start) * 1000, 2)

    # 2. Probe status
    metrics = shared_track_cache.get_health_metrics()
    has_cache = shared_track_cache.has_any_validated_cache()

    liveness_status = "alive"
    if db_connected:
        readiness_status = "ready" if metrics.get("overall_fallback", "none") == "none" else "degraded"
    elif has_cache:
        readiness_status = "degraded"
    else:
        readiness_status = "unavailable"

    # 3. Connection pool summary
    pool_summary = get_pool_config_summary()

    # 4. Dialect and masked URL
    cur_url = db_engine.current_db_url
    dialect = "postgresql" if "postgresql" in cur_url else "sqlite"
    display_url = cur_url.split("@")[-1] if "@" in cur_url else cur_url
    if "@" in cur_url:
        display_url = f"postgresql://***:***@{display_url}"

    # 5. Host & resource stats
    disk_path = settings.root_dir
    disk_usage = shutil.disk_usage(disk_path)
    free_disk_gb = round(disk_usage.free / (1024 ** 3), 2)
    total_disk_gb = round(disk_usage.total / (1024 ** 3), 2)

    # Memory usage RSS
    rss_mb = 0
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if platform.system() == "Darwin":
            rss_mb = round(usage / (1024 * 1024), 1)
        else:
            rss_mb = round(usage / 1024, 1)
    except Exception:
        pass

    # 6. Overall verdict
    if db_connected and readiness_status == "ready":
        verdict = "HEALTHY"
    elif db_connected and readiness_status == "degraded":
        verdict = "DEGRADED"
    else:
        verdict = "CRITICAL"

    return {
        "verdict": verdict,
        "timestamp": int(time.time()),
        "probes": {
            "liveness": liveness_status,
            "readiness": readiness_status,
        },
        "database": {
            "connected": db_connected,
            "dialect": dialect,
            "display_url": display_url,
            "ping_ms": ping_ms,
            "error": db_error,
        },
        "pool": pool_summary,
        "cache": {
            "stats": shared_track_cache.stats(),
            "health_metrics": metrics,
            "degraded_mode": metrics.get("degraded_mode", False),
            "fallback_status": metrics.get("overall_fallback", "none"),
        },
        "system": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "free_disk_gb": free_disk_gb,
            "total_disk_gb": total_disk_gb,
            "rss_mb": rss_mb,
            "environment": settings.environment,
            "web_concurrency": settings.web_concurrency,
            "app_replicas": settings.app_replicas,
        },
    }


def _get_default_pg_url() -> str:
    """Retrieve the configured PostgreSQL connection URL from environment, env file, or settings."""
    env_url = os.getenv("DATABASE_URL_ADMIN") or os.getenv("DATABASE_URL")
    if env_url and "postgresql" in env_url:
        return env_url

    candidates = [
        settings.root_dir / "local.env",
        settings.root_dir / "env",
        settings.root_dir / ".env",
        settings.root_dir / "prod.env",
    ]
    for env_file in candidates:
        if env_file.exists():
            try:
                from dotenv import dotenv_values
                vals = dotenv_values(env_file)
                pg = vals.get("DATABASE_URL_ADMIN") or vals.get("DATABASE_URL")
                if pg and "postgresql" in pg:
                    return pg
            except Exception:
                pass

    if "postgresql" in settings.database_url:
        return settings.database_url
    if "postgresql" in getattr(settings, "database_url_admin", ""):
        return settings.database_url_admin

    return ""


@router.post("/admin/system/database")
def admin_switch_database(
    body: DatabaseSwitchRequest,
    admin_info: dict = Depends(auth_admin),
):
    """Switch active database between SQLite and PostgreSQL with optional live data migration."""
    dialect_clean = body.dialect.strip().lower()
    raw_url = (body.connection_url or "").strip()

    if dialect_clean == "sqlite":
        if not raw_url or raw_url.lower() == "sqlite":
            target_url = f"sqlite:///{settings.root_dir / 'organic_battles.sqlite3'}"
        else:
            target_url = raw_url
    elif dialect_clean == "postgresql":
        default_pg = _get_default_pg_url()
        if not raw_url or "***:***" in raw_url or raw_url.lower() == "postgresql":
            target_url = default_pg
        elif "localhost" in raw_url and "localhost" not in default_pg:
            target_url = default_pg
        else:
            target_url = raw_url
    else:
        raise HTTPException(400, "Unsupported dialect. Choose 'sqlite' or 'postgresql'.")

    try:
        old_url = db_engine.current_db_url
        migration_stats = None
        if body.migrate_data and old_url != target_url:
            source_engine = build_engine(old_url)
            target_engine = build_engine(target_url)
            db_engine._migrate_legacy_table_names(source_engine)
            try:
                from app.infrastructure.database.alembic_runner import run_alembic_migrations
                run_alembic_migrations(target_engine=target_engine)
            except Exception:
                Base.metadata.create_all(bind=target_engine)
            migration_stats = migrate_sqlite_to_postgres(source_engine, target_engine)

        result = switch_database(target_url)
        if migration_stats is not None:
            result["migration"] = migration_stats
        admin_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
        admin_username = admin_info.get("username", "admin")
        logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) switched database dialect to '%s'", admin_username, admin_id, dialect_clean)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Database switch failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=f"Database switch failed: {exc}")


@router.post("/admin/system/folders")
def admin_switch_folders(
    body: FolderSwitchRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
):
    """Update data_folder and boss_folder paths in PostgreSQL database and tracks_config.json."""
    from app.infrastructure.database.tracks_repo import TracksRepository
    repo = TracksRepository(db)
    updated_in_db = repo.update_track_folders(body.track_id, body.data_folder, body.boss_folder)

    # Also synchronize to tracks_config.json if it exists
    config_path = settings.root_dir / "data" / "tracks_config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            json_updated = False
            for t in cfg.get("tracks", []):
                if not body.track_id or t.get("id") == body.track_id:
                    t["data_folder"] = body.data_folder
                    if body.boss_folder:
                        t["boss_folder"] = body.boss_folder
                    json_updated = True
            if json_updated:
                config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to sync json file on folder switch: %s", e)

    if not updated_in_db and body.track_id:
        raise HTTPException(404, f"Track '{body.track_id}' not found")

    # Invalidate in-memory cache so new paths are loaded immediately
    from app.api.deps import TRACK_BUNDLES
    TRACK_BUNDLES.clear()

    admin_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
    admin_username = admin_info.get("username", "admin")
    logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) updated folders for track '%s' (data: %s, boss: %s)", admin_username, admin_id, body.track_id, body.data_folder, body.boss_folder)
    from app.infrastructure.database.admin_repo import AdminRepository
    AdminRepository(db).log_action(
        admin_user_id=admin_id,
        admin_username=admin_username,
        action="SWITCH_FOLDERS",
        target_type="storage",
        details={"track_id": body.track_id, "data_folder": body.data_folder, "boss_folder": body.boss_folder},
    )


    return {"status": "ok", "message": "Folder locations updated in database and bundle cache refreshed"}


@router.get("/admin/tracks")
def admin_get_tracks(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_admin_db)):
    """Retrieve all tracks with relational properties from database."""
    from app.infrastructure.database.tracks_repo import TracksRepository
    repo = TracksRepository(db)
    return {"tracks": repo.get_tracks_config()["tracks"]}


@router.put("/admin/tracks/{track_id}")
def admin_update_track(
    track_id: str,
    body: TrackUpdateRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
):
    """Update specific track metadata in PostgreSQL database."""
    from app.infrastructure.database.tracks_repo import TracksRepository
    repo = TracksRepository(db)
    track = repo.get_track(track_id)
    if not track:
        raise HTTPException(404, f"Track '{track_id}' not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "No fields provided to update")

    for k, v in updates.items():
        if v is not None:
            setattr(track, k, v)
    db.commit()
    db.refresh(track)

    from app.api.deps import TRACK_BUNDLES
    TRACK_BUNDLES.clear()

    return {"status": "ok", "message": f"Track '{track_id}' updated successfully", "track": repo.get_track_dict(track_id)}


@router.get("/admin/curricula")
def admin_get_curricula(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_admin_db)):
    """Retrieve all curricula registered in database."""
    from app.infrastructure.database.tracks_repo import TracksRepository
    repo = TracksRepository(db)
    return {"curricula": repo.get_tracks_config()["curricula"]}



class LoggingConfigRequest(BaseModel):
    levels: Dict[str, str] = Field(default_factory=dict)
    log_file_path: Optional[str] = None


@router.get("/admin/system/logging")
def admin_get_logging_config(admin_info: dict = Depends(auth_admin)):
    """Retrieve active logging configuration and log file information."""
    from app.observability.logging import get_logging_config
    return get_logging_config()


@router.post("/admin/system/logging")
def admin_update_logging_config(
    body: LoggingConfigRequest,
    admin_info: dict = Depends(auth_admin),
):
    """Update active logging levels dynamically and persist to logging.properties."""
    from app.observability.logging import update_logging_config
    cfg = update_logging_config(levels=body.levels, log_file_path=body.log_file_path)
    admin_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
    admin_username = admin_info.get("username", "admin")
    logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) updated logging configuration: %s", admin_username, admin_id, body.levels)
    return {
        "status": "ok",
        "message": "Logging configuration updated and persisted",
        "config": cfg,
    }


@router.get("/admin/system/logging/tail")
def admin_tail_logs(
    lines: int = 100,
    log_type: str = Query("admin", description="'admin' for logs/admin.log or 'player' for logs/organic_battles.log"),
    admin_info: dict = Depends(auth_admin),
):
    """Retrieve recent log lines from active log file for dashboard console."""
    from app.observability.logging import tail_log_file, DEFAULT_LOG_FILE, ADMIN_LOG_FILE
    target_file = ADMIN_LOG_FILE if log_type == "admin" else DEFAULT_LOG_FILE
    log_lines = tail_log_file(lines=min(max(1, lines), 1000), log_type=log_type)
    return {
        "log_file": str(target_file),
        "log_type": log_type,
        "lines_count": len(log_lines),
        "lines": log_lines,
    }


@router.post("/admin/system/cache/warm")
def admin_warm_cache(
    tracks: Optional[str] = None,
    admin_info: dict = Depends(auth_admin),
):
    """Warm cache for specified tracks or configured popular tracks."""
    from app.infrastructure.cache.shared_cache import shared_track_cache
    admin_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
    admin_username = admin_info.get("username", "admin")
    logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) triggered cache warming for tracks: %s", admin_username, admin_id, tracks)
    track_ids = [t.strip() for t in tracks.split(",") if t.strip()] if tracks else None
    results = shared_track_cache.warm_tracks(settings.root_dir, track_ids)
    return {"status": "ok", "results": results, "stats": shared_track_cache.stats()}


@router.get("/admin/tracks/{track_id}/releases")
def admin_get_track_releases(
    track_id: str,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
):
    """Retrieve versioned content releases for a track."""
    from app.infrastructure.database.releases_repo import ReleasesRepository
    repo = ReleasesRepository(db)
    releases = repo.get_track_releases(track_id)
    return {
        "track_id": track_id,
        "releases": [
            {
                "id": r.id,
                "version": r.version,
                "status": r.status,
                "checksum": r.checksum,
                "created_at": r.created_at,
                "published_at": r.published_at,
            }
            for r in releases
        ],
    }


@router.post("/admin/tracks/{track_id}/releases/{version}/rollback")
def admin_rollback_track_release(
    track_id: str,
    version: int,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
):
    """Roll back active track questions to a previous release version."""
    from app.infrastructure.database.releases_repo import ReleasesRepository
    from app.infrastructure.cache.shared_cache import shared_track_cache
    repo = ReleasesRepository(db)
    try:
        active = repo.rollback_to_release(track_id, version)
        shared_track_cache.invalidate_track(track_id)

        admin_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
        admin_username = admin_info.get("username", "admin")
        logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) rolled back track '%s' to release %s (v%d)", admin_username, admin_id, track_id, active.id, version)
        from app.infrastructure.database.admin_repo import AdminRepository
        AdminRepository(db).log_action(
            admin_user_id=admin_id,
            admin_username=admin_username,
            action="ROLLBACK_RELEASE",
            target_type="release",
            target_id=active.id,
            details={"track_id": track_id, "version": version, "release_id": active.id},
        )

        return {
            "status": "ok",
            "message": f"Track '{track_id}' rolled back to release {active.id} (v{version})",
            "active_release": active.id,
            "version": active.version,
        }
    except ValueError as exc:
        raise HTTPException(404, str(exc))


class AdminCreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=24, pattern=USERNAME_REGEX)
    password: str
    role: Optional[str] = "admin"


@router.post("/admin/manage/users")
def admin_create_admin_user(
    body: AdminCreateUserRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_admin_db),
):
    """Create a new administrator account (admin-only workflow)."""
    from app.infrastructure.database.admin_repo import AdminRepository
    from app.infrastructure.database.repositories import UserRepository
    admin_repo = AdminRepository(db)
    user_repo = UserRepository(db)

    clean_uname = body.username.strip().lower()
    if not re.match(USERNAME_REGEX, clean_uname):
        raise HTTPException(400, "Admin username must be between 3 and 24 characters and only contain letters, numbers, underscores, dots, or hyphens.")
    if len(body.password) < 5:
        raise HTTPException(400, "Password must be at least 5 characters")

    if admin_repo.get_by_username(clean_uname):
        raise HTTPException(409, f"Admin user '{clean_uname}' already exists")
    if user_repo.get_by_username(clean_uname):
        raise HTTPException(409, f"Username '{clean_uname}' is already in use by a player account")

    pwd_hash = hash_password(body.password)
    new_admin = admin_repo.create_admin(username=clean_uname, password_hash=pwd_hash, role=body.role or "admin")

    creator_id = admin_info.get("id") or admin_info.get("admin_id") or "unknown"
    creator_uname = admin_info.get("username", "admin")
    logger.info("[ADMIN_ACTION] Admin '%s' (ID: %s) created new admin user '%s' (ID: %s, role: %s)", creator_uname, creator_id, new_admin.username, new_admin.id, new_admin.role)
    admin_repo.log_action(
        admin_user_id=creator_id,
        admin_username=creator_uname,
        action="CREATE_ADMIN_USER",
        target_type="admin_user",
        target_id=new_admin.id,
        details={"username": new_admin.username, "role": new_admin.role},
    )

    return {
        "status": "ok",
        "admin_id": new_admin.id,
        "username": new_admin.username,
        "role": new_admin.role,
        "message": f"Admin user '{new_admin.username}' created successfully",
    }


@router.post("/admin/logout")
def admin_logout(
    response: Response,
    authorization: Optional[str] = Header(default=None),
    admin_token: Optional[str] = Cookie(default=None),
    db: DBSession = Depends(get_admin_db),
):
    raw = admin_token or (authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None)
    if raw:
        thash = code_hash(raw)
        from app.infrastructure.database.admin_repo import AdminRepository
        admin_repo = AdminRepository(db)
        admin_sess = admin_repo.get_session(thash)
        if admin_sess:
            admin_user = admin_repo.get_by_id(admin_sess.admin_user_id)
            uname = admin_user.username if admin_user else "admin"
            logger.info("[ADMIN_ACTION] Admin user '%s' (ID: %s) logged out", uname, admin_sess.admin_user_id)
            admin_repo.log_action(
                admin_user_id=admin_sess.admin_user_id,
                admin_username=uname,
                action="LOGOUT",
                target_type="auth",
                target_id=admin_sess.admin_user_id,
            )
            admin_repo.delete_session(thash)
        revoke_admin_token(thash)
    response.delete_cookie("admin_token")
    return {"status": "ok"}

