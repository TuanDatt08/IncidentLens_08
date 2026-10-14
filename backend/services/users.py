"""Admin account management and transactionally serialized last-admin invariant."""
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from backend.db import session_scope
from backend.errors import ApiError
from backend.models.auth import AuthEvent, User
from backend.models.auth_contracts import CreateUser, UpdateUser, public_user
from backend.services.access import Principal, require_permission
from backend.services.auth import hash_password, revoke_sessions


def list_users(limit: int, offset: int, *, principal: Principal):
    require_permission(principal, "user:manage")
    with session_scope() as session:
        total = session.scalar(select(func.count()).select_from(User))
        items = session.scalars(select(User).order_by(User.created_at, User.id).limit(limit).offset(offset))
        return {"items": [public_user(user) for user in items], "total": total, "limit": limit, "offset": offset}


def create_user(data: CreateUser, *, principal: Principal):
    require_permission(principal, "user:manage")
    encoded = hash_password(data.temporary_password)
    try:
        with session_scope() as session:
            user = User(email=data.email, display_name=data.display_name, roles=data.roles, password_hash=encoded)
            session.add(user)
            session.flush()
            session.add(AuthEvent(event="USER_CREATED", actor_id=principal.user_id, target_id=user.id, outcome="success"))
            return {"user": public_user(user)}
    except IntegrityError as exc:
        raise ApiError("EMAIL_ALREADY_EXISTS", "Email already exists.", 409) from exc


def _lock_admins(session):
    # All admin mutations share a transaction advisory lock in PG. This also
    # serializes operations targeting different rows, unlike row locks alone.
    if session.bind.dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(20261010)"))
    elif session.bind.dialect.name == "sqlite":
        session.execute(text("BEGIN IMMEDIATE"))


def _target(session, user_id):
    user = session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise ApiError("USER_NOT_FOUND", "User was not found.", 404)
    return user


def update_user(user_id: UUID, data: UpdateUser, *, principal: Principal):
    require_permission(principal, "user:manage")
    with session_scope() as session:
        _lock_admins(session)
        user = _target(session, user_id)
        changes = data.model_dump(exclude_unset=True)
        removing_admin = user.is_active and "admin" in user.roles and (
            changes.get("is_active") is False or "admin" not in changes.get("roles", user.roles))
        if removing_admin:
            active = session.scalars(select(User).where(User.is_active.is_(True))).all()
            if sum("admin" in item.roles for item in active) <= 1:
                raise ApiError("LAST_ADMIN_REQUIRED", "Keep at least one active administrator.", 409)
        revoke = ("roles" in changes and changes["roles"] != user.roles) or ("is_active" in changes and changes["is_active"] != user.is_active)
        for key, value in changes.items():
            setattr(user, key, value)
        if revoke:
            revoke_sessions(session, user.id)
        session.add(AuthEvent(event="USER_UPDATED", actor_id=principal.user_id, target_id=user.id, outcome="success", event_metadata={"fields": sorted(changes)}))
        return {"user": public_user(user)}


def reset_password(user_id: UUID, password: str, *, principal: Principal):
    require_permission(principal, "user:manage")
    encoded = hash_password(password)
    with session_scope() as session:
        user = _target(session, user_id)
        user.password_hash = encoded
        user.must_change_password = True
        revoke_sessions(session, user.id)
        session.add(AuthEvent(event="PASSWORD_RESET", actor_id=principal.user_id, target_id=user.id, outcome="success"))
