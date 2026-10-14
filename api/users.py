from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.dependencies import permission
from backend.models.auth_contracts import CreateUser, ResetPassword, UpdateUser
from backend.services.access import Principal
from backend.services.users import create_user, list_users, reset_password, update_user

router = APIRouter(prefix="/admin/users", tags=["users"])


@router.get("")
def listing(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), principal: Principal = Depends(permission("user:manage"))):
    return list_users(limit, offset, principal=principal)


@router.post("", status_code=201)
def create(data: CreateUser, principal: Principal = Depends(permission("user:manage"))):
    return create_user(data, principal=principal)


@router.patch("/{user_id}")
def update(user_id: UUID, data: UpdateUser, principal: Principal = Depends(permission("user:manage"))):
    return update_user(user_id, data, principal=principal)


@router.post("/{user_id}/reset-password", status_code=204)
def reset(user_id: UUID, data: ResetPassword, principal: Principal = Depends(permission("user:manage"))):
    reset_password(user_id, data.temporary_password, principal=principal)
