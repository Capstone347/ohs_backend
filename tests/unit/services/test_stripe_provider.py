import types

import pytest

from app.schemas.payment import StripeWebhookEventType
from app.services.stripe_provider import StripePaymentProvider


def _make_fake_stripe(session_return=None, construct_return=None, raise_on_construct=False):
    module = types.ModuleType("stripe")

    class StripeError(Exception):
        pass

    class SignatureVerificationError(StripeError):
        pass

    class FakeSession:
        @staticmethod
        def create(**kwargs):
            return session_return

    class FakeCheckout:
        Session = FakeSession

    class Webhook:
        @staticmethod
        def construct_event(payload, signature, secret):
            if raise_on_construct:
                raise SignatureVerificationError("bad sig")
            return construct_return

    module.checkout = FakeCheckout()
    module.StripeError = StripeError
    module.SignatureVerificationError = SignatureVerificationError
    module.Webhook = Webhook
    module.api_key = None
    return module


def test_stripe_provider_create_checkout_session(monkeypatch):
    fake_session = types.SimpleNamespace(
        id="cs_test_123",
        url="https://checkout.stripe.com/pay/cs_test_123",
    )
    fake_stripe = _make_fake_stripe(session_return=fake_session)
    monkeypatch.setattr("app.services.stripe_provider._stripe", fake_stripe)

    provider = StripePaymentProvider.__new__(StripePaymentProvider)
    provider.api_key = "sk_test"
    provider.webhook_secret = "whsec_test"

    result = provider.create_checkout_session(
        order_id=1,
        amount_cents=1500,
        currency="cad",
        product_name="OHS Manual - Basic",
        customer_email="user@example.com",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )

    assert result.checkout_session_id == "cs_test_123"
    assert result.checkout_url == "https://checkout.stripe.com/pay/cs_test_123"


def test_stripe_provider_verify_webhook(monkeypatch):
    fake_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_456",
                "payment_intent": "pi_test_789",
                "payment_status": "paid",
                "metadata": {"order_id": "42"},
            }
        },
    }
    fake_stripe = _make_fake_stripe(construct_return=fake_event)
    monkeypatch.setattr("app.services.stripe_provider._stripe", fake_stripe)

    provider = StripePaymentProvider.__new__(StripePaymentProvider)
    provider.api_key = "sk_test"
    provider.webhook_secret = "whsec_test"

    event = provider.verify_webhook_signature(b"payload", "sig")

    assert event.event_type == StripeWebhookEventType.CHECKOUT_SESSION_COMPLETED
    assert event.checkout_session_id == "cs_test_456"
    assert event.payment_intent_id == "pi_test_789"
    assert event.metadata == {"order_id": "42"}


def test_stripe_provider_raises_on_signature_failure(monkeypatch):
    fake_stripe = _make_fake_stripe(raise_on_construct=True)
    monkeypatch.setattr("app.services.stripe_provider._stripe", fake_stripe)

    provider = StripePaymentProvider.__new__(StripePaymentProvider)
    provider.api_key = "sk_test"
    provider.webhook_secret = "whsec_test"

    with pytest.raises(ValueError, match="invalid webhook signature"):
        provider.verify_webhook_signature(b"payload", "sig")


def test_stripe_provider_handles_payment_intent_event(monkeypatch):
    fake_event = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_001",
                "status": "succeeded",
                "metadata": {"order_id": "10"},
            }
        },
    }
    fake_stripe = _make_fake_stripe(construct_return=fake_event)
    monkeypatch.setattr("app.services.stripe_provider._stripe", fake_stripe)

    provider = StripePaymentProvider.__new__(StripePaymentProvider)
    provider.api_key = "sk_test"
    provider.webhook_secret = "whsec_test"

    event = provider.verify_webhook_signature(b"payload", "sig")

    assert event.event_type == StripeWebhookEventType.PAYMENT_INTENT_SUCCEEDED
    assert event.payment_intent_id == "pi_test_001"
    assert event.payment_status == "succeeded"