from pydantic import BaseModel, Field
from enum import Enum


class ErrorCode(Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    COMPANY_NOT_FOUND = "COMPANY_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    INVALID_NAICS_CODE = "INVALID_NAICS_CODE"
    PAYMENT_PROCESSING_ERROR = "PAYMENT_PROCESSING_ERROR"
    DOCUMENT_GENERATION_ERROR = "DOCUMENT_GENERATION_ERROR"
    EMAIL_DELIVERY_ERROR = "EMAIL_DELIVERY_ERROR"
    FILE_STORAGE_ERROR = "FILE_STORAGE_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


class ErrorResponse(BaseModel):
    error: "ErrorDetail"


class ErrorDetail(BaseModel):
    code: ErrorCode = Field(..., example=ErrorCode.VALIDATION_ERROR)
    message: str = Field(..., example="One or more fields failed validation")
    details: dict[str, str] | None = Field(None, example={"company_name": "This field is required"})