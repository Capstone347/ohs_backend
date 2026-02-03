from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.dependencies import get_document_service
from app.services.document_service import DocumentService
from app.schemas.document import (
    DocumentGenerateResponse,
    DocumentPreviewResponse,
    DocumentResponse,
)
from app.services.exceptions import (
    FileNotFoundServiceException,
    DocumentGenerationServiceException,
)
from app.repositories.base_repository import RecordNotFoundError

router = APIRouter()


@router.post("/orders/{order_id}/generate-preview", response_model=DocumentGenerateResponse, status_code=201)
def generate_document_preview(
    order_id: int,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentGenerateResponse:
    if order_id <= 0:
        raise HTTPException(status_code=400, detail="order_id must be greater than 0")
    
    try:
        document = document_service.generate_document_for_order(order_id)
        
        return DocumentGenerateResponse(
            document_id=document.document_id,
            order_id=document.order_id,
            message="Document generated successfully",
            generated_at=document.generated_at
        )
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentGenerationServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")


@router.get("/documents/{document_id}/preview")
def get_document_preview(
    document_id: int,
    document_service: DocumentService = Depends(get_document_service),
) -> FileResponse:
    if document_id <= 0:
        raise HTTPException(status_code=400, detail="document_id must be greater than 0")
    
    try:
        preview_path = document_service.get_document_preview_path(document_id)
        
        if not preview_path.exists():
            raise HTTPException(status_code=404, detail="Preview file not found")
        
        return FileResponse(
            path=str(preview_path),
            media_type="application/pdf",
            filename=f"preview_document_{document_id}.pdf"
        )
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundServiceException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve preview: {str(e)}")


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: int,
    token: str = Query(..., min_length=1, description="Access token for document download"),
    document_service: DocumentService = Depends(get_document_service),
) -> FileResponse:
    if document_id <= 0:
        raise HTTPException(status_code=400, detail="document_id must be greater than 0")
    
    if not token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    try:
        document_path = document_service.get_document_download_path(document_id, token)
        
        if not document_path.exists():
            raise HTTPException(status_code=404, detail="Document file not found")
        
        return FileResponse(
            path=str(document_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"ohs_manual_document_{document_id}.docx"
        )
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundServiceException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentGenerationServiceException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download document: {str(e)}")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    if document_id <= 0:
        raise HTTPException(status_code=400, detail="document_id must be greater than 0")
    
    try:
        document = document_service.get_document_by_id(document_id)
        
        return DocumentResponse(
            document_id=document.document_id,
            order_id=document.order_id,
            file_path=document.file_path or "",
            file_format=document.file_format.value if document.file_format else "docx",
            access_token=document.access_token,
            token_expires_at=document.token_expires_at,
            generated_at=document.generated_at
        )
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")
