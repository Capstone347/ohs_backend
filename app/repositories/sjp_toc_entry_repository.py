from sqlalchemy.orm import Session

from app.models.sjp_toc_entry import SjpTocEntry
from app.repositories.base_repository import BaseRepository


class SjpTocEntryRepository(BaseRepository[SjpTocEntry]):
    def __init__(self, db: Session):
        super().__init__(SjpTocEntry, db)

    def get_by_job_id(self, job_id: int) -> list[SjpTocEntry]:
        if not job_id:
            raise ValueError("job_id is required")

        return (
            self.db.query(SjpTocEntry)
            .filter(SjpTocEntry.job_id == job_id)
            .order_by(SjpTocEntry.position.asc())
            .all()
        )

