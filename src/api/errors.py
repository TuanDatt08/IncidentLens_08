"""Stable public error envelope."""

from typing import Any

import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [str(part) for error in exc.errors() for part in error.get("loc", ())]
    code = "INVALID_VIDEO" if request.url.path.endswith("/incidents/upload") and "video" in fields else "INVALID_REQUEST"
    return JSONResponse(status_code=422, content={"error": {"code": code, "message": "Invalid request payload.", "details": None}})


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = "INTERNAL_ERROR" if exc.status_code >= 500 else "INVALID_REQUEST"
    message = "Internal server error." if exc.status_code >= 500 else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": message, "details": None}})


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled API error", exc_info=exc)
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error.", "details": None}})
