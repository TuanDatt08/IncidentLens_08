"""Stable public error envelope."""

import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.errors import ApiError


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        headers={"Retry-After": str(exc.details["retry_after"])} if exc.code == "RATE_LIMITED" else None,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [str(part) for error in exc.errors() for part in error.get("loc", ())]
    code = "INVALID_VIDEO" if request.url.path.endswith("/incidents/upload") and "video" in fields else "INVALID_REQUEST"
    return JSONResponse(status_code=422, content={"error": {"code": code, "message": "Invalid request payload.", "details": None}})


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = "INTERNAL_ERROR" if exc.status_code >= 500 else "INVALID_REQUEST"
    message = "Internal server error." if exc.status_code >= 500 else str(exc.detail)
    return JSONResponse(status_code=exc.status_code,
        headers=exc.headers, content={"error": {"code": code, "message": message, "details": None}})


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled API error", exc_info=exc)
    return JSONResponse(status_code=500, headers={"Cache-Control": "no-store"}, content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error.", "details": None}})
