from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_legal_service
from app.services.legal_service import LegalService
from app.schemas.legal import (
    LegalDisclaimerResponse,
    LegalAcknowledgmentRequest,
    LegalAcknowledgmentResponse,
)
from app.services.exceptions import (
    ServiceException,
    FileNotFoundServiceException,
)
from app.repositories.base_repository import RecordNotFoundError

router = APIRouter()


@router.get("/legal-disclaimers/{plan_id}/{jurisdiction}", response_model=LegalDisclaimerResponse)
def get_legal_disclaimer(
    plan_id: int,
    jurisdiction: str,
    legal_service: LegalService = Depends(get_legal_service),
) -> LegalDisclaimerResponse:
    if plan_id <= 0:
        raise HTTPException(status_code=400, detail="plan_id must be greater than 0")
    
    if not jurisdiction:
        raise HTTPException(status_code=400, detail="jurisdiction is required")
    
    if len(jurisdiction) != 2:
        raise HTTPException(status_code=400, detail="jurisdiction must be a 2-character code")
    
    jurisdiction_upper = jurisdiction.upper()
    
    try:
        disclaimer_content = legal_service.get_legal_disclaimer(plan_id, jurisdiction_upper)
        
        return LegalDisclaimerResponse(
            plan_id=plan_id,
            jurisdiction=jurisdiction_upper,
            content=disclaimer_content,
            version=1
        )
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundServiceException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve legal disclaimer: {str(e)}")


@router.post("/orders/{order_id}/acknowledge-terms", response_model=LegalAcknowledgmentResponse, status_code=201)
def acknowledge_legal_terms(
    order_id: int,
    request: LegalAcknowledgmentRequest,
    legal_service: LegalService = Depends(get_legal_service),
) -> LegalAcknowledgmentResponse:
    if order_id <= 0:
        raise HTTPException(status_code=400, detail="order_id must be greater than 0")
    
    if not request.jurisdiction:
        raise HTTPException(status_code=400, detail="jurisdiction is required")
    
    if len(request.jurisdiction) != 2:
        raise HTTPException(status_code=400, detail="jurisdiction must be a 2-character code")
    
    if not request.content:
        raise HTTPException(status_code=400, detail="content is required")
    
    jurisdiction_upper = request.jurisdiction.upper()
    
    try:
        acknowledgment = legal_service.record_acknowledgment(
            order_id=order_id,
            jurisdiction=jurisdiction_upper,
            content=request.content,
            version=request.version
        )
        
        return LegalAcknowledgmentResponse(
            id=acknowledgment.id,
            order_id=acknowledgment.order_id,
            jurisdiction=acknowledgment.jurisdiction,
            version=acknowledgment.version,
            effective_date=acknowledgment.effective_date,
            acknowledged_at=datetime.now(timezone.utc)
        )
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record acknowledgment: {str(e)}")


@router.get("/orders/{order_id}/legal-acknowledgment", response_model=LegalAcknowledgmentResponse)
def get_order_legal_acknowledgment(
    order_id: int,
    legal_service: LegalService = Depends(get_legal_service),
) -> LegalAcknowledgmentResponse:
    if order_id <= 0:
        raise HTTPException(status_code=400, detail="order_id must be greater than 0")
    
    try:
        acknowledgment = legal_service.get_acknowledgment_by_order(order_id)
        
        return LegalAcknowledgmentResponse(
            id=acknowledgment.id,
            order_id=acknowledgment.order_id,
            jurisdiction=acknowledgment.jurisdiction,
            version=acknowledgment.version,
            effective_date=acknowledgment.effective_date,
            acknowledged_at=datetime.now(timezone.utc)
        )
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve acknowledgment: {str(e)}")
