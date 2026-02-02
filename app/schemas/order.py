from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re

from app.models.order_status import OrderStatusEnum

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class OrderBase(BaseModel):
    plan_id: str = Field(..., min_length=1, example="basic")
    user_email: str = Field(..., example="customer@example.com")

    @field_validator("user_email")
    def validate_email(cls, v: str) -> str:
        if not re.match(EMAIL_REGEX, v):
            raise ValueError("invalid email format")
        return v


class OrderCreate(OrderBase):
    company_id: int = Field(..., gt=0, example=42)


class OrderResponse(OrderBase):
    id: int = Field(..., example=101)
    status: OrderStatusEnum = Field(..., example=OrderStatusEnum.DRAFT)
    created_at: datetime

    class Config:
        from_attributes = True
