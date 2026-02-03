from pydantic import BaseModel, Field
from datetime import datetime


class DocumentResponse(BaseModel):
    document_id: int = Field(..., example=7)
    order_id: int = Field(..., example=101)
    file_path: str = Field(..., min_length=1, example="/data/documents/ohs_manual_order_101.docx")
    file_format: str = Field(..., example="docx")
    access_token: str = Field(..., example="a1b2c3d4e5f6...")
    token_expires_at: datetime = Field(..., example="2026-03-02T12:00:00Z")
    generated_at: datetime = Field(..., example="2026-02-02T12:00:00Z")

    class Config:
        from_attributes = True


class DocumentGenerateRequest(BaseModel):
    order_id: int = Field(..., gt=0, example=101)


class DocumentGenerateResponse(BaseModel):
    document_id: int = Field(..., example=7)
    order_id: int = Field(..., example=101)
    message: str = Field(..., example="Document generated successfully")
    generated_at: datetime = Field(..., example="2026-02-02T12:00:00Z")


class DocumentDownloadRequest(BaseModel):
    access_token: str = Field(..., min_length=1, example="a1b2c3d4e5f6...")


class DocumentPreviewResponse(BaseModel):
    document_id: int = Field(..., example=7)
    preview_available: bool = Field(..., example=True)
    message: str = Field(..., example="Preview generated successfully")
