from pydantic import BaseModel, Field
from enum import Enum


class StripePaymentIntentStatus(Enum):
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    SUCCEEDED = "succeeded"


class StripeWebhookEventType(Enum):
    PAYMENT_INTENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_INTENT_FAILED = "payment_intent.failed"
    PAYMENT_INTENT_CANCELED = "payment_intent.canceled"


class PaymentCreate(BaseModel):
    order_id: int = Field(..., gt=0, example=101)
    amount_cents: int = Field(..., ge=0, example=19900)
    currency: str = Field(..., min_length=3, max_length=3, example="CAD")


class PaymentIntentResponse(BaseModel):
    id: str = Field(..., example="pi_1Kxyz123456")
    client_secret: str = Field(..., example="secret_ABC123")
    status: StripePaymentIntentStatus = Field(..., example=StripePaymentIntentStatus.REQUIRES_PAYMENT_METHOD)
    amount_cents: int = Field(..., ge=0, example=19900)
    currency: str = Field(..., min_length=3, max_length=3, example="CAD")


class StripeWebhookEvent(BaseModel):
    event_type: StripeWebhookEventType = Field(..., example=StripeWebhookEventType.PAYMENT_INTENT_SUCCEEDED)
    payment_intent_id: str = Field(..., example="pi_1Kxyz123456")
    metadata: dict[str, str] = Field(default_factory=dict, example={"order_id": "101"})
