from typing import Optional, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


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
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(code, msg, exc.status_code),
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = first_error.get("msg", "Invalid request payload")
    return JSONResponse(
        status_code=422,
        content=format_error_response("VALIDATION_ERROR", msg, 422, exc.errors()),
    )

