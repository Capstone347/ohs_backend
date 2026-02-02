from pydantic import BaseModel, Field, validator
from typing import List
import re


NAICS_REGEX = r"^\d{6}$"


class CompanyBase(BaseModel):
    company_name: str = Field(..., min_length=1, example="Acme Safety Inc.")
    province: str = Field(..., min_length=2, max_length=50, example="Ontario")
    naics_codes: List[str] = Field(..., min_items=1, example=["123456"])

    @validator("naics_codes", each_item=True)
    def validate_naics(cls, v: str) -> str:
        if not re.match(NAICS_REGEX, v):
            raise ValueError("NAICS codes must be exactly 6 digits")
        return v


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: int = Field(..., example=42)

    class Config:
        orm_mode = True
