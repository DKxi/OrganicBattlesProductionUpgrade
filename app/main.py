from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.settings import settings
from app.infrastructure.database.engine import ensure_db_schema
from app.observability.logging import setup_logging
from app.observability.middleware import SecurityAndObservabilityMiddleware
from app.api.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.api.deps import limiter
from app.api.v1.router import api_v1_router


def create_app() -> FastAPI:
    """FastAPI application factory."""
    setup_logging()
    ensure_db_schema()

    application = FastAPI(
        title="Organic Battles V3",
        description="Organic Chemistry Boss Battle RPG Platform",
        version="3.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # Attach Rate Limiter state & handler
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Custom Exception Handlers for uniform error envelopes
    application.add_exception_handler(AppException, app_exception_handler)
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Attach Security & Observability Middleware
    application.add_middleware(SecurityAndObservabilityMiddleware)

    # Register API routes under both /api/v1 and /api (for frontend backward compatibility)
    application.include_router(api_v1_router, prefix="/api/v1")
    application.include_router(api_v1_router, prefix="/api")

    # Also register health probes at root level (/health/live, /health/ready, /healthz, /readyz)
    from app.api.v1 import health
    application.include_router(health.router)


    from app.domain.content.loader import load_tracks_config

    @application.get("/static/assets/bosses/{filename:path}")
    @application.get("/bosses/{filename:path}")
    def serve_boss_image(filename: str):
        """
        Dynamically serve boss images.
        Checks:
        1. Configured boss_folder directories from tracks_config.json (e.g. data/tracks/advanced/bosses)
        2. data/bosses/
        3. data/
        4. bosses/
        5. static/assets/bosses/
        6. Fallback to static/assets/bosses/boss-placeholder.svg
        """
        raw_name = Path(filename).name
        config = load_tracks_config(settings.root_dir)

        # 1. Configured track boss folders
        for t in config.get("tracks", []):
            bf = t.get("boss_folder")
            if bf:
                bf_path = Path(bf) if Path(bf).is_absolute() else settings.root_dir / bf
                target_file = bf_path / raw_name
                if target_file.is_file():
                    return FileResponse(target_file)

        # 2. Fallback to default track bosses folder data/tracks/default/bosses
        default_bosses = settings.root_dir / "data" / "tracks" / "default" / "bosses" / raw_name
        if default_bosses.is_file():
            return FileResponse(default_bosses)

        # 3. Fallback to bosses/ (folder outside data/)
        root_bosses = settings.root_dir / "bosses" / raw_name
        if root_bosses.is_file():
            return FileResponse(root_bosses)

        # 3. Fallback to data/bosses
        data_bosses = settings.root_dir / "data" / "bosses" / raw_name
        if data_bosses.is_file():
            return FileResponse(data_bosses)

        # 4. Fallback to data/
        data_file = settings.root_dir / "data" / raw_name
        if data_file.is_file():
            return FileResponse(data_file)

        # 5. Fallback to static/assets/bosses
        static_boss = settings.root_dir / "static" / "assets" / "bosses" / raw_name
        if static_boss.is_file():
            return FileResponse(static_boss)

        # 6. Fallback to SVG placeholder
        placeholder = settings.root_dir / "static" / "assets" / "bosses" / "boss-placeholder.svg"
        if placeholder.is_file():
            return FileResponse(placeholder, media_type="image/svg+xml")

        raise HTTPException(404, f"Boss image '{raw_name}' not found")

    # Static file mounts
    static_dir = settings.root_dir / "static"
    avatars_dir = settings.root_dir / "avatars"
    bosses_dir = settings.root_dir / "bosses"

    if static_dir.exists():
        application.mount("/static", StaticFiles(directory=static_dir), name="static")
    if avatars_dir.exists():
        application.mount("/avatars", StaticFiles(directory=avatars_dir), name="avatars")
    if bosses_dir.exists():
        application.mount("/bosses", StaticFiles(directory=bosses_dir), name="bosses")

    @application.get("/")
    def index():
        return FileResponse(settings.root_dir / "templates" / "index.html")

    @application.get("/favicon.ico")
    def favicon():
        fav = settings.root_dir / "static" / "favicon.ico"
        if fav.exists():
            return FileResponse(fav)
        svg = settings.root_dir / "static" / "assets" / "bosses" / "boss-placeholder.svg"
        if svg.exists():
            return FileResponse(svg)
        return FileResponse(settings.root_dir / "templates" / "index.html")

    return application


app = create_app()
