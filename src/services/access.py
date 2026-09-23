"""Local MVP access boundary until the identity provider is selected."""

from src.api.errors import ApiError
from src.config import get_settings


def require_demo_access() -> None:
    # Local demo has no user identity. Close write/media access in production
    # rather than treating a caller-supplied role header as authentication.
    if get_settings().app_env == "production":
        raise ApiError("PERMISSION_DENIED", "Authentication is required for this operation.", 403)
