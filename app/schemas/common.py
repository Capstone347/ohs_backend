from datetime import datetime

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = Field(default="healthy")
    version: str = Field(default="1.0.0")
    environment: str
    timestamp: datetime
