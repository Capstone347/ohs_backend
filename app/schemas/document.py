from pydantic import BaseModel, Field
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int = Field(..., example=7)
    order_id: int = Field(..., example=101)
    filename: str = Field(..., min_length=1, example="ohs_manual_order_101.docx")
    mime_type: str = Field(..., min_length=3, example="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    path: str = Field(..., min_length=1, example="/data/documents/ohs_manual_order_101.docx")
    created_at: datetime = Field(..., example="2026-02-02T12:00:00Z")

    class Config:
        from_attributes = True
