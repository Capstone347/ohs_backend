from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.llm_usage_log import LlmUsageLog
from app.repositories.base_repository import BaseRepository


class LlmUsageLogRepository(BaseRepository[LlmUsageLog]):
    def __init__(self, db: Session):
        super().__init__(LlmUsageLog, db)

    def get_by_job_id(self, job_id: int) -> list[LlmUsageLog]:
        if not job_id:
            raise ValueError("job_id is required")

        return (
            self.db.query(LlmUsageLog)
            .filter(LlmUsageLog.job_id == job_id)
            .order_by(LlmUsageLog.created_at.asc())
            .all()
        )

    def get_total_cost_by_job(self, job_id: int) -> Decimal:
        if not job_id:
            raise ValueError("job_id is required")

        result = (
            self.db.query(func.sum(LlmUsageLog.estimated_cost_usd))
            .filter(LlmUsageLog.job_id == job_id)
            .scalar()
        )
        return result if result is not None else Decimal("0")

