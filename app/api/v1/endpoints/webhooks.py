import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_order_fulfillment_service,
    get_order_repository,
    get_order_status_repository,
    get_payment_service,
    get_sjp_generation_service,
)
from app.models.order_status import OrderStatusEnum, PaymentStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.schemas.payment import StripeWebhookEventType
from app.services.order_fulfillment_service import OrderFulfillmentService
from app.services.payment_service import PaymentService
from app.services.sjp_generation_service import SjpGenerationService

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
    fulfillment_service: OrderFulfillmentService = Depends(get_order_fulfillment_service),
    sjp_service: SjpGenerationService = Depends(get_sjp_generation_service),
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
            fulfillment_service=fulfillment_service,
            sjp_service=sjp_service,
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
    fulfillment_service: OrderFulfillmentService,
    sjp_service: SjpGenerationService,
) -> dict:
    order_status = order_status_repo.get_by_id(order_id)
    if order_status and order_status.payment_status == PaymentStatus.PAID.value:
        return {"status": "already_processed"}

    order_status_repo.mark_as_paid(order_id, payment_provider="stripe")

    if event.payment_intent_id:
        order_status_repo.update_stripe_payment_intent_id(order_id, event.payment_intent_id)

    order = order_repo.get_by_id_with_relations(order_id)

    if order and order.is_industry_specific:
        order_status_repo.update_order_status(order_id, OrderStatusEnum.PROCESSING)
        try:
            sjp_service.start_generation_for_webhook(order_id)
            logger.info(
                "Order %d is industry-specific, SJP generation started. Will move to review_pending on completion.",
                order_id,
            )
        except Exception:
            logger.error("Failed to start SJP generation for order %d", order_id, exc_info=True)
            order_status_repo.update_order_status(order_id, OrderStatusEnum.REVIEW_PENDING)
        return {"status": "ok", "action": "sjp_generation_started"}

    if order and order.plan and order.plan.requires_approval:
        order_status_repo.update_order_status(order_id, OrderStatusEnum.REVIEW_PENDING)
        logger.info("Order %d requires approval, set to review_pending", order_id)
        return {"status": "ok", "action": "review_pending"}

    fulfillment_service.fulfill_order(order_id)

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
