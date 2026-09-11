import os
import json
import time
import secrets
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, Response, Depends, HTTPException, Header, Cookie
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.settings import settings
from app.api.deps import get_db, auth_admin, limiter, get_content_bundle
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


class AdminLoginRequest(BaseModel):
    username: str
    password: str


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
def admin_login(request: Request, body: AdminLoginRequest, response: Response):
    if body.username != settings.admin_username or body.password != settings.admin_password:
        logger.warning("Admin authentication failed for username: %s", body.username)
        raise HTTPException(401, "Incorrect admin username or password")

    token = secrets.token_urlsafe(40)
    thash = code_hash(token)
    ttl_seconds = settings.admin_session_ttl_hours * 3600
    set_admin_token(thash, ttl_seconds)

    response.set_cookie(
        "admin_token",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=ttl_seconds,
    )
    logger.info("Admin user '%s' authenticated successfully", body.username)
    return {"token": token, "username": settings.admin_username, "status": "ok"}


@router.get("/admin/status")
def admin_status(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_db)):
    total_users = db.query(User).count()
    total_sessions = db.query(GameSession).count()
    return {
        "status": "ok",
        "admin_user": admin_info["username"],
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
            completed_list = json.loads(s.completed_json)
        except Exception:
            completed_list = []

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


@router.get("/admin/system/config")
def get_system_config(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_db)):
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

    return {
        "active_database": {
            "dialect": dialect,
            "url": display_url,
        },
        "database_pool": get_pool_config_summary(),
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


def _get_default_pg_url() -> str:
    """Retrieve the configured PostgreSQL connection URL from environment, env file, or settings."""
    env_url = os.getenv("DATABASE_URL")
    if env_url and "postgresql" in env_url:
        return env_url

    env_file = settings.root_dir / "env" if (settings.root_dir / "env").exists() else settings.root_dir / ".env"
    if env_file.exists():
        try:
            from dotenv import dotenv_values
            vals = dotenv_values(env_file)
            pg = vals.get("DATABASE_URL")
            if pg and "postgresql" in pg:
                return pg
        except Exception:
            pass

    if "postgresql" in settings.database_url:
        return settings.database_url

    return "postgresql+psycopg2://postgres.aamwrwbsrmorllisdffc:[REDACTED-PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres"


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
            db_engine._migrate_legacy_table_names(target_engine)
            Base.metadata.create_all(bind=target_engine)
            migration_stats = migrate_sqlite_to_postgres(source_engine, target_engine)

        result = switch_database(target_url)
        if migration_stats is not None:
            result["migration"] = migration_stats
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
    db: DBSession = Depends(get_db),
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

    return {"status": "ok", "message": "Folder locations updated in database and bundle cache refreshed"}


@router.get("/admin/tracks")
def admin_get_tracks(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_db)):
    """Retrieve all tracks with relational properties from database."""
    from app.infrastructure.database.tracks_repo import TracksRepository
    repo = TracksRepository(db)
    return {"tracks": repo.get_tracks_config()["tracks"]}


@router.put("/admin/tracks/{track_id}")
def admin_update_track(
    track_id: str,
    body: TrackUpdateRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
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
def admin_get_curricula(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_db)):
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
    logger.info("Admin updated logging configuration: %s", body.levels)
    return {
        "status": "ok",
        "message": "Logging configuration updated and persisted",
        "config": cfg,
    }


@router.get("/admin/system/logging/tail")
def admin_tail_logs(
    lines: int = 100,
    admin_info: dict = Depends(auth_admin),
):
    """Retrieve recent log lines from active log file for dashboard console."""
    from app.observability.logging import tail_log_file, DEFAULT_LOG_FILE
    log_lines = tail_log_file(lines=min(max(1, lines), 1000))
    return {
        "log_file": str(DEFAULT_LOG_FILE),
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
    track_ids = [t.strip() for t in tracks.split(",") if t.strip()] if tracks else None
    results = shared_track_cache.warm_tracks(settings.root_dir, track_ids)
    return {"status": "ok", "results": results, "stats": shared_track_cache.stats()}


@router.get("/admin/tracks/{track_id}/releases")
def admin_get_track_releases(
    track_id: str,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db),
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
    db: DBSession = Depends(get_db),
):
    """Roll back active track questions to a previous release version."""
    from app.infrastructure.database.releases_repo import ReleasesRepository
    from app.infrastructure.cache.shared_cache import shared_track_cache
    repo = ReleasesRepository(db)
    try:
        active = repo.rollback_to_release(track_id, version)
        shared_track_cache.invalidate_track(track_id)
        return {
            "status": "ok",
            "message": f"Track '{track_id}' rolled back to release {active.id} (v{version})",
            "active_release": active.id,
            "version": active.version,
        }
    except ValueError as exc:
        raise HTTPException(404, str(exc))


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
