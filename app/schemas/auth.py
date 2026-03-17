import re

from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RequestOtpRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_email = value.strip().lower()
        if not re.match(EMAIL_REGEX, normalized_email):
            raise ValueError("invalid email format")
        return normalized_email


class RequestOtpResponse(BaseModel):
    message: str = Field(default="If the email is registered, an OTP has been sent.")

