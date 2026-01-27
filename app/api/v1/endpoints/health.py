from datetime import datetime, UTC

from fastapi import APIRouter

from app.config import settings
from app.schemas.common import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        environment=settings.environment.value,
        timestamp=datetime.now(UTC)
    )
