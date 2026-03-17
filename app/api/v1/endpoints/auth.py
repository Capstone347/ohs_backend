from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.dependencies import get_auth_service
from app.config import settings
from app.schemas.auth import (
    AuthenticatedUserResponse,
    RequestOtpRequest,
    RequestOtpResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/request-otp",
    response_model=RequestOtpResponse,
    status_code=status.HTTP_200_OK,
)
def request_otp(
    payload: RequestOtpRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> RequestOtpResponse:
    forwarded_for = request.headers.get("x-forwarded-for")
    request_ip = forwarded_for.split(",")[0].strip() if forwarded_for else None

    if not request_ip and request.client:
        request_ip = request.client.host

    auth_service.request_otp(payload.email, request_ip)
    return RequestOtpResponse()


@router.post(
    "/verify-otp",
    response_model=VerifyOtpResponse,
    status_code=status.HTTP_200_OK,
)
def verify_otp(
    payload: VerifyOtpRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> VerifyOtpResponse | JSONResponse:
    try:
        verification_result = auth_service.verify_otp(payload.email, payload.otp)
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid email or OTP"},
        )

    session_token = str(verification_result["session_token"])
    response.set_cookie(
        key="auth_session",
        value=session_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.auth_session_expiry_minutes * 60,
        path="/",
    )

    return VerifyOtpResponse(user=verification_result["user"])


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(
        key="auth_session",
        path="/",
        secure=settings.is_production,
        httponly=True,
        samesite="lax",
    )
    return {"message": "Logged out"}


@router.get(
    "/me",
    response_model=AuthenticatedUserResponse,
    status_code=status.HTTP_200_OK,
)
def get_authenticated_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthenticatedUserResponse | JSONResponse:
    session_token = request.cookies.get("auth_session")
    try:
        user_data = auth_service.get_authenticated_user(session_token)
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid auth session"},
        )

    return AuthenticatedUserResponse(**user_data)


