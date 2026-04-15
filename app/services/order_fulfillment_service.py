import logging
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.models.order_status import OrderStatusEnum
from app.models.plan import PlanSlug
from app.repositories.document_repository import DocumentRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.repositories.sjp_generation_job_repository import SjpGenerationJobRepository
from app.schemas.email import DocumentDeliveryContext
from app.services.document_service import DocumentService
from app.services.email_service import EmailService
from app.services.email_template_renderer import EmailTemplateRenderer
from app.services.sjp_document_service import SjpDocumentService

logger = logging.getLogger(__name__)


class OrderFulfillmentService:
    def __init__(
        self,
        order_repo: OrderRepository,
        order_status_repo: OrderStatusRepository,
        document_repo: DocumentRepository,
        document_service: DocumentService,
        email_service: EmailService,
        email_template_renderer: EmailTemplateRenderer,
        sjp_document_service: SjpDocumentService,
        sjp_job_repo: SjpGenerationJobRepository,
    ):
        self.order_repo = order_repo
        self.order_status_repo = order_status_repo
        self.document_repo = document_repo
        self.document_service = document_service
        self.email_service = email_service
        self.email_template_renderer = email_template_renderer
        self.sjp_document_service = sjp_document_service
        self.sjp_job_repo = sjp_job_repo

    def fulfill_order(self, order_id: int) -> None:
        try:
            order = self.order_repo.get_by_id_with_relations(order_id)
        except Exception:
            logger.error("Failed to fetch order %d for delivery", order_id, exc_info=True)
            return

        if not order or not order.user:
            logger.warning("Order %d has no user, skipping delivery", order_id)
            return

        company_name = order.company.name if order.company else ""
        recipient = order.user.email

        is_standalone_sjp = (
            order.is_industry_specific
            and order.plan
            and order.plan.slug == PlanSlug.INDUSTRY_SPECIFIC.value
        )
        is_addon_sjp = (
            order.is_industry_specific
            and order.plan
            and order.plan.slug != PlanSlug.INDUSTRY_SPECIFIC.value
        )

        documents = self.document_repo.get_documents_by_order_id(order_id)

        if is_standalone_sjp:
            sjp_doc = self._generate_sjp_document(order_id, company_name, order)
            if not sjp_doc:
                return
            documents = [sjp_doc]

        elif is_addon_sjp:
            manual_doc = self._ensure_manual_document(order_id, documents)
            if not manual_doc:
                return
            sjp_doc = self._generate_sjp_document(order_id, company_name, order)
            documents = [d for d in [manual_doc, sjp_doc] if d]

        else:
            if not documents:
                try:
                    document = self.document_service.generate_document_for_order(order_id)
                    documents = [document]
                except Exception:
                    logger.error("Document generation failed for order %d", order_id, exc_info=True)
                    return

        if not documents:
            logger.error("No documents generated for order %d", order_id)
            return

        primary_doc = documents[0]
        download_link = self._build_download_link(primary_doc)

        sjp_download_link = None
        sjp_count = None
        if len(documents) > 1:
            sjp_download_link = self._build_download_link(documents[1])
            sjp_count = self._get_sjp_count(order_id)

        context_model = DocumentDeliveryContext(
            order_id=order_id,
            company_name=company_name or "",
            download_link=download_link,
            document_name=f"order_{order_id}_document.pdf",
            sjp_download_link=sjp_download_link,
            sjp_count=sjp_count,
        )
        html_body = self.email_template_renderer.render_document_delivery(context_model)

        try:
            self.email_service.send_email(order_id, recipient, "Your documents are ready", html_body)
        except Exception:
            logger.error("Email delivery failed for order %d", order_id, exc_info=True)

        self.order_status_repo.update_order_status(order_id, OrderStatusEnum.AVAILABLE)
        self.order_repo.update_completed_at(order_id, datetime.now(UTC))

    def _get_sjp_count(self, order_id: int) -> int:
        jobs = self.sjp_job_repo.get_by_order_id(order_id)
        if not jobs:
            return 0
        return len(jobs[0].toc_entries) if jobs[0].toc_entries else 0

    def _generate_sjp_document(self, order_id: int, company_name: str, order):
        try:
            jobs = self.sjp_job_repo.get_by_order_id(order_id)
            if not jobs:
                logger.error("No SJP generation job found for order %d", order_id)
                return None

            job = jobs[0]

            logo_path = None
            if order.company_logos:
                latest_logo = max(order.company_logos, key=lambda x: x.uploaded_at)
                path = Path(latest_logo.file_path)
                if path.exists():
                    logo_path = path

            return self.sjp_document_service.generate_sjp_document(
                job_id=job.id,
                order_id=order_id,
                company_name=company_name,
                logo_path=logo_path,
            )
        except Exception:
            logger.error("SJP document generation failed for order %d", order_id, exc_info=True)
            return None

    def _ensure_manual_document(self, order_id: int, existing_documents: list):
        if existing_documents:
            return existing_documents[0]
        try:
            return self.document_service.generate_document_for_order(order_id)
        except Exception:
            logger.error("Manual document generation failed for order %d", order_id, exc_info=True)
            return None

    def _build_download_link(self, document) -> str:
        link = f"{settings.app_base_url}/api/v1/documents/{document.document_id}/download"
        if document.access_token:
            link += f"?token={document.access_token}"
        return link
