from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from app.models.company_logo import CompanyLogo
from app.repositories.base_repository import BaseRepository


class CompanyLogoRepository(BaseRepository[CompanyLogo]):
    def __init__(self, db: Session):
        super().__init__(CompanyLogo, db)

    def get_by_order_id(self, order_id: int) -> list[CompanyLogo]:
        if not order_id:
            raise ValueError("order_id is required")
        
        return (
            self.db.query(CompanyLogo)
            .filter(CompanyLogo.order_id == order_id)
            .order_by(CompanyLogo.uploaded_at.desc())
            .all()
        )

    def get_latest_by_order_id(self, order_id: int) -> CompanyLogo | None:
        if not order_id:
            raise ValueError("order_id is required")
        
        return (
            self.db.query(CompanyLogo)
            .filter(CompanyLogo.order_id == order_id)
            .order_by(CompanyLogo.uploaded_at.desc())
            .first()
        )

    def get_by_id_with_order(self, logo_id: int) -> CompanyLogo | None:
        if not logo_id:
            raise ValueError("logo_id is required")
        
        return (
            self.db.query(CompanyLogo)
            .options(joinedload(CompanyLogo.order))
            .filter(CompanyLogo.id == logo_id)
            .first()
        )

    def create_logo(self, order_id: int, file_path: str) -> CompanyLogo:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not file_path:
            raise ValueError("file_path is required")
        
        logo = CompanyLogo(
            order_id=order_id,
            file_path=file_path,
            uploaded_at=datetime.utcnow()
        )
        return self.create(logo)

    def update_file_path(self, logo_id: int, file_path: str) -> CompanyLogo:
        if not logo_id:
            raise ValueError("logo_id is required")
        
        if not file_path:
            raise ValueError("file_path is required")
        
        logo = self.get_by_id_or_fail(logo_id)
        logo.file_path = file_path
        return self.update(logo)

    def get_recent_uploads(self, limit: int = 50) -> list[CompanyLogo]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        
        return (
            self.db.query(CompanyLogo)
            .options(joinedload(CompanyLogo.order))
            .order_by(CompanyLogo.uploaded_at.desc())
            .limit(limit)
            .all()
        )

    def get_logos_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> list[CompanyLogo]:
        if not start_date:
            raise ValueError("start_date is required")
        
        if not end_date:
            raise ValueError("end_date is required")
        
        if start_date > end_date:
            raise ValueError("start_date must be before end_date")
        
        return (
            self.db.query(CompanyLogo)
            .filter(
                CompanyLogo.uploaded_at >= start_date,
                CompanyLogo.uploaded_at <= end_date
            )
            .order_by(CompanyLogo.uploaded_at.desc())
            .all()
        )

    def count_logos_for_order(self, order_id: int) -> int:
        if not order_id:
            raise ValueError("order_id is required")
        
        return self.db.query(CompanyLogo).filter(CompanyLogo.order_id == order_id).count()

    def delete_logos_by_order_id(self, order_id: int) -> int:
        if not order_id:
            raise ValueError("order_id is required")
        
        deleted_count = (
            self.db.query(CompanyLogo)
            .filter(CompanyLogo.order_id == order_id)
            .delete()
        )
        self.db.commit()
        return deleted_count
