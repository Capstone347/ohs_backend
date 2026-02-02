from pydantic import BaseModel, Field
from datetime import datetime


class LegalAcknowledgment(BaseModel):
    user_id: int = Field(..., example=7)
    accepted: bool = Field(..., example=True)
    accepted_at: datetime | None = Field(None, example="2026-02-02T12:34:56Z")
