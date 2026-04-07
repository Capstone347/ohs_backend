from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class SjpGenerationStartRequest(BaseModel):
    """Request to initiate SJP generation for an order."""
    idempotency_key: str | None = Field(
        default_factory=lambda: str(uuid4()),
        example="550e8400-e29b-41d4-a716-446655440000",
        description="Unique key for idempotent request handling. Auto-generated if omitted."
    )


class SjpGenerationJobResponse(BaseModel):
    """Response containing details of a created/retrieved SJP generation job."""
    job_id: int = Field(..., example=1, description="Unique identifier for the generation job")
    status: str = Field(..., example="pending", description="Current status of the job")
    created_at: datetime = Field(..., example="2026-02-02T12:00:00Z", description="Job creation timestamp")

    class Config:
        from_attributes = True
