from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import get_admin_auth_service, get_authenticated_admin_context
from app.schemas.admin_auth import (
    AdminChangePasswordRequest,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUserResponse,
)
from app.services.admin_auth_service import AdminAuthService

router = APIRouter()

ADMIN_COOKIE_NAME = "admin_session"
ADMIN_COOKIE_MAX_AGE = 60 * 60 * 8


@router.post(
    "/auth/login",
    response_model=AdminLoginResponse,
    status_code=status.HTTP_200_OK,
)
def admin_login(
    body: AdminLoginRequest,
    response: Response,
    admin_auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminLoginResponse:
    try:
        result = admin_auth_service.login(body.email, body.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from None

    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=result["session_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ADMIN_COOKIE_MAX_AGE,
    )

    return AdminLoginResponse(admin=AdminUserResponse(**result["admin"]))


@router.get(
    "/auth/me",
    response_model=AdminUserResponse,
    status_code=status.HTTP_200_OK,
)
def admin_me(
    admin_context: dict[str, int | str] = Depends(get_authenticated_admin_context),
) -> AdminUserResponse:
    return AdminUserResponse(**admin_context)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
)
def admin_logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key=ADMIN_COOKIE_NAME)
    return {"message": "logged out"}


@router.post(
    "/auth/change-password",
    status_code=status.HTTP_200_OK,
)
def admin_change_password(
    body: AdminChangePasswordRequest,
    admin_context: dict[str, int | str] = Depends(get_authenticated_admin_context),
    admin_auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> dict[str, str]:
    try:
        admin_auth_service.change_password(
            admin_id=admin_context["id"],
            current_password=body.current_password,
            new_password=body.new_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    return {"message": "password changed"}
