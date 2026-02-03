from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Optional
import json

from app.schemas import StripeWebhookEvent, StripeWebhookEventType
from app.database.session import get_db
from app.services.payment_service import PaymentService
from app.services.stripe_provider import StripePaymentProvider
from app.config import settings

router = APIRouter()


@router.post("/webhooks/payment-confirmation")
async def handle_payment_webhook(request: Request, db=Depends(get_db)) -> dict:
    from app.repositories.order_status_repository import OrderStatusRepository

    signature = request.headers.get("stripe-signature") or request.headers.get("Stripe-Signature")
    body = await request.body()

    event: Optional[StripeWebhookEvent]

    if signature and settings.stripe_webhook_secret:
        provider = StripePaymentProvider(api_key=settings.stripe_api_key, webhook_secret=settings.stripe_webhook_secret)
        service = PaymentService(provider=provider)
        try:
            event = service.verify_webhook_signature(body, signature)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid webhook signature")
        except Exception:
            raise HTTPException(status_code=400, detail="failed to process webhook")
    else:
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
            event = StripeWebhookEvent(**payload)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid webhook payload")

    if event.event_type != StripeWebhookEventType.PAYMENT_INTENT_SUCCEEDED:
        return {"status": "ignored", "reason": "not a succeeded event"}

    metadata = event.metadata or {}
    order_id_str = metadata.get("order_id")
    if not order_id_str:
        return {"status": "error", "reason": "order_id missing from metadata"}

    try:
        order_id = int(order_id_str)
    except ValueError:
        return {"status": "error", "reason": "invalid order_id in metadata"}

    order_status_repo = OrderStatusRepository(db)

    order_status_repo.mark_as_paid(order_id, payment_provider="stripe")

    from app.api.v1.endpoints.payments import trigger_order_delivery

    trigger_order_delivery(order_id=order_id, db=db)

    return {"status": "ok"}
