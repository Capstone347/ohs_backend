from pydantic import BaseModel, Field
from datetime import datetime, date


class LegalDisclaimerRequest(BaseModel):
    plan_id: int = Field(..., gt=0, example=1)
    jurisdiction: str = Field(..., min_length=2, max_length=2, example="ON")


class LegalDisclaimerResponse(BaseModel):
    plan_id: int = Field(..., example=1)
    jurisdiction: str = Field(..., example="ON")
    content: str = Field(..., min_length=1, example="This is the legal disclaimer content...")
    version: int = Field(..., example=1)


class LegalAcknowledgmentRequest(BaseModel):
    jurisdiction: str = Field(..., min_length=2, max_length=2, example="ON")
    content: str = Field(..., min_length=1, example="I acknowledge that I have read...")
    version: int = Field(default=1, example=1)


class LegalAcknowledgmentResponse(BaseModel):
    id: int = Field(..., example=7)
    order_id: int = Field(..., example=101)
    jurisdiction: str = Field(..., example="ON")
    version: int = Field(..., example=1)
    effective_date: date = Field(..., example="2026-02-02")
    acknowledged_at: datetime = Field(..., example="2026-02-02T12:34:56Z")

    class Config:
        from_attributes = True
