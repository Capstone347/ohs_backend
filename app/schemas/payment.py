from pydantic import BaseModel, Field
from enum import Enum


class StripeCheckoutStatus(Enum):
    OPEN = "open"
    COMPLETE = "complete"
    EXPIRED = "expired"


class StripeWebhookEventType(Enum):
    CHECKOUT_SESSION_COMPLETED = "checkout.session.completed"
    CHECKOUT_SESSION_EXPIRED = "checkout.session.expired"
    PAYMENT_INTENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_INTENT_FAILED = "payment_intent.payment_failed"


class CheckoutSessionResponse(BaseModel):
    checkout_session_id: str = Field(..., example="cs_test_abc123")
    checkout_url: str = Field(..., example="https://checkout.stripe.com/c/pay/cs_test_abc123")


class StripeConfigResponse(BaseModel):
    publishable_key: str = Field(..., example="pk_test_abc123")


class StripeWebhookEvent(BaseModel):
    event_type: StripeWebhookEventType | None = None
    checkout_session_id: str | None = None
    payment_intent_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    payment_status: str | None = None
