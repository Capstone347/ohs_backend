from pathlib import Path
from datetime import datetime, timezone

from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.order_repository import OrderRepository
from app.services.file_storage_service import FileStorageService
from app.services.document_generation_service import DocumentGenerationService
from app.services.preview_service import PreviewService
from app.services.exceptions import (
    FileNotFoundServiceException,
    DocumentGenerationServiceException,
)


class DocumentService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        order_repository: OrderRepository,
        file_storage_service: FileStorageService,
        document_generation_service: DocumentGenerationService,
        preview_service: PreviewService,
    ):
        self.document_repository = document_repository
        self.order_repository = order_repository
        self.file_storage_service = file_storage_service
        self.document_generation_service = document_generation_service
        self.preview_service = preview_service

    def generate_document_for_order(self, order_id: int) -> Document:
        if not order_id:
            raise ValueError("order_id is required for document generation")
        
        order = self.order_repository.get_by_id_or_fail(order_id)
        
        generated_document = self.document_generation_service.generate_manual(order_id)
        
        return generated_document

    def get_document_by_id(self, document_id: int) -> Document:
        if not document_id:
            raise ValueError("document_id is required")
        
        return self.document_repository.get_by_id_or_fail(document_id)

    def get_document_preview_path(self, document_id: int) -> Path:
        if not document_id:
            raise ValueError("document_id is required")
        
        document = self.document_repository.get_by_id_or_fail(document_id)
        
        preview_path = self.preview_service.generate_preview(document_id)
        
        return preview_path

    def get_document_download_path(self, document_id: int, access_token: str) -> Path:
        if not document_id:
            raise ValueError("document_id is required")
        
        if not access_token:
            raise ValueError("access_token is required for document download")
        
        document = self.document_repository.get_by_id_or_fail(document_id)
        
        if document.access_token != access_token:
            raise DocumentGenerationServiceException("Invalid access token")
        
        if document.token_expires_at < datetime.now(timezone.utc):
            raise DocumentGenerationServiceException("Access token has expired")
        
        if not document.file_path:
            raise FileNotFoundServiceException(f"Document {document_id} has no file path")
        
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise FileNotFoundServiceException(f"Document file not found: {file_path}")
        
        self.document_repository.increment_download_count(document_id)
        
        return file_path

    def validate_access_token(self, access_token: str) -> bool:
        if not access_token:
            raise ValueError("access_token is required")
        
        document = self.document_repository.get_by_access_token(access_token)
        
        if not document:
            return False
        
        if document.token_expires_at < datetime.now(timezone.utc):
            return False
        
        return True
