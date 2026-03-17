from pydantic import BaseModel, Field


class OrderConfirmationContext(BaseModel):
    order_id: int = Field(..., gt=0)
    company_name: str = Field(..., min_length=1)
    plan_name: str = Field(..., min_length=1)
    total_amount: str = Field(..., min_length=1)
    created_at: str = Field(..., min_length=1)
    user_email: str = Field(..., min_length=1)


class DocumentDeliveryContext(BaseModel):
    order_id: int = Field(..., gt=0)
    company_name: str = Field(..., min_length=1)
    download_link: str = Field(..., min_length=1)
    document_name: str = Field(..., min_length=1)


class AuthOtpContext(BaseModel):
    otp_code: str = Field(..., min_length=6, max_length=8)
    expires_in_minutes: int = Field(..., gt=0)
    recipient_email: str = Field(..., min_length=3)

