import stripe

from app.services.payment_service import BasePaymentProvider
from app.schemas.payment import (
    PaymentIntentResponse,
    StripePaymentIntentStatus,
    StripeWebhookEvent,
    StripeWebhookEventType,
)


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
        
        stripe.api_key = self.api_key
        
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency.lower(),
            metadata={"order_id": str(order_id)},
        )
        
        return PaymentIntentResponse(
            id=intent.id,
            client_secret=intent.client_secret,
            status=StripePaymentIntentStatus(intent.status),
            amount_cents=intent.amount,
            currency=intent.currency.upper(),
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
        
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            self.webhook_secret
        )
        
        event_type = StripeWebhookEventType(event["type"])
        payment_intent = event["data"]["object"]
        
        return StripeWebhookEvent(
            event_type=event_type,
            payment_intent_id=payment_intent["id"],
            metadata=payment_intent.get("metadata", {}),
        )
