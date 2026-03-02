from sqlalchemy.orm import Session

from app.models.industry_intake_response import IndustryIntakeResponse
from app.repositories.base_repository import BaseRepository, RecordNotFoundError


class IndustryIntakeResponseRepository(BaseRepository[IndustryIntakeResponse]):
    def __init__(self, db: Session):
        super().__init__(IndustryIntakeResponse, db)

    def get_by_order_id(self, order_id: int) -> IndustryIntakeResponse | None:
        if not order_id:
            raise ValueError("order_id is required")

        return (
            self.db.query(IndustryIntakeResponse)
            .filter(IndustryIntakeResponse.order_id == order_id)
            .first()
        )

    def get_by_order_id_or_fail(self, order_id: int) -> IndustryIntakeResponse:
        record = self.get_by_order_id(order_id)
        if not record:
            raise RecordNotFoundError(
                f"IndustryIntakeResponse for order {order_id} not found"
            )
        return record

    def upsert(self, order_id: int, answers: dict) -> IndustryIntakeResponse:
        if not order_id:
            raise ValueError("order_id is required")

        if answers is None:
            raise ValueError("answers is required")

        existing = self.get_by_order_id(order_id)

        if existing:
            existing.answers = answers
            return self.update(existing)

        record = IndustryIntakeResponse(order_id=order_id, answers=answers)
        return self.create(record)
