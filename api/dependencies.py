"""Cookie identity, exact Origin and synchronizer CSRF checks."""
import secrets

from fastapi import Depends, Request

from backend.config import get_settings
from backend.errors import ApiError
from backend.services.access import Principal, require_permission
from backend.services.auth import SessionContext, resolve_session


def check_origin(request: Request) -> None:
    allowed = {origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()}
    if request.headers.get("origin") not in allowed:
        raise ApiError("CSRF_FAILED", "Request origin is not allowed.", 403)


def get_session_context(request: Request) -> SessionContext:
    context = resolve_session(request.cookies.get(get_settings().auth_cookie_name))
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        received = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(received.encode(), context.csrf_token.encode()):
            raise ApiError("CSRF_FAILED", "CSRF token is invalid.", 403)
    return context


def get_current_principal(context: SessionContext = Depends(get_session_context)) -> Principal:
    return context.principal


def permission(name: str):
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        require_permission(principal, name)
        return principal
    return dependency
