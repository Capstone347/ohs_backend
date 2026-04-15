import stripe as _stripe

from app.schemas.payment import (
    CheckoutSessionResponse,
    StripeWebhookEvent,
    StripeWebhookEventType,
)
from app.services.payment_service import BasePaymentProvider


class StripePaymentProvider(BasePaymentProvider):
    def __init__(self, api_key: str, webhook_secret: str):
        if not api_key:
            raise ValueError("api_key is required")
        if not webhook_secret:
            raise ValueError("webhook_secret is required")

        self.api_key = api_key
        self.webhook_secret = webhook_secret
        _stripe.api_key = self.api_key

    def create_checkout_session(
        self,
        order_id: int,
        amount_cents: int,
        currency: str,
        product_name: str,
        customer_email: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResponse:
        if not order_id:
            raise ValueError("order_id is required")

        if amount_cents <= 0:
            raise ValueError("amount_cents must be greater than zero")

        if not currency:
            raise ValueError("currency is required")

        if not product_name:
            raise ValueError("product_name is required")

        if not customer_email:
            raise ValueError("customer_email is required")

        if not success_url:
            raise ValueError("success_url is required")

        if not cancel_url:
            raise ValueError("cancel_url is required")

        try:
            session = _stripe.checkout.Session.create(
                mode="payment",
                customer_email=customer_email,
                line_items=[
                    {
                        "price_data": {
                            "currency": currency.lower(),
                            "product_data": {"name": product_name},
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                metadata={"order_id": str(order_id)},
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except _stripe.StripeError as exc:
            raise RuntimeError("failed to create checkout session") from exc

        return CheckoutSessionResponse(
            checkout_session_id=session.id,
            checkout_url=session.url,
        )

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> StripeWebhookEvent:
        if not payload:
            raise ValueError("payload is required")

        if not signature:
            raise ValueError("signature is required")

        try:
            event = _stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret,
            )
        except _stripe.SignatureVerificationError as exc:
            raise ValueError("invalid webhook signature") from exc

        return _normalize_event(event)


def _safe_get(obj: object, *keys: str, default: object = None) -> object:
    try:
        cur = obj
        for k in keys:
            if cur is None:
                return default
            if isinstance(cur, dict):
                cur = cur.get(k)
            else:
                cur = getattr(cur, k, None)
        return cur if cur is not None else default
    except Exception:
        return default


def _normalize_event(event: object) -> StripeWebhookEvent:
    raw_type = _safe_get(event, "type")
    try:
        event_type = StripeWebhookEventType(raw_type)
    except ValueError:
        event_type = None

    obj = _safe_get(event, "data", "object") or {}

    checkout_session_id: str | None = None
    payment_intent_id: str | None = None
    payment_status: str | None = None

    if raw_type in (
        "checkout.session.completed",
        "checkout.session.expired",
    ):
        checkout_session_id = _safe_get(obj, "id")
        payment_intent_id = _safe_get(obj, "payment_intent")
        payment_status = _safe_get(obj, "payment_status")
    elif raw_type in (
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
    ):
        payment_intent_id = _safe_get(obj, "id")
        payment_status = _safe_get(obj, "status")

    metadata_raw = _safe_get(obj, "metadata") or {}
    if hasattr(metadata_raw, "to_dict"):
        metadata_raw = metadata_raw.to_dict()
    metadata: dict[str, str] = {}
    if isinstance(metadata_raw, dict):
        for k, v in metadata_raw.items():
            metadata[str(k)] = str(v) if v is not None else ""

    return StripeWebhookEvent(
        event_type=event_type,
        checkout_session_id=checkout_session_id,
        payment_intent_id=payment_intent_id,
        metadata=metadata,
        payment_status=payment_status,
    )
