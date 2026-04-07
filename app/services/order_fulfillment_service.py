import logging
from datetime import UTC, datetime

from app.config import settings
from app.models.order_status import OrderStatusEnum
from app.repositories.document_repository import DocumentRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.schemas.email import DocumentDeliveryContext
from app.services.document_service import DocumentService
from app.services.email_service import EmailService
from app.services.email_template_renderer import EmailTemplateRenderer

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
    ):
        self.order_repo = order_repo
        self.order_status_repo = order_status_repo
        self.document_repo = document_repo
        self.document_service = document_service
        self.email_service = email_service
        self.email_template_renderer = email_template_renderer

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

        documents = self.document_repo.get_documents_by_order_id(order_id)

        if not documents:
            try:
                document = self.document_service.generate_document_for_order(order_id)
                documents = [document]
            except Exception:
                logger.error("Document generation failed for order %d", order_id, exc_info=True)
                return

        access_token = documents[0].access_token if documents else ""
        document_id = documents[0].document_id if documents else order_id

        download_link = f"{settings.app_base_url}/api/v1/documents/{document_id}/download"
        if access_token:
            download_link += f"?token={access_token}"

        context_model = DocumentDeliveryContext(
            order_id=order_id,
            company_name=company_name or "",
            download_link=download_link,
            document_name=f"order_{order_id}_document.pdf",
        )
        html_body = self.email_template_renderer.render_document_delivery(context_model)

        try:
            self.email_service.send_email(order_id, recipient, "Your documents are ready", html_body)
        except Exception:
            logger.error("Email delivery failed for order %d", order_id, exc_info=True)

        self.order_status_repo.update_order_status(order_id, OrderStatusEnum.AVAILABLE)
        self.order_repo.update_completed_at(order_id, datetime.now(UTC))
