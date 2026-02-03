import sys
import types
import pytest

from app.services.stripe_provider import StripePaymentProvider
from app.schemas.payment import StripeWebhookEventType


def make_fake_stripe_module(create_return=None, construct_return=None):
    module = types.ModuleType("stripe")

    class PaymentIntent:
        @staticmethod
        def create(*args, **kwargs):
            return create_return

    class Webhook:
        @staticmethod
        def construct_event(payload, signature, secret):
            return construct_return

    module.PaymentIntent = PaymentIntent
    module.Webhook = Webhook
    return module


def make_fake_stripe_module_object_response():
    module = types.ModuleType("stripe")

    class IntentObject:
        def __init__(self):
            self.id = "pi_obj_1"
            self.client_secret = "cs_obj_1"
            self.status = "succeeded"
            self.amount = 2000
            self.currency = "cad"

    class PaymentIntent:
        @staticmethod
        def create(*args, **kwargs):
            return IntentObject()

    class Webhook:
        @staticmethod
        def construct_event(payload, signature, secret):
            return {"type": "payment_intent.succeeded", "data": {"object": {"id": "pi_obj_1"}}}

    module.PaymentIntent = PaymentIntent
    module.Webhook = Webhook
    return module


def make_fake_stripe_module_raising():
    module = types.ModuleType("stripe")

    class PaymentIntent:
        @staticmethod
        def create(*args, **kwargs):
            return {"id": "pi_123", "client_secret": "cs_123", "status": "requires_payment_method", "amount": 1500, "currency": "cad"}

    class Webhook:
        @staticmethod
        def construct_event(payload, signature, secret):
            raise Exception("invalid signature")

    module.PaymentIntent = PaymentIntent
    module.Webhook = Webhook
    return module


def test_stripe_provider_create_payment_intent(monkeypatch):
    fake_intent = {"id": "pi_123", "client_secret": "cs_123", "status": "requires_payment_method", "amount": 1500, "currency": "cad"}
    fake_stripe = make_fake_stripe_module(create_return=fake_intent)
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe)

    provider = StripePaymentProvider(api_key="sk_test", webhook_secret="whsec_test")
    result = provider.create_payment_intent(order_id=1, amount_cents=1500, currency="cad")

    assert result["id"] == "pi_123"
    assert result["client_secret"] == "cs_123"
    assert result["status"] == "requires_payment_method"
    assert result["amount_cents"] == 1500


def test_stripe_provider_verify_webhook(monkeypatch):
    fake_event = {"type": "payment_intent.succeeded", "data": {"object": {"id": "pi_123"}}}
    fake_stripe = make_fake_stripe_module(construct_return=fake_event)
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe)

    provider = StripePaymentProvider(api_key="sk_test", webhook_secret="whsec_test")
    event = provider.verify_webhook_signature(b"payload", "sig")

    assert event.event_type == StripeWebhookEventType.PAYMENT_INTENT_SUCCEEDED
    assert event.payment_intent_id == "pi_123"


def test_stripe_provider_handles_sdk_object_response(monkeypatch):
    fake_stripe = make_fake_stripe_module_object_response()
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe)

    provider = StripePaymentProvider(api_key="sk_test", webhook_secret="whsec_test")
    result = provider.create_payment_intent(order_id=2, amount_cents=2000, currency="cad")

    assert result["id"] == "pi_obj_1"
    assert result["client_secret"] == "cs_obj_1"
    assert result["status"] == "succeeded"
    assert result["amount_cents"] == 2000


def test_stripe_provider_raises_on_signature_verification_failure(monkeypatch):
    fake_stripe = make_fake_stripe_module_raising()
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe)

    provider = StripePaymentProvider(api_key="sk_test", webhook_secret="whsec_test")

    with pytest.raises(Exception):
        provider.verify_webhook_signature(b"payload", "sig")