from app.services.payment_service import PaymentService
from app.schemas.payment import PaymentIntentResponse, StripeWebhookEvent
import pytest


def test_payment_service_create_payment_intent_success():
    svc = PaymentService()
    result = svc.create_payment_intent(order_id=5, amount_cents=1000)
    assert isinstance(result, PaymentIntentResponse)
    assert result.id == "pi_mock_5"
    assert result.client_secret == "cs_mock_5"
    assert result.status.value == "succeeded"


def test_payment_service_negative_or_zero_amount_raises():
    svc = PaymentService()
    with pytest.raises(ValueError):
        svc.create_payment_intent(order_id=1, amount_cents=0)

    with pytest.raises(ValueError):
        svc.create_payment_intent(order_id=1, amount_cents=-100)


def test_payment_service_currency_and_webhook():
    svc = PaymentService()
    result = svc.create_payment_intent(order_id=7, amount_cents=2500, currency="usd")
    assert result.currency == "usd"

    event = svc.verify_webhook_signature(b"payload", "sig")
    assert isinstance(event, StripeWebhookEvent)
    assert event.event_type.value == "payment_intent.succeeded"
    assert event.payment_intent_id == "pi_mock"
