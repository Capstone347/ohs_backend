from decimal import Decimal
from types import SimpleNamespace

from fastapi import APIRouter, Path, Depends

from app.schemas import PaymentIntentResponse, PaymentCreate, StripePaymentIntentStatus
from app.database.session import get_db
from app.repositories.order_repository import OrderRepository

router = APIRouter()


@router.post(
    "/orders/{order_id}/payment-intent",
    response_model=PaymentIntentResponse,
)
def create_payment_intent(
    order_id: int = Path(..., gt=0),
    db=Depends(get_db),
) -> PaymentIntentResponse:
    order_repo = OrderRepository(db)
    order = order_repo.get_by_id_or_fail(order_id)

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


@router.post("/orders/{order_id}/deliver")
def trigger_order_delivery(order_id: int = Path(..., gt=0), db=Depends(get_db)) -> dict:
    """Trigger internal document delivery for an order (sends email).

    This endpoint is intended for internal use by webhooks or background jobs.
    """
    from app.repositories.email_log_repository import EmailLogRepository
    from app.repositories.order_repository import OrderRepository
    from app.services.email_template_renderer import EmailTemplateRenderer
    from app.services.email_service import EmailService
    from app.config import settings

    order_repo = OrderRepository(db)
    email_log_repo = EmailLogRepository(db)

    order = order_repo.get_by_id_with_relations(order_id)

    company_name = getattr(order.company, "name", "") if order and getattr(order, "company", None) else ""
    recipient = order.user.email if order and getattr(order, "user", None) else ""

    renderer = EmailTemplateRenderer()
    from app.schemas.email import DocumentDeliveryContext

    context_model = DocumentDeliveryContext(
        order_id=order_id,
        company_name=company_name or "",
        download_link=f"https://example.com/orders/{order_id}/download",
        document_name=f"order_{order_id}_document.pdf",
    )

    html_body = renderer.render_document_delivery(context_model) if renderer else ""

    email_service = EmailService(email_log_repo, settings)
    email_service.send_email(order_id, recipient, "Your documents are ready", html_body)

    return {"status": "delivery_triggered"}
