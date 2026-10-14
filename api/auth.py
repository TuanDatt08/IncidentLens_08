from fastapi import APIRouter, Depends, Request, Response

from api.dependencies import check_origin, get_session_context
from backend.config import get_settings
from backend.errors import ApiError
from backend.models.auth_contracts import ChangePassword, Login
from backend.services.auth import SessionContext, change_password, login_user, logout

router = APIRouter(prefix="/auth", tags=["auth"])


def clear_cookie(response: Response):
    settings = get_settings()
    response.delete_cookie(settings.auth_cookie_name, path="/", secure=settings.auth_cookie_secure, httponly=True, samesite="lax")


@router.post("/login", dependencies=[Depends(check_origin)])
def login_route(data: Login, request: Request, response: Response):
    if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
        raise ApiError("INVALID_REQUEST", "Login requires JSON.", 415)
    user, token, csrf = login_user(data.email, data.password, request.client.host if request.client else "unknown")
    settings = get_settings()
    response.set_cookie(settings.auth_cookie_name, token, max_age=settings.auth_absolute_timeout_seconds,
                        httponly=True, secure=settings.auth_cookie_secure, samesite="lax", path="/")
    return {"user": user, "csrf_token": csrf}


@router.get("/me")
def me(context: SessionContext = Depends(get_session_context)):
    return {"user": context.user, "csrf_token": context.csrf_token}


@router.post("/logout", status_code=204)
def logout_route(response: Response, context: SessionContext = Depends(get_session_context)):
    logout(context)
    clear_cookie(response)


@router.post("/change-password", status_code=204)
def password_route(data: ChangePassword, response: Response, context: SessionContext = Depends(get_session_context)):
    change_password(context, data.current_password, data.new_password)
    clear_cookie(response)
