"""Signed local identity fixtures; production identity integration stays closed."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from backend.config import get_settings
from backend.errors import ApiError


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]
    recordings: frozenset[str]


def authenticate(authorization: str | None) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError("UNAUTHENTICATED", "Authentication required.", 401)
    settings = get_settings()
    if settings.app_env == "production":
        raise ApiError("IDENTITY_NOT_CONFIGURED", "Reviewed production identity integration required.", 503)
    secret = settings.v2_identity_secret
    if len(secret) < 32:
        raise ApiError("IDENTITY_NOT_CONFIGURED", "Local identity signing is not configured.", 503)
    try:
        token = authorization[7:]
        if len(token) > 16384:
            raise ValueError("identity too large")
        body, signature = token.split(".")
        expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        claims = json.loads(base64.b64decode(body + "=" * (-len(body) % 4), altchars=b"-_", validate=True))
        if not isinstance(claims, dict) or claims.get("iss") != "local-v2" or claims.get("aud") != "incidentlens-v2":
            raise ValueError("invalid issuer/audience")
        exp = claims["exp"]
        if isinstance(exp, bool) or not isinstance(exp, int) or exp <= time.time():
            raise ValueError("expired identity")
        subject, roles, recordings = claims["sub"], claims["roles"], claims["recordings"]
        if not isinstance(subject, str) or not subject.strip() or not isinstance(roles, list) or not roles or any(role not in {"Engineer", "Reviewer"} for role in roles):
            raise ValueError("invalid actor/roles")
        if not isinstance(recordings, list) or any(not isinstance(scope, str) or not scope.strip() for scope in recordings):
            raise ValueError("invalid scopes")
        return Principal(subject, frozenset(roles), frozenset(recordings))
    except (ValueError, KeyError, TypeError, UnicodeError, binascii.Error) as exc:
        raise ApiError("UNAUTHENTICATED", "Identity invalid or expired.", 401) from exc


def authorize(principal: Principal, recording_id: str, role: str | None = None) -> None:
    if recording_id not in principal.recordings:
        raise ApiError("NOT_FOUND", "Resource not found.", 404)
    if role is not None and role not in principal.roles:
        raise ApiError("PERMISSION_DENIED", "Role does not permit this action.", 403)
