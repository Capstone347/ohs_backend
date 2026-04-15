from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_authenticated_user_context,
    get_sjp_generation_service,
)
from app.schemas.sjp import (
    SjpContentResponse,
    SjpFullContentResponse,
    SjpGenerationJobResponse,
    SjpGenerationStartRequest,
    SjpGenerationStatusResponse,
)
from app.services.sjp_generation_service import (
    InvalidOrderState,
    MissingIndustryProfile,
    OrderNotFound,
    SjpGenerationJobNotFound,
    SjpGenerationService,
)

router = APIRouter()


@router.post(
    "/{order_id}/generate",
    response_model=SjpGenerationJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate SJP generation for a paid industry-specific order",
)
async def initiate_sjp_generation(
    order_id: int,
    request: SjpGenerationStartRequest,
    user_context: dict = Depends(get_authenticated_user_context),
    sjp_service: SjpGenerationService = Depends(get_sjp_generation_service),
) -> SjpGenerationJobResponse:
    user_id = user_context["id"]

    try:
        job = sjp_service.start_generation(
            order_id=order_id,
            user_id=user_id,
            idempotency_key=request.idempotency_key,
        )
    except OrderNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidOrderState as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except MissingIndustryProfile as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return SjpGenerationJobResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
    )


@router.get(
    "/{order_id}/status",
    response_model=SjpGenerationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get SJP generation status for an order (public)",
)
def get_sjp_generation_status(
    order_id: int,
    sjp_service: SjpGenerationService = Depends(get_sjp_generation_service),
) -> SjpGenerationStatusResponse:
    try:
        return sjp_service.get_generation_status(order_id=order_id)
    except OrderNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SjpGenerationJobNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{order_id}/content",
    response_model=SjpFullContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full SJP content for a completed generation job",
)
def get_sjp_content(
    order_id: int,
    user_context: dict = Depends(get_authenticated_user_context),
    sjp_service: SjpGenerationService = Depends(get_sjp_generation_service),
) -> SjpFullContentResponse:
    user_id = int(user_context["id"])

    try:
        return sjp_service.get_full_content(order_id=order_id, user_id=user_id)
    except OrderNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SjpGenerationJobNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{order_id}/content/{toc_entry_id}",
    response_model=SjpContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single SJP entry content",
)
def get_single_sjp_content(
    order_id: int,
    toc_entry_id: int,
    user_context: dict = Depends(get_authenticated_user_context),
    sjp_service: SjpGenerationService = Depends(get_sjp_generation_service),
) -> SjpContentResponse:
    user_id = int(user_context["id"])

    try:
        return sjp_service.get_single_sjp_content(
            order_id=order_id, toc_entry_id=toc_entry_id, user_id=user_id
        )
    except OrderNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SjpGenerationJobNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
