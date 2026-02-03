from pathlib import Path
from datetime import datetime

from app.repositories.document_repository import DocumentRepository
from app.services.file_storage_service import FileStorageService
from app.utils.pdf_utils import create_secure_preview_pdf
from app.services.exceptions import (
    FileNotFoundServiceException,
    DocumentGenerationServiceException,
)


class PreviewService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        file_storage_service: FileStorageService,
    ):
        self.document_repository = document_repository
        self.file_storage_service = file_storage_service

    def generate_preview(self, document_id: int) -> Path:
        if not document_id:
            raise ValueError("document_id is required for preview generation")
        
        document = self.document_repository.get_by_id(document_id)
        if not document:
            raise FileNotFoundServiceException(f"Document {document_id} not found")
        
        if not document.file_path:
            raise DocumentGenerationServiceException(f"Document {document_id} has no file path")
        
        source_path = Path(document.file_path)
        if not source_path.exists():
            raise FileNotFoundServiceException(f"Document file not found: {source_path}")
        
        order = document.order
        if not order or not order.plan:
            raise DocumentGenerationServiceException(f"Document {document_id} has no associated order or plan")
        
        preview_pdf_path = create_secure_preview_pdf(source_path, order.plan.slug)
        
        final_preview_path = self._move_to_preview_directory(preview_pdf_path, document.order_id, document_id)
        
        return final_preview_path

    def _move_to_preview_directory(self, temp_pdf_path: Path, order_id: int, document_id: int) -> Path:
        timestamp = int(datetime.now().timestamp())
        filename = f"preview_order_{order_id}_doc_{document_id}_{timestamp}.pdf"
        final_path = self.file_storage_service.preview_documents_dir / filename
        
        temp_pdf_path.rename(final_path)
        
        return final_path
