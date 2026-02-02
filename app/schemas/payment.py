from pydantic import BaseModel, Field
from typing import Literal


class PaymentCreate(BaseModel):
    order_id: int = Field(..., gt=0, example=101)
    amount_cents: int = Field(..., ge=0, example=19900)
    currency: str = Field(..., min_length=3, max_length=3, example="CAD")


class PaymentIntentResponse(BaseModel):
    id: str = Field(..., example="pi_1Kxyz123456")
    client_secret: str = Field(..., example="secret_ABC123")
    status: Literal["requires_payment_method", "requires_confirmation", "succeeded"] = Field(..., example="requires_payment_method")
