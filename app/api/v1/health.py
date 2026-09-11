from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession
from app.api.deps import get_db
from app.infrastructure.cache.shared_cache import shared_track_cache

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health/live")
@router.get("/healthz")
def health_liveness():
    """Liveness probe."""
    return {"status": "alive"}


@router.get("/health/ready")
@router.get("/readyz")
def health_readiness(response: Response, db: DBSession = Depends(get_db)):
    """
    Readiness probe:
    - If database is healthy: returns 200 OK with status: ready (or degraded if serving fallbacks).
    - If database is unavailable but validated cache exists: returns 200 OK with status: degraded.
    - If database is unavailable and no validated cache exists: returns 503 Service Unavailable with status: unavailable.
    """
    db_healthy = False
    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        db_healthy = False

    metrics = shared_track_cache.get_health_metrics()
    has_cache = shared_track_cache.has_any_validated_cache()

    if db_healthy:
        response.status_code = 200
        return {
            "status": "ready",
            "database": "available",
            "fallback_status": metrics.get("overall_fallback", "none"),
            "content_sources": metrics.get("content_sources", {}),
            "content_versions": metrics.get("content_versions", {}),
            "metrics": metrics,
        }

    # Database is unavailable
    shared_track_cache.record_content_status(
        track_id="system",
        source="cache" if has_cache else "none",
        version="none",
        fallback_status="cache_degraded" if has_cache else "unavailable",
        database_available=False,
    )

    if has_cache:
        response.status_code = 200
        return {
            "status": "degraded",
            "database": "unavailable",
            "reason": "PostgreSQL unavailable; serving validated cache",
            "fallback_status": "cache_degraded",
            "content_sources": metrics.get("content_sources", {}),
            "content_versions": metrics.get("content_versions", {}),
            "metrics": shared_track_cache.get_health_metrics(),
        }

    response.status_code = 503
    return {
        "status": "unavailable",
        "database": "unavailable",
        "reason": "PostgreSQL unavailable and no validated cache exists",
        "fallback_status": "unavailable",
        "metrics": shared_track_cache.get_health_metrics(),
    }
