from abc import ABC, abstractmethod

from app.schemas.payment import (
    CheckoutSessionResponse,
    StripeWebhookEvent,
)


class BasePaymentProvider(ABC):
    @abstractmethod
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
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> StripeWebhookEvent:
        pass


class PaymentService:
    def __init__(self, provider: BasePaymentProvider):
        self.provider = provider

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
        return self.provider.create_checkout_session(
            order_id=order_id,
            amount_cents=amount_cents,
            currency=currency,
            product_name=product_name,
            customer_email=customer_email,
            success_url=success_url,
            cancel_url=cancel_url,
        )

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> StripeWebhookEvent:
        return self.provider.verify_webhook_signature(payload, signature)
