"""Argon2id passwords, opaque sessions and shared login failure budgets."""
import math
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select, update

from backend.config import get_settings
from backend.db import session_scope
from backend.errors import ApiError
from backend.models.auth import AuthEvent, LoginRateLimit, User, UserSession
from backend.models.auth_contracts import public_user
from backend.services.access import Principal

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    if not 6 <= len(password) <= 128:
        raise ValueError("Password must contain 6 to 128 characters")
    return password_hasher.hash(password)


def verify_password(encoded: str, password: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def utc_now() -> datetime:
    return datetime.now(UTC)


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def auth_required() -> ApiError:
    return ApiError("AUTHENTICATION_REQUIRED", "Sign in to continue.", 401)


@dataclass(frozen=True)
class SessionContext:
    principal: Principal
    session_id: UUID
    csrf_token: str
    user: dict


def revoke_sessions(session, user_id: UUID) -> None:
    session.execute(update(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None)).values(revoked_at=utc_now()))


def resolve_session(token: str | None) -> SessionContext:
    if not token or len(token) > 128:
        raise auth_required()
    result = None
    # Commit revocation on expiry before raising outside the transaction.
    with session_scope() as session:
        user_id = session.scalar(select(UserSession.user_id).where(UserSession.token_hash == token_hash(token)))
        user = session.scalar(select(User).where(User.id == user_id).with_for_update()) if user_id else None
        row = session.scalar(select(UserSession).where(UserSession.token_hash == token_hash(token)).with_for_update()) if user else None
        current = utc_now()
        if row and row.revoked_at is None:
            if not user.is_active or current >= aware(row.expires_at) or current - aware(row.last_seen_at) >= timedelta(seconds=get_settings().auth_idle_timeout_seconds):
                row.revoked_at = current
            else:
                row.last_seen_at = current
                result = SessionContext(Principal(user.id, frozenset(user.roles), user.must_change_password), row.id, row.csrf_token, public_user(user))
    if result is None:
        raise auth_required()
    return result


def _rate_keys(email: str, ip: str) -> list[tuple[str, int]]:
    settings = get_settings()
    return sorted([("email:" + token_hash(email), settings.auth_email_failure_limit), ("ip:" + token_hash(ip), settings.auth_ip_failure_limit)])


def _reserve_login(email: str, ip: str) -> datetime:
    """Reserve shared counters before hashing; release successful attempts.

    Atomic UPSERT plus row locks serialize workers. No DB locks held during Argon2.
    In-flight attempts conservatively count toward the failure budget.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    current = utc_now()
    retry = 0
    with session_scope() as session:
        session.execute(delete(LoginRateLimit).where(LoginRateLimit.window_start < current - timedelta(minutes=15)))
        rows = []
        insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
        for key, limit in _rate_keys(email, ip):
            session.execute(insert(LoginRateLimit).values(key=key, failures=0, window_start=current).on_conflict_do_nothing(index_elements=["key"]))
            row = session.scalar(select(LoginRateLimit).where(LoginRateLimit.key == key).with_for_update())
            rows.append(row)
            if row.failures >= limit:
                retry = max(retry, math.ceil((aware(row.window_start) + timedelta(minutes=15) - current).total_seconds()))
        if not retry:
            for row in rows:
                row.failures += 1
    if retry:
        raise ApiError("RATE_LIMITED", "Too many login attempts. Try again later.", 429, {"retry_after": max(1, retry)})
    return current


def login_user(email: str, password: str, ip: str) -> tuple[dict, str, str]:
    reserved_at = _reserve_login(email, ip)
    with session_scope() as session:
        user = session.scalar(select(User).where(User.email == email))
        encoded = user.password_hash if user else None
    # Unknown accounts perform the same expensive verification as known ones.
    valid = verify_password(encoded or _dummy_hash(), password)
    rehashed = hash_password(password) if valid and password_hasher.check_needs_rehash(encoded) else None
    result = None
    with session_scope() as session:
        user = session.scalar(select(User).where(User.email == email).with_for_update())
        if user and user.is_active and valid and user.password_hash == encoded:
            if rehashed:
                user.password_hash = rehashed
            current = utc_now()
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            session.add(UserSession(user_id=user.id, token_hash=token_hash(token), csrf_token=csrf,
                                    created_at=current, last_seen_at=current,
                                    expires_at=current + timedelta(seconds=get_settings().auth_absolute_timeout_seconds)))
            for key, _ in _rate_keys(email, ip):
                session.execute(update(LoginRateLimit).where(LoginRateLimit.key == key, LoginRateLimit.window_start <= reserved_at, LoginRateLimit.failures > 0).values(failures=LoginRateLimit.failures - 1))
            session.add(AuthEvent(event="LOGIN", actor_id=user.id, outcome="success"))
            result = (public_user(user), token, csrf)
        else:
            session.add(AuthEvent(event="LOGIN", target_id=user.id if user else None, outcome="failure"))
    if result is None:
        raise ApiError("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    return result


@lru_cache
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(32))


def logout(context: SessionContext) -> None:
    with session_scope() as session:
        # Match resolve/reset/change-password lock ordering (user -> session).
        # AuthEvent's user FK otherwise makes session-first logout deadlock
        # with a concurrent password reset which holds the user row.
        session.scalar(select(User).where(User.id == context.principal.user_id).with_for_update())
        session.execute(update(UserSession).where(UserSession.id == context.session_id).values(revoked_at=utc_now()))
        session.add(AuthEvent(event="LOGOUT", actor_id=context.principal.user_id, outcome="success"))


def change_password(context: SessionContext, current_password: str, new_password: str) -> None:
    with session_scope() as session:
        encoded = session.get(User, context.principal.user_id).password_hash
    if not verify_password(encoded, current_password):
        raise ApiError("INVALID_CREDENTIALS", "Current password is incorrect.", 401)
    if secrets.compare_digest(current_password.encode(), new_password.encode()):
        raise ApiError("INVALID_REQUEST", "Choose a different password.", 422)
    new_hash = hash_password(new_password)
    with session_scope() as session:
        user = session.scalar(select(User).where(User.id == context.principal.user_id).with_for_update())
        row = session.get(UserSession, context.session_id)
        if not user.is_active or user.password_hash != encoded or row.revoked_at is not None:
            raise auth_required()
        user.password_hash = new_hash
        user.must_change_password = False
        revoke_sessions(session, user.id)
        session.add(AuthEvent(event="PASSWORD_CHANGED", actor_id=user.id, outcome="success"))
