from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_industry_intake_service
from app.repositories.base_repository import RecordNotFoundError
from app.schemas.industry_intake import (
    IndustryIntakeAnswersRequest,
    IndustryIntakeAnswersResponse,
    IntakeQuestionsResponse,
)
from app.services.exceptions import OrderServiceException
from app.services.industry_intake_service import IndustryIntakeService

router = APIRouter()


@router.get(
    "/intake-questions",
    response_model=IntakeQuestionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dynamic intake questions for given NAICS codes",
)
def get_intake_questions(
    naics: str = Query(
        ...,
        description="Comma-separated NAICS codes (6 digits each)",
        example="236110,238210",
    ),
    intake_service: IndustryIntakeService = Depends(get_industry_intake_service),
) -> IntakeQuestionsResponse:
    naics_codes = [code.strip() for code in naics.split(",") if code.strip()]

    if not naics_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one NAICS code is required",
        )

    for code in naics_codes:
        if len(code) != 6 or not code.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid NAICS code: {code}. Must be exactly 6 digits",
            )

    return intake_service.get_intake_questions(naics_codes)


@router.put(
    "/{order_id}/intake-answers",
    response_model=IndustryIntakeAnswersResponse,
    status_code=status.HTTP_200_OK,
    summary="Save or update industry intake answers for an order",
)
def save_intake_answers(
    order_id: int,
    request: IndustryIntakeAnswersRequest,
    intake_service: IndustryIntakeService = Depends(get_industry_intake_service),
) -> IndustryIntakeAnswersResponse:
    try:
        return intake_service.save_intake_answers(order_id, request.answers)
    except RecordNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrderServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{order_id}/intake-answers",
    response_model=IndustryIntakeAnswersResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve saved industry intake answers for an order",
)
def get_intake_answers(
    order_id: int,
    intake_service: IndustryIntakeService = Depends(get_industry_intake_service),
) -> IndustryIntakeAnswersResponse:
    try:
        return intake_service.get_intake_answers(order_id)
    except RecordNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrderServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
