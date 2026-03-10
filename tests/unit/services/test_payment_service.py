import pytest

from app.schemas.payment import CheckoutSessionResponse, StripeWebhookEvent, StripeWebhookEventType
from app.services.payment_service import BasePaymentProvider, PaymentService


class FakePaymentProvider(BasePaymentProvider):
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
        if amount_cents <= 0:
            raise ValueError("amount_cents must be greater than zero")
        return CheckoutSessionResponse(
            checkout_session_id=f"cs_test_{order_id}",
            checkout_url=f"https://checkout.stripe.com/pay/cs_test_{order_id}",
        )

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> StripeWebhookEvent:
        return StripeWebhookEvent(
            event_type=StripeWebhookEventType.CHECKOUT_SESSION_COMPLETED,
            checkout_session_id="cs_test_1",
            payment_intent_id="pi_test_1",
            metadata={"order_id": "1"},
            payment_status="paid",
        )


def test_payment_service_create_checkout_session_success():
    svc = PaymentService(provider=FakePaymentProvider())
    result = svc.create_checkout_session(
        order_id=5,
        amount_cents=1000,
        currency="CAD",
        product_name="OHS Manual",
        customer_email="test@example.com",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )
    assert isinstance(result, CheckoutSessionResponse)
    assert result.checkout_session_id == "cs_test_5"
    assert "checkout.stripe.com" in result.checkout_url


def test_payment_service_negative_or_zero_amount_raises():
    svc = PaymentService(provider=FakePaymentProvider())
    with pytest.raises(ValueError):
        svc.create_checkout_session(
            order_id=1,
            amount_cents=0,
            currency="CAD",
            product_name="OHS Manual",
            customer_email="test@example.com",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )


def test_payment_service_verify_webhook():
    svc = PaymentService(provider=FakePaymentProvider())
    event = svc.verify_webhook_signature(b"payload", "sig")
    assert isinstance(event, StripeWebhookEvent)
    assert event.event_type == StripeWebhookEventType.CHECKOUT_SESSION_COMPLETED
    assert event.checkout_session_id == "cs_test_1"
