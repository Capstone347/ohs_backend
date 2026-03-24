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


class VerifyOtpRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    otp: str = Field(..., min_length=6, max_length=8)

    @field_validator("email")
    @classmethod
    def validate_verify_email(cls, value: str) -> str:
        normalized_email = value.strip().lower()
        if not re.match(EMAIL_REGEX, normalized_email):
            raise ValueError("invalid email format")
        return normalized_email

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        normalized_otp = value.strip()
        if not normalized_otp:
            raise ValueError("otp is required")
        return normalized_otp


class AuthenticatedUserResponse(BaseModel):
    id: int = Field(..., gt=0)
    email: str = Field(..., min_length=3)
    full_name: str = Field(..., min_length=1)


class VerifyOtpResponse(BaseModel):
    user: AuthenticatedUserResponse


