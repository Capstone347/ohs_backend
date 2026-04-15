from sqlalchemy.orm import Session

from app.models.sjp_generation_job import SjpGenerationJob
from app.repositories.base_repository import BaseRepository


class SjpGenerationJobRepository(BaseRepository[SjpGenerationJob]):
    def __init__(self, db: Session):
        super().__init__(SjpGenerationJob, db)

    def get_by_order_id(self, order_id: int) -> list[SjpGenerationJob]:
        if not order_id:
            raise ValueError("order_id is required")

        return (
            self.db.query(SjpGenerationJob)
            .filter(SjpGenerationJob.order_id == order_id)
            .order_by(SjpGenerationJob.created_at.desc())
            .all()
        )

    def get_all_by_statuses(self, statuses: list[str]) -> list[SjpGenerationJob]:
        return (
            self.db.query(SjpGenerationJob)
            .filter(SjpGenerationJob.status.in_(statuses))
            .order_by(SjpGenerationJob.created_at.desc())
            .all()
        )

    def get_by_idempotency_key(self, idempotency_key: str) -> SjpGenerationJob | None:
        if not idempotency_key:
            raise ValueError("idempotency_key is required")

        return (
            self.db.query(SjpGenerationJob)
            .filter(SjpGenerationJob.idempotency_key == idempotency_key)
            .first()
        )
