from app.services.payment_service import BasePaymentProvider
from app.schemas.payment import (
    PaymentIntentResponse,
    StripePaymentIntentStatus,
    StripeWebhookEvent,
    StripeWebhookEventType,
)
import json


class StripePaymentProvider(BasePaymentProvider):
    def __init__(self, api_key: str, webhook_secret: str):
        if not api_key:
            raise ValueError("api_key is required")
        if not webhook_secret:
            raise ValueError("webhook_secret is required")
        self.api_key = api_key
        self.webhook_secret = webhook_secret

    def create_payment_intent(
        self,
        order_id: int,
        amount_cents: int,
        currency: str = "CAD"
    ) -> PaymentIntentResponse:
        if not order_id:
            raise ValueError("order_id is required")
        
        if amount_cents <= 0:
            raise ValueError("amount_cents must be greater than zero")
        
        if not currency:
            raise ValueError("currency is required")
        
        import stripe as _stripe

        _stripe.api_key = self.api_key

        try:
            intent = _stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata={"order_id": str(order_id)},
            )
        except Exception as exc:
            raise RuntimeError("failed to create payment intent") from exc

        intent_id = self._safe_get(intent, "id")
        client_secret = self._safe_get(intent, "client_secret")
        status = self._safe_get(intent, "status")
        amount_val = self._safe_get(intent, "amount")
        try:
            amount_cents_ret = int(amount_val) if amount_val is not None else 0
        except (TypeError, ValueError):
            amount_cents_ret = 0

        intent_currency = (self._safe_get(intent, "currency") or "").upper()

        return {
            "id": intent_id,
            "client_secret": client_secret,
            "status": status,
            "amount_cents": amount_cents_ret,
            "currency": intent_currency,
        }

    def _safe_get(self, obj, *keys, default=None):
        """Safe nested getter that works for dicts or SDK objects.

        Usage:
            self._safe_get(event, "data", "object", "id")
        """
        try:
            cur = obj
            if len(keys) == 1:
                k = keys[0]
                if isinstance(cur, dict):
                    return cur.get(k, default)
                return getattr(cur, k, default)

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

    def _normalize_event(self, event) -> StripeWebhookEvent:
        """Normalize a raw Stripe SDK event (dict or object) into our
        StripeWebhookEvent model.
        """
        raw_type = self._safe_get(event, "type")
        try:
            event_type = StripeWebhookEventType(raw_type)
        except Exception:
            event_type = None

        obj = self._safe_get(event, "data", "object")
        if obj is None:
            obj = self._safe_get(event, "data", "object", default={})

        payment_intent_id = self._safe_get(obj, "id") or self._safe_get(event, "data", "object", "id")
        metadata_raw = self._safe_get(obj, "metadata") or {}

        metadata: dict[str, str] = {}
        if isinstance(metadata_raw, dict):
            for k, v in metadata_raw.items():
                metadata[str(k)] = str(v) if v is not None else ""

        return StripeWebhookEvent(
            event_type=event_type or StripeWebhookEventType.PAYMENT_INTENT_SUCCEEDED,
            payment_intent_id=payment_intent_id or "",
            metadata=metadata,
        )

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> StripeWebhookEvent:
        if not payload:
            raise ValueError("payload is required")
        
        if not signature:
            raise ValueError("signature is required")
        
        if not self.webhook_secret:
            raise ValueError("webhook_secret is not configured")
        
        import stripe as _stripe

        try:
            event = _stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
        except Exception as exc:
            raise ValueError("invalid webhook signature") from exc

        return self._normalize_event(event)
