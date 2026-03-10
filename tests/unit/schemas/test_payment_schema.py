from app.schemas.payment import (
    CheckoutSessionResponse,
    StripeCheckoutStatus,
    StripeConfigResponse,
    StripeWebhookEvent,
    StripeWebhookEventType,
)


def test_checkout_session_response_valid():
    resp = CheckoutSessionResponse(
        checkout_session_id="cs_test_123",
        checkout_url="https://checkout.stripe.com/pay/cs_test_123",
    )
    assert resp.checkout_session_id == "cs_test_123"
    assert "checkout.stripe.com" in resp.checkout_url


def test_stripe_config_response():
    config = StripeConfigResponse(publishable_key="pk_test_abc")
    assert config.publishable_key == "pk_test_abc"


def test_stripe_webhook_event_checkout_completed():
    event = StripeWebhookEvent(
        event_type=StripeWebhookEventType.CHECKOUT_SESSION_COMPLETED,
        checkout_session_id="cs_test_1",
        payment_intent_id="pi_test_1",
        metadata={"order_id": "42"},
        payment_status="paid",
    )
    assert event.event_type == StripeWebhookEventType.CHECKOUT_SESSION_COMPLETED
    assert event.metadata["order_id"] == "42"


def test_stripe_webhook_event_allows_none_type():
    event = StripeWebhookEvent(
        event_type=None,
        metadata={},
    )
    assert event.event_type is None
    assert event.checkout_session_id is None


def test_stripe_checkout_status_values():
    assert StripeCheckoutStatus.OPEN.value == "open"
    assert StripeCheckoutStatus.COMPLETE.value == "complete"
    assert StripeCheckoutStatus.EXPIRED.value == "expired"
