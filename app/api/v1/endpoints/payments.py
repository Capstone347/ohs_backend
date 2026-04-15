from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import (
    get_order_fulfillment_service,
    get_order_repository,
    get_order_status_repository,
    get_payment_service,
)
from app.config import settings
from app.repositories.base_repository import RecordNotFoundError
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.schemas.payment import CheckoutSessionResponse, StripeConfigResponse
from app.services.order_fulfillment_service import OrderFulfillmentService
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
    if order.is_industry_specific and order.plan.slug != "industry_specific":
        product_name = f"OHS Manual - {order.plan.name} + Industry Specific"
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
    fulfillment_service: OrderFulfillmentService = Depends(get_order_fulfillment_service),
) -> dict:
    try:
        order = order_repo.get_by_id_with_relations(order_id)
    except RecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    fulfillment_service.fulfill_order(order_id)

    return {"status": "delivery_triggered"}
