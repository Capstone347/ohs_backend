from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import get_auth_service
from app.schemas.auth import RequestOtpRequest, RequestOtpResponse
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

