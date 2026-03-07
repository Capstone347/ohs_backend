from pathlib import Path
from datetime import datetime, timezone, timedelta
from docx import Document
import secrets

from app.models.order import Order
from app.models.document import Document as DocumentModel, DocumentFormat
from app.repositories.order_repository import OrderRepository
from app.repositories.document_repository import DocumentRepository
from app.services.file_storage_service import FileStorageService
from app.utils.template_utils import (
    TemplateLoader,
    replace_template_variables,
    insert_company_logo,
    build_company_replacements,
)
from app.services.exceptions import (
    DocumentGenerationServiceException,
    FileNotFoundServiceException,
)


class DocumentGenerationService:
    def __init__(
        self,
        order_repository: OrderRepository,
        document_repository: DocumentRepository,
        file_storage_service: FileStorageService,
    ):
        self.order_repository = order_repository
        self.document_repository = document_repository
        self.file_storage_service = file_storage_service

    def generate_manual(self, order_id: int) -> DocumentModel:
        if not order_id:
            raise ValueError("order_id is required for manual generation")
        
        order = self.order_repository.get_by_id_with_relations(order_id)
        if not order:
            raise FileNotFoundServiceException(f"Order {order_id} not found")
        
        if not order.plan:
            raise DocumentGenerationServiceException(f"Order {order_id} has no associated plan")
        
        if not order.company:
            raise DocumentGenerationServiceException(f"Order {order_id} has no associated company")
        
        template_path = TemplateLoader.load_template(order.plan.slug)
        
        doc = Document(str(template_path))
        
        replacements = build_company_replacements(order.company, order_id)
        
        doc = replace_template_variables(doc, replacements)
        
        company_logo = self._get_company_logo(order)
        if company_logo:
            try:
                doc = insert_company_logo(doc, company_logo)
            except ValueError:
                pass
        
        output_path = self._generate_output_path(order_id)
        doc.save(str(output_path))
        
        document_model = self._create_document_record(order_id, output_path)
        
        return document_model

    def _get_company_logo(self, order: Order) -> Path | None:
        if not order.company_logos:
            return None
        
        if not order.company_logos:
            return None
        
        latest_logo = max(order.company_logos, key=lambda x: x.uploaded_at)
        
        logo_path = Path(latest_logo.file_path)
        if not logo_path.exists():
            return None
        
        return logo_path

    def _generate_output_path(self, order_id: int) -> Path:
        timestamp = int(datetime.now().timestamp())
        filename = f"order_{order_id}_{timestamp}.docx"
        return self.file_storage_service.generated_documents_dir / filename

    def _create_document_record(self, order_id: int, file_path: Path) -> DocumentModel:
        access_token = secrets.token_hex(32)
        token_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        
        document = DocumentModel(
            order_id=order_id,
            file_path=str(file_path),
            file_format=DocumentFormat.DOCX.value,
            access_token=access_token,
            token_expires_at=token_expires_at,
            generated_at=datetime.now(timezone.utc),
        )
        
        created_document = self.document_repository.create(document)
        
        return created_document
