import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.settings import settings

logger = logging.getLogger("organicbattles.api")


class SecurityAndObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        client_ip = request.client.host if request.client else "unknown"

        start_time = time.time()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(
                "HTTP %s %s ERROR [req:%s] [ip:%s] (%0.2fms): %s",
                request.method,
                request.url.path,
                request_id,
                client_ip,
                process_time * 1000,
                exc,
                exc_info=True,
            )
            raise

        process_time = time.time() - start_time

        # Observability headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        # Structured request logging
        status = response.status_code
        is_health = request.url.path.startswith("/health") or request.url.path in ("/readyz", "/healthz")
        
        log_msg = (
            f"HTTP {request.method} {request.url.path} -> {status} "
            f"({process_time * 1000:.2f}ms) [req:{request_id}] [ip:{client_ip}]"
        )
        if status >= 500:
            logger.error(log_msg)
        elif status >= 400:
            logger.warning(log_msg)
        elif is_health:
            logger.debug(log_msg)
        else:
            logger.info(log_msg)

        # Security hardening headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:;"
        )

        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

