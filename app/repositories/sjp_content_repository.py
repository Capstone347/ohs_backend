from sqlalchemy.orm import Session

from app.models.sjp_content import SjpContent
from app.repositories.base_repository import BaseRepository


class SjpContentRepository(BaseRepository[SjpContent]):
    def __init__(self, db: Session):
        super().__init__(SjpContent, db)

    def get_by_toc_entry_id(self, toc_entry_id: int) -> SjpContent | None:
        if not toc_entry_id:
            raise ValueError("toc_entry_id is required")

        return (
            self.db.query(SjpContent)
            .filter(SjpContent.toc_entry_id == toc_entry_id)
            .first()
        )

    def get_by_toc_entry_ids(self, toc_entry_ids: list[int]) -> list[SjpContent]:
        if not toc_entry_ids:
            raise ValueError("toc_entry_ids is required and must not be empty")

        return (
            self.db.query(SjpContent)
            .filter(SjpContent.toc_entry_id.in_(toc_entry_ids))
            .all()
        )

