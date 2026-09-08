import logging
from typing import Optional, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger("organicbattles.api")


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "BAD_REQUEST", details: Any = None):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


def format_error_response(code: str, message: str, status_code: int, details: Any = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "status_code": status_code,
            "details": details,
        },
        "detail": message,  # Backward compatibility for legacy frontend/tests
    }


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "none")
    log_msg = f"AppException [{exc.code} {exc.status_code}] on {request.method} {request.url.path} [req:{req_id}]: {exc.message}"
    if exc.status_code >= 500:
        logger.error(log_msg, exc_info=True)
    else:
        logger.warning(log_msg)

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(exc.code, exc.message, exc.status_code, exc.details),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
    }
    code = code_map.get(exc.status_code, "ERROR")
    msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    req_id = getattr(request.state, "request_id", "none")

    log_msg = f"HTTPException [{code} {exc.status_code}] on {request.method} {request.url.path} [req:{req_id}]: {msg}"
    if exc.status_code >= 500:
        logger.error(log_msg, exc_info=True)
    else:
        logger.warning(log_msg)

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(code, msg, exc.status_code),
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = first_error.get("msg", "Invalid request payload")
    req_id = getattr(request.state, "request_id", "none")
    logger.warning("Validation error on %s %s [req:%s]: %s (details: %s)", request.method, request.url.path, req_id, msg, exc.errors())

    return JSONResponse(
        status_code=422,
        content=format_error_response("VALIDATION_ERROR", msg, 422, exc.errors()),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "none")
    logger.error("Unhandled exception on %s %s [req:%s]: %s", request.method, request.url.path, req_id, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content=format_error_response("INTERNAL_ERROR", str(exc) or "Internal server error", 500),
    )


