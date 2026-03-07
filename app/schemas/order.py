from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from decimal import Decimal
import re

from app.models.order_status import OrderStatusEnum, PaymentStatus

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
NAICS_REGEX = r"^\d{6}$"


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


class OrderCreateRequest(BaseModel):
    plan_id: int = Field(..., gt=0, example=1)
    user_email: str = Field(..., example="customer@example.com")
    full_name: str = Field(..., min_length=1, example="John Doe")
    jurisdiction: str = Field(..., min_length=2, max_length=100, example="Ontario")

    @field_validator("user_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(EMAIL_REGEX, v):
            raise ValueError("invalid email format")
        return v


class OrderCreatedResponse(BaseModel):
    order_id: int = Field(..., example=1)
    status: OrderStatusEnum = Field(..., example=OrderStatusEnum.DRAFT)
    created_at: datetime
    message: str = Field(..., example="Order created successfully")


class CompanyDetailsResponse(BaseModel):
    id: int = Field(..., example=42)
    name: str = Field(..., example="Acme Safety Inc.")
    logo_id: int | None = Field(None, example=1)


class DocumentSummary(BaseModel):
    document_id: int = Field(..., example=7)
    access_token: str = Field(..., example="a1b2c3d4e5f6...")
    token_expires_at: datetime = Field(..., example="2026-03-02T12:00:00Z")
    generated_at: datetime = Field(..., example="2026-02-02T12:00:00Z")
    file_format: str = Field(..., example="docx")

    class Config:
        from_attributes = True


class OrderSummaryResponse(BaseModel):
    order_id: int = Field(..., example=1)
    user_email: str = Field(..., example="customer@example.com")
    full_name: str = Field(..., example="John Doe")
    company: CompanyDetailsResponse | None = None
    plan_name: str | None = Field(None, example="Basic Plan")
    jurisdiction: str = Field(..., example="Ontario")
    total_amount: Decimal = Field(..., example=Decimal("199.99"))
    order_status: OrderStatusEnum = Field(..., example=OrderStatusEnum.DRAFT)
    payment_status: PaymentStatus = Field(..., example=PaymentStatus.PENDING)
    created_at: datetime
    completed_at: datetime | None = None
    is_industry_specific: bool = Field(..., example=False)
    documents: list[DocumentSummary] = Field(default_factory=list)
    
    class Config:
        from_attributes = True
