import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_document_repository,
    get_document_service,
    get_email_service,
    get_email_template_renderer,
    get_order_repository,
    get_order_status_repository,
    get_payment_service,
)
from app.config import settings
from app.models.order_status import PaymentStatus
from app.repositories.document_repository import DocumentRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.schemas.email import DocumentDeliveryContext
from app.schemas.payment import StripeWebhookEventType
from app.services.document_service import DocumentService
from app.services.email_service import EmailService
from app.services.email_template_renderer import EmailTemplateRenderer
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/webhooks/stripe",
    status_code=status.HTTP_200_OK,
)
async def handle_stripe_webhook(
    request: Request,
    order_status_repo: OrderStatusRepository = Depends(get_order_status_repository),
    payment_service: PaymentService = Depends(get_payment_service),
    order_repo: OrderRepository = Depends(get_order_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    document_service: DocumentService = Depends(get_document_service),
    renderer: EmailTemplateRenderer = Depends(get_email_template_renderer),
    email_service: EmailService = Depends(get_email_service),
) -> dict:
    signature = request.headers.get("stripe-signature") or request.headers.get("Stripe-Signature")
    body = await request.body()

    if not body:
        raise HTTPException(status_code=400, detail="Request body is required")

    if not signature:
        raise HTTPException(status_code=400, detail="stripe-signature header is required")

    try:
        event = payment_service.verify_webhook_signature(body, signature)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if not event.event_type:
        return {"status": "ignored", "reason": "unhandled event type"}

    metadata = event.metadata or {}
    order_id = _extract_order_id(metadata)

    if not order_id:
        logger.warning("Webhook event %s missing order_id in metadata", event.event_type.value)
        return {"status": "ignored", "reason": "no order_id in metadata"}

    if event.event_type == StripeWebhookEventType.CHECKOUT_SESSION_COMPLETED:
        return _handle_checkout_completed(
            order_id=order_id,
            event=event,
            order_status_repo=order_status_repo,
            order_repo=order_repo,
            document_repo=document_repo,
            document_service=document_service,
            renderer=renderer,
            email_service=email_service,
        )

    if event.event_type == StripeWebhookEventType.CHECKOUT_SESSION_EXPIRED:
        return _handle_checkout_expired(order_id, order_status_repo)

    if event.event_type == StripeWebhookEventType.PAYMENT_INTENT_SUCCEEDED:
        return _handle_payment_intent_succeeded(order_id, event, order_status_repo)

    if event.event_type == StripeWebhookEventType.PAYMENT_INTENT_FAILED:
        return _handle_payment_intent_failed(order_id, order_status_repo)

    return {"status": "ignored", "reason": "unhandled event type"}


def _extract_order_id(metadata: dict[str, str]) -> int | None:
    order_id_str = metadata.get("order_id")
    if not order_id_str:
        return None
    try:
        order_id = int(order_id_str)
        return order_id if order_id > 0 else None
    except ValueError:
        return None


def _handle_checkout_completed(
    order_id: int,
    event: object,
    order_status_repo: OrderStatusRepository,
    order_repo: OrderRepository,
    document_repo: DocumentRepository,
    document_service: DocumentService,
    renderer: EmailTemplateRenderer,
    email_service: EmailService,
) -> dict:
    order_status = order_status_repo.get_by_id(order_id)
    if order_status and order_status.payment_status == PaymentStatus.PAID.value:
        return {"status": "already_processed"}

    order_status_repo.mark_as_paid(order_id, payment_provider="stripe")

    if event.payment_intent_id:
        order_status_repo.update_stripe_payment_intent_id(order_id, event.payment_intent_id)

    _generate_and_deliver(
        order_id=order_id,
        order_repo=order_repo,
        document_repo=document_repo,
        document_service=document_service,
        renderer=renderer,
        email_service=email_service,
    )

    return {"status": "ok"}


def _handle_checkout_expired(
    order_id: int,
    order_status_repo: OrderStatusRepository,
) -> dict:
    order_status_repo.mark_as_failed(order_id)
    logger.info("Checkout session expired for order %d", order_id)
    return {"status": "ok", "action": "marked_failed"}


def _handle_payment_intent_succeeded(
    order_id: int,
    event: object,
    order_status_repo: OrderStatusRepository,
) -> dict:
    if event.payment_intent_id:
        order_status_repo.update_stripe_payment_intent_id(order_id, event.payment_intent_id)
    logger.info("Payment intent succeeded for order %d (secondary confirmation)", order_id)
    return {"status": "ok", "action": "payment_intent_recorded"}


def _handle_payment_intent_failed(
    order_id: int,
    order_status_repo: OrderStatusRepository,
) -> dict:
    order_status_repo.mark_as_failed(order_id)
    logger.info("Payment intent failed for order %d", order_id)
    return {"status": "ok", "action": "marked_failed"}


def _generate_and_deliver(
    order_id: int,
    order_repo: OrderRepository,
    document_repo: DocumentRepository,
    document_service: DocumentService,
    renderer: EmailTemplateRenderer,
    email_service: EmailService,
) -> None:
    try:
        order = order_repo.get_by_id_with_relations(order_id)
    except Exception:
        logger.error("Failed to fetch order %d for delivery", order_id, exc_info=True)
        return

    if not order or not order.user:
        logger.warning("Order %d has no user, skipping delivery", order_id)
        return

    company_name = order.company.name if order.company else ""
    recipient = order.user.email

    documents = document_repo.get_documents_by_order_id(order_id)

    if not documents:
        try:
            document = document_service.generate_document_for_order(order_id)
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
    html_body = renderer.render_document_delivery(context_model)

    try:
        email_service.send_email(order_id, recipient, "Your documents are ready", html_body)
    except Exception:
        logger.error("Email delivery failed for order %d", order_id, exc_info=True)
