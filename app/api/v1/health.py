from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession
from app.api.deps import get_db

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health/live")
@router.get("/healthz")
def health_liveness():
    """Liveness probe."""
    return {"status": "alive"}


@router.get("/health/ready")
@router.get("/readyz")
def health_readiness(db: DBSession = Depends(get_db)):
    """Readiness probe: validates database connectivity."""
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
