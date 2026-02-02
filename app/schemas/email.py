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
