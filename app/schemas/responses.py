from pydantic import BaseModel, Field
from typing import Any, Optional


class ErrorResponse(BaseModel):
    code: str = Field(..., example="VALIDATION_ERROR")
    message: str = Field(..., example="One or more fields failed validation")
    details: Optional[Any] = Field(None, example={"company_name": "required"})


class SuccessResponse(BaseModel):
    ok: bool = Field(True, example=True)
    data: Optional[Any] = Field(None)
