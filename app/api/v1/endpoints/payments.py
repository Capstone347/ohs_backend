from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import (
    get_order_repository,
    get_email_log_repository,
    get_email_template_renderer,
    get_email_service,
    get_document_repository,
)
from app.repositories.order_repository import OrderRepository
from app.repositories.email_log_repository import EmailLogRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.base_repository import RecordNotFoundError
from app.schemas.payment import PaymentIntentResponse, StripePaymentIntentStatus
from app.schemas.email import DocumentDeliveryContext
from app.services.email_template_renderer import EmailTemplateRenderer
from app.services.email_service import EmailService
from app.config import settings

router = APIRouter()


@router.post(
    "/orders/{order_id}/payment-intent",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_200_OK,
)
def create_payment_intent(
    order_id: int = Path(..., gt=0),
    order_repo: OrderRepository = Depends(get_order_repository),
) -> PaymentIntentResponse:
    if order_id <= 0:
        raise HTTPException(status_code=400, detail="order_id must be greater than 0")
    
    try:
        order = order_repo.get_by_id_or_fail(order_id)
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    amount_cents = int((order.total_amount * Decimal(100)).to_integral_value())
    currency = "CAD"
    if getattr(order, "order_status", None) and getattr(order.order_status, "currency", None):
        currency = order.order_status.currency

    pi_id = f"pi_mock_{order_id}"
    client_secret = f"secret_mock_{order_id}"

    return PaymentIntentResponse(
        id=pi_id,
        client_secret=client_secret,
        status=StripePaymentIntentStatus.SUCCEEDED,
        amount_cents=amount_cents,
        currency=currency,
    )


@router.post(
    "/orders/{order_id}/deliver",
    status_code=status.HTTP_200_OK,
)
def trigger_order_delivery(
    order_id: int = Path(..., gt=0),
    order_repo: OrderRepository = Depends(get_order_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    renderer: EmailTemplateRenderer = Depends(get_email_template_renderer),
    email_service: EmailService = Depends(get_email_service),
) -> dict:
    if order_id <= 0:
        raise HTTPException(status_code=400, detail="order_id must be greater than 0")

    try:
        order = order_repo.get_by_id_with_relations(order_id)
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    company_name = getattr(order.company, "name", "") if order and getattr(order, "company", None) else ""
    recipient = order.user.email if order and getattr(order, "user", None) else ""
    
    if not recipient:
        raise HTTPException(status_code=400, detail="Order has no associated user email")

    # Get document with access token
    documents = document_repo.get_documents_by_order_id(order_id)
    access_token = documents[0].access_token if documents else ""
    
    download_link = f"{settings.app_base_url}/api/v1/documents/{order_id}/download"
    if access_token:
        download_link += f"?token={access_token}"

    context_model = DocumentDeliveryContext(
        order_id=order_id,
        company_name=company_name or "",
        download_link=download_link,
        document_name=f"order_{order_id}_document.pdf",
    )

    html_body = renderer.render_document_delivery(context_model)

    email_service.send_email(order_id, recipient, "Your documents are ready", html_body)

    return {"status": "delivery_triggered"}
