from pydantic import BaseModel, Field, field_validator
from typing import List
import re


NAICS_REGEX = r"^\d{6}$"


class CompanyBase(BaseModel):
    company_name: str = Field(..., min_length=1, example="Acme Safety Inc.")
    province: str = Field(..., min_length=2, max_length=50, example="Ontario")
    naics_codes: list[str] = Field(..., min_items=1, example=["123456"])
    
    @field_validator("naics_codes")
    @classmethod
    def validate_naics(cls, v: list[str]) -> list[str]:
        for code in v:
            if not re.match(NAICS_REGEX, code):
                raise ValueError("NAICS codes must be exactly 6 digits")
        return v

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    id: int = Field(..., example=42)
    
    class Config:
        from_attributes = True