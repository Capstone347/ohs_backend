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


class SjpTocEntryStatusResponse(BaseModel):
    toc_entry_id: int = Field(..., example=1)
    title: str = Field(..., example="Working at heights")
    status: str = Field(..., example="completed")
    is_completed: bool = Field(..., example=True)
    generated_at: datetime | None = Field(None, example="2026-04-07T12:10:00Z")
    error_message: str | None = Field(None, example="Model timeout")


class SjpProgressSummaryResponse(BaseModel):
    completed_sjps: int = Field(..., example=5)
    total_sjps: int = Field(..., example=12)
    progress_ratio: float = Field(..., example=0.4167)


class SjpGenerationStatusResponse(BaseModel):
    job_id: int = Field(..., example=10)
    order_id: int = Field(..., example=123)
    status: str = Field(..., example="generating_sjps")
    created_at: datetime = Field(..., example="2026-04-07T12:00:00Z")
    updated_at: datetime = Field(..., example="2026-04-07T12:11:00Z")
    toc_generated_at: datetime | None = Field(None, example="2026-04-07T12:03:00Z")
    completed_at: datetime | None = Field(None, example="2026-04-07T12:20:00Z")
    failed_at: datetime | None = Field(None, example="2026-04-07T12:12:00Z")
    error_message: str | None = Field(None, example="OpenAI upstream error")
    progress: SjpProgressSummaryResponse
    toc_entries: list[SjpTocEntryStatusResponse] = Field(default_factory=list)


class SjpContentSections(BaseModel):
    task_description: str
    required_ppe: list[str]
    step_by_step_instructions: list[str]
    identified_hazards: list[str]
    control_measures: list[str]
    training_requirements: list[str]
    emergency_procedures: str
    legislative_references: str | None = None


class SjpContentResponse(BaseModel):
    toc_entry_id: int
    title: str
    position: int
    status: str
    sections: SjpContentSections | None = None
    generated_at: datetime | None = None
    error_message: str | None = None

    class Config:
        from_attributes = True


class SjpFullContentResponse(BaseModel):
    job_id: int
    order_id: int
    province: str
    naics_codes: list[str]
    status: str
    disclaimer: str
    entries: list[SjpContentResponse] = Field(default_factory=list)


class SjpContentEditRequest(BaseModel):
    task_description: str | None = None
    required_ppe: list[str] | None = None
    step_by_step_instructions: list[str] | None = None
    identified_hazards: list[str] | None = None
    control_measures: list[str] | None = None
    training_requirements: list[str] | None = None
    emergency_procedures: str | None = None
    legislative_references: str | None = None
