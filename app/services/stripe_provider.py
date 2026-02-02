from typing import Dict

from app.services.payment_service import BasePaymentProvider


class StripePaymentProvider(BasePaymentProvider):
    def __init__(self, api_key: str, webhook_secret: str):
        if not api_key:
            raise ValueError("api_key is required")
        if not webhook_secret:
            raise ValueError("webhook_secret is required")
        self.api_key = api_key
        self.webhook_secret = webhook_secret

    def create_payment_intent(self, order_id: int, amount_cents: int, currency: str = "cad") -> Dict[str, str]:
        if amount_cents <= 0:
            raise ValueError("amount_cents must be greater than zero")
        import stripe
        stripe.api_key = self.api_key
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            metadata={"order_id": str(order_id)},
        )

        if isinstance(intent, dict):
            id_ = intent.get("id")
            client_secret = intent.get("client_secret")
            status = intent.get("status")
            currency = intent.get("currency")
            amount = intent.get("amount")
        else:
            id_ = getattr(intent, "id", None)
            client_secret = getattr(intent, "client_secret", None)
            status = getattr(intent, "status", None)
            currency = getattr(intent, "currency", None)
            amount = getattr(intent, "amount", amount_cents)

        return {
            "id": id_,
            "client_secret": client_secret,
            "status": status,
            "currency": currency,
            "amount": str(amount),
        }

    def verify_webhook_signature(self, payload: bytes, signature: str) -> Dict:
        import stripe
        event = stripe.Webhook.construct_event(payload, signature, self.webhook_secret)
        return event
