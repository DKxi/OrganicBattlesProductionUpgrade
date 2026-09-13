from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.settings import settings
from app.observability.logging import setup_logging
from app.observability.middleware import SecurityAndObservabilityMiddleware
from app.api.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.api.deps import limiter
from app.api.v1.router import api_v1_router


def create_app() -> FastAPI:
    """FastAPI application factory."""
    setup_logging()

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
    application.add_exception_handler(Exception, generic_exception_handler)

    # Observability & Security Middleware
    application.add_middleware(SecurityAndObservabilityMiddleware)

    # Mount API Routers (under both /api/v1 and /api for compatibility)
    application.include_router(api_v1_router, prefix="/api/v1")
    application.include_router(api_v1_router, prefix="/api")

    # Also register health probes at root level (/health/live, /health/ready, /healthz, /readyz)
    from app.api.v1 import health
    application.include_router(health.router)


    from app.domain.content.loader import (
        load_tracks_config,
        is_advanced_boss_image,
        is_default_boss_image,
        is_foundational_boss_image,
    )

    @application.get("/static/assets/bosses/{filename:path}")
    @application.get("/bosses/{filename:path}")
    def serve_boss_image(filename: str):
        """
        Dynamically serve boss images.
        1. If the image belongs to the Advanced Bosses catalog and Supabase S3 / Storage is active,
           redirects (307 Temporary Redirect) to Supabase Storage public CDN (Approach 1).
        2. If the image belongs to the Default Bosses catalog and Supabase S3 / Storage is active,
           redirects (307 Temporary Redirect) to Supabase Storage DefaultBosses public CDN.
        3. If the image belongs to the Foundational Bosses catalog and Supabase S3 / Storage is active,
           redirects (307 Temporary Redirect) to Supabase Storage FoundationalBosses public CDN.
        4. Configured track boss folders from tracks_config.json (local files).
        5. Fallback search through data/tracks/default/bosses, bosses/, data/bosses, static/assets/bosses
        6. Final fallback to static/assets/bosses/boss-placeholder.svg
        """
        raw_name = Path(filename).name

        # Security: Only allow image extensions
        allowed_exts = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
        if Path(raw_name).suffix.lower() not in allowed_exts:
            raise HTTPException(404, f"Invalid image format for '{raw_name}'")

        # Redirect to Supabase Public Storage CDN for Advanced Bosses
        if settings.use_supabase_boss_storage and is_advanced_boss_image(raw_name, settings.root_dir):
            public_url = f"{settings.supabase_public_storage_base_url}/{raw_name}"
            return RedirectResponse(
                url=public_url,
                status_code=307,
                headers={"Cache-Control": "public, max-age=86400"}
            )

        # Redirect to Supabase Public Storage CDN for Default Bosses
        if settings.use_supabase_boss_storage and is_default_boss_image(raw_name, settings.root_dir):
            public_url = f"{settings.supabase_default_bosses_base_url}/{raw_name}"
            return RedirectResponse(
                url=public_url,
                status_code=307,
                headers={"Cache-Control": "public, max-age=86400"}
            )

        # Redirect to Supabase Public Storage CDN for Foundational Bosses
        if settings.use_supabase_boss_storage and is_foundational_boss_image(raw_name, settings.root_dir):
            public_url = f"{settings.supabase_foundational_bosses_base_url}/{raw_name}"
            return RedirectResponse(
                url=public_url,
                status_code=307,
                headers={"Cache-Control": "public, max-age=86400"}
            )

        config = load_tracks_config(settings.root_dir)

        # 1. Configured track boss folders (local directories)
        for t in config.get("tracks", []):
            bf = t.get("boss_folder")
            if bf and not (bf.startswith("http://") or bf.startswith("https://") or bf.startswith("s3://")):
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

        # 4. Fallback to data/bosses
        data_bosses = settings.root_dir / "data" / "bosses" / raw_name
        if data_bosses.is_file():
            return FileResponse(data_bosses)

        # 5. Fallback to data/
        data_file = settings.root_dir / "data" / raw_name
        if data_file.is_file():
            return FileResponse(data_file)

        # 6. Fallback to static/assets/bosses
        static_boss = settings.root_dir / "static" / "assets" / "bosses" / raw_name
        if static_boss.is_file():
            return FileResponse(static_boss)

        # 7. Fallback to SVG placeholder
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
