from pydantic import BaseModel, Field


class JurisdictionPromptPack(BaseModel):
    province_code: str = Field(..., min_length=2, max_length=3)
    province_name: str = Field(..., min_length=1)
    legislation_name: str = Field(..., min_length=1)
    regulatory_body: str = Field(..., min_length=1)
    key_regulations: list[str] = Field(..., min_length=1)
    terminology_notes: str = Field(..., min_length=1)
    prompt_preamble: str = Field(..., min_length=1)
    is_generic: bool = Field(default=False)

