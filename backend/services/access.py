"""Verified user identity and explicit additive permissions."""
from dataclasses import dataclass
from uuid import UUID

from backend.config import get_settings
from backend.errors import ApiError


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    roles: frozenset[str]
    must_change_password: bool


PERMISSIONS = {
    "engineer": {"incident:read", "incident:create", "analysis:create", "report:edit", "report:submit"},
    "reviewer": {"incident:read", "report:approve", "report:reject"},
    "admin": {"incident:read", "user:manage"},
}


def require_permission(principal: Principal, permission: str) -> None:
    if principal.must_change_password:
        raise ApiError("PASSWORD_CHANGE_REQUIRED", "Change your temporary password before continuing.", 403)
    if not any(permission in PERMISSIONS.get(role, set()) for role in principal.roles):
        raise ApiError("PERMISSION_DENIED", "You do not have permission for this operation.", 403)


def require_demo_access() -> None:
    # Local demo has no user identity. Close write/media access in production
    # rather than treating a caller-supplied role header as authentication.
    if get_settings().app_env == "production":
        raise ApiError("PERMISSION_DENIED", "Authentication is required for this operation.", 403)
