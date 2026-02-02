from abc import ABC, abstractmethod

from app.schemas.payment import (
    PaymentIntentResponse,
    StripePaymentIntentStatus,
    StripeWebhookEvent,
    StripeWebhookEventType,
)


class BasePaymentProvider(ABC):
    @abstractmethod
    def create_payment_intent(
        self,
        order_id: int,
        amount_cents: int,
        currency: str
    ) -> PaymentIntentResponse:
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> StripeWebhookEvent:
        pass


class MockPaymentProvider(BasePaymentProvider):
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
        
        return PaymentIntentResponse(
            id=f"pi_mock_{order_id}",
            client_secret=f"cs_mock_{order_id}",
            status=StripePaymentIntentStatus.SUCCEEDED,
            amount_cents=amount_cents,
            currency=currency,
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
        
        return StripeWebhookEvent(
            event_type=StripeWebhookEventType.PAYMENT_INTENT_SUCCEEDED,
            payment_intent_id="pi_mock",
            metadata={"order_id": "1"}
        )


class PaymentService:
    def __init__(self, provider: BasePaymentProvider | None = None):
        self.provider = provider or MockPaymentProvider()

    def create_payment_intent(
        self,
        order_id: int,
        amount_cents: int,
        currency: str = "CAD"
    ) -> PaymentIntentResponse:
        return self.provider.create_payment_intent(order_id, amount_cents, currency)

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> StripeWebhookEvent:
        return self.provider.verify_webhook_signature(payload, signature)
