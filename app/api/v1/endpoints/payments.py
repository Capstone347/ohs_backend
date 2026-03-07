from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import (
    get_document_repository,
    get_email_service,
    get_email_template_renderer,
    get_order_repository,
    get_order_status_repository,
    get_payment_service,
)
from app.config import settings
from app.repositories.base_repository import RecordNotFoundError
from app.repositories.document_repository import DocumentRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.schemas.email import DocumentDeliveryContext
from app.schemas.payment import CheckoutSessionResponse, StripeConfigResponse
from app.services.email_service import EmailService
from app.services.email_template_renderer import EmailTemplateRenderer
from app.services.payment_service import PaymentService

router = APIRouter()


@router.get(
    "/stripe/config",
    response_model=StripeConfigResponse,
    status_code=status.HTTP_200_OK,
)
def get_stripe_config() -> StripeConfigResponse:
    return StripeConfigResponse(publishable_key=settings.stripe_publishable_key)


@router.post(
    "/orders/{order_id}/create-checkout-session",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_200_OK,
)
def create_checkout_session(
    order_id: int = Path(..., gt=0),
    order_repo: OrderRepository = Depends(get_order_repository),
    order_status_repo: OrderStatusRepository = Depends(get_order_status_repository),
    payment_service: PaymentService = Depends(get_payment_service),
) -> CheckoutSessionResponse:
    try:
        order = order_repo.get_by_id_with_relations(order_id)
    except RecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    if not order.user:
        raise HTTPException(status_code=400, detail="Order has no associated user")

    if not order.plan:
        raise HTTPException(status_code=400, detail="Order has no associated plan")

    amount_cents = int((order.total_amount * Decimal(100)).to_integral_value())
    currency = "CAD"
    if order.order_status and order.order_status.currency:
        currency = order.order_status.currency

    product_name = f"OHS Manual - {order.plan.name}"
    success_url = f"{settings.frontend_url}/orders/{order_id}/success"
    cancel_url = f"{settings.frontend_url}/orders/{order_id}/payment"

    checkout_response = payment_service.create_checkout_session(
        order_id=order_id,
        amount_cents=amount_cents,
        currency=currency,
        product_name=product_name,
        customer_email=order.user.email,
        success_url=success_url,
        cancel_url=cancel_url,
    )

    order_status_repo.update_stripe_checkout_session_id(
        order_id, checkout_response.checkout_session_id
    )

    return checkout_response


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
    try:
        order = order_repo.get_by_id_with_relations(order_id)
    except RecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    company_name = order.company.name if order.company else ""
    recipient = order.user.email if order.user else ""

    if not recipient:
        raise HTTPException(status_code=400, detail="Order has no associated user email")

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
