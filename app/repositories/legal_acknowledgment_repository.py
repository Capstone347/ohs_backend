from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload

from app.models.legal_acknowledgment import LegalAcknowledgement
from app.repositories.base_repository import BaseRepository


class LegalAcknowledgmentRepository(BaseRepository[LegalAcknowledgement]):
    def __init__(self, db: Session):
        super().__init__(LegalAcknowledgement, db)

    def get_by_order_id(self, order_id: int) -> LegalAcknowledgement | None:
        if not order_id:
            raise ValueError("order_id is required")
        
        return (
            self.db.query(LegalAcknowledgement)
            .filter(LegalAcknowledgement.order_id == order_id)
            .first()
        )

    def get_by_order_id_or_fail(self, order_id: int) -> LegalAcknowledgement:
        acknowledgment = self.get_by_order_id(order_id)
        if not acknowledgment:
            from app.repositories.base_repository import RecordNotFoundError
            raise RecordNotFoundError(f"Legal acknowledgment for order {order_id} not found")
        return acknowledgment

    def get_by_jurisdiction(self, jurisdiction: str) -> list[LegalAcknowledgement]:
        if not jurisdiction:
            raise ValueError("jurisdiction is required")
        
        return (
            self.db.query(LegalAcknowledgement)
            .filter(LegalAcknowledgement.jurisdiction == jurisdiction)
            .order_by(LegalAcknowledgement.effective_date.desc())
            .all()
        )

    def get_by_order_id_with_order(self, order_id: int) -> LegalAcknowledgement | None:
        if not order_id:
            raise ValueError("order_id is required")
        
        return (
            self.db.query(LegalAcknowledgement)
            .options(joinedload(LegalAcknowledgement.order))
            .filter(LegalAcknowledgement.order_id == order_id)
            .first()
        )

    def create_acknowledgment(
        self,
        order_id: int,
        jurisdiction: str,
        content: str,
        version: int = 1,
        effective_date: datetime | None = None
    ) -> LegalAcknowledgement:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not jurisdiction:
            raise ValueError("jurisdiction is required")
        
        if not content:
            raise ValueError("content is required")
        
        if version < 1:
            raise ValueError("version must be greater than 0")
        
        acknowledgment = LegalAcknowledgement(
            order_id=order_id,
            jurisdiction=jurisdiction,
            content=content,
            version=version,
            effective_date=effective_date or datetime.now(timezone.utc).date()
        )
        
        return self.create(acknowledgment)

    def get_latest_by_jurisdiction_and_version(self, jurisdiction: str, version: int) -> LegalAcknowledgement | None:
        if not jurisdiction:
            raise ValueError("jurisdiction is required")
        
        if not version:
            raise ValueError("version is required")
        
        return (
            self.db.query(LegalAcknowledgement)
            .filter(
                LegalAcknowledgement.jurisdiction == jurisdiction,
                LegalAcknowledgement.version == version
            )
            .order_by(LegalAcknowledgement.effective_date.desc())
            .first()
        )
