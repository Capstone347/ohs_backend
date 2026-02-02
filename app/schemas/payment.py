from pydantic import BaseModel, Field
from enum import Enum


class StripePaymentIntentStatus(Enum):
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    SUCCEEDED = "succeeded"


class PaymentCreate(BaseModel):
    order_id: int = Field(..., gt=0, example=101)
    amount_cents: int = Field(..., ge=0, example=19900)
    currency: str = Field(..., min_length=3, max_length=3, example="CAD")


class PaymentIntentResponse(BaseModel):
    id: str = Field(..., example="pi_1Kxyz123456")
    client_secret: str = Field(..., example="secret_ABC123")
    status: StripePaymentIntentStatus = Field(..., example=StripePaymentIntentStatus.REQUIRES_PAYMENT_METHOD)
