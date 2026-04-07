from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_authenticated_user_context,
    get_sjp_generation_service,
)
from app.schemas.sjp import SjpGenerationStartRequest, SjpGenerationJobResponse
from app.services.sjp_generation_service import (
    SjpGenerationService,
    OrderNotFound,
    InvalidOrderState,
    MissingIndustryProfile,
)

router = APIRouter()


@router.post(
    "/{order_id}/generate",
    response_model=SjpGenerationJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate SJP generation for a paid industry-specific order",
)
def initiate_sjp_generation(
    order_id: int,
    request: SjpGenerationStartRequest,
    user_context: dict = Depends(get_authenticated_user_context),
    sjp_service: SjpGenerationService = Depends(get_sjp_generation_service),
) -> SjpGenerationJobResponse:
    """
    POST /api/v1/sjp/{order_id}/generate

    Initiates the two-stage SJP generation pipeline for a paid order with is_industry_specific=True.

    **Request body:**
    - idempotency_key: optional string (auto-generated if omitted)

    **Validations:**
    - Order exists and belongs to authenticated user
    - Order is paid (payment_status == "paid")
    - Order has is_industry_specific=True
    - Order has industry profile with NAICS codes and province

    **Idempotency:**
    - If job already exists for this idempotency_key, returns existing job instead of creating duplicate
    - If duplicate generation requested, returns 409 Conflict or existing job

    **Response:**
    - job_id: Unique identifier for the generation job
    - status: Current status of the job (e.g., "pending")
    - created_at: Job creation timestamp

    **Error Responses:**
    - 400: Order is not paid or not industry-specific
    - 404: Order not found or not owned by user
    - 409: Duplicate generation (or returns existing job for idempotency)
    """
    user_id = user_context["id"]

    try:
        job = sjp_service.start_generation(
            order_id=order_id,
            user_id=user_id,
            idempotency_key=request.idempotency_key,
        )
    except OrderNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidOrderState as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except MissingIndustryProfile as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return SjpGenerationJobResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
    )
