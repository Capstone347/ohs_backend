from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from app.models.document import Document, DocumentFormat
from app.repositories.base_repository import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: Session):
        super().__init__(Document, db)

    def get_by_id(self, document_id: int) -> Document | None:
        if not document_id:
            raise ValueError("document_id is required")
        
        return self.db.query(Document).filter(Document.document_id == document_id).first()

    def get_by_id_or_fail(self, document_id: int) -> Document:
        document = self.get_by_id(document_id)
        if not document:
            from app.repositories.base_repository import RecordNotFoundError
            raise RecordNotFoundError(f"Document with id {document_id} not found")
        return document

    def get_by_access_token(self, access_token: str) -> Document | None:
        if not access_token:
            raise ValueError("access_token is required")
        
        return self.db.query(Document).filter(Document.access_token == access_token).first()

    def get_by_access_token_or_fail(self, access_token: str) -> Document:
        document = self.get_by_access_token(access_token)
        if not document:
            from app.repositories.base_repository import RecordNotFoundError
            raise RecordNotFoundError(f"Document with access token not found")
        return document

    def get_documents_by_order_id(self, order_id: int) -> list[Document]:
        if not order_id:
            raise ValueError("order_id is required")
        
        return (
            self.db.query(Document)
            .filter(Document.order_id == order_id)
            .order_by(Document.generated_at.desc())
            .all()
        )

    def get_by_id_with_order(self, document_id: int) -> Document | None:
        if not document_id:
            raise ValueError("document_id is required")
        
        return (
            self.db.query(Document)
            .options(joinedload(Document.order))
            .filter(Document.document_id == document_id)
            .first()
        )

    def create_document(
        self,
        order_id: int,
        access_token: str,
        token_expires_at: datetime,
        file_path: str | None = None,
        file_format: DocumentFormat = DocumentFormat.DOCX,
        content: dict | None = None
    ) -> Document:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not access_token:
            raise ValueError("access_token is required")
        
        if not token_expires_at:
            raise ValueError("token_expires_at is required")
        
        document = Document(
            order_id=order_id,
            access_token=access_token,
            token_expires_at=token_expires_at,
            file_path=file_path,
            file_format=file_format,
            content=content,
            generated_at=datetime.utcnow()
        )
        return self.create(document)

    def increment_download_count(self, document_id: int) -> Document:
        if not document_id:
            raise ValueError("document_id is required")
        
        document = self.get_by_id_or_fail(document_id)
        document.downloaded_count += 1
        document.last_downloaded_at = datetime.utcnow()
        return self.update(document)

    def update_file_path(self, document_id: int, file_path: str) -> Document:
        if not document_id:
            raise ValueError("document_id is required")
        
        if not file_path:
            raise ValueError("file_path is required")
        
        document = self.get_by_id_or_fail(document_id)
        document.file_path = file_path
        return self.update(document)

    def update_content(self, document_id: int, content: dict) -> Document:
        if not document_id:
            raise ValueError("document_id is required")
        
        if not content:
            raise ValueError("content is required")
        
        document = self.get_by_id_or_fail(document_id)
        document.content = content
        return self.update(document)

    def is_token_valid(self, access_token: str) -> bool:
        if not access_token:
            raise ValueError("access_token is required")
        
        document = self.get_by_access_token(access_token)
        
        if not document:
            return False
        
        if datetime.utcnow() > document.token_expires_at:
            return False
        
        return True

    def get_expired_documents(self) -> list[Document]:
        return (
            self.db.query(Document)
            .filter(Document.token_expires_at < datetime.utcnow())
            .all()
        )

    def get_documents_by_format(self, file_format: DocumentFormat) -> list[Document]:
        if not file_format:
            raise ValueError("file_format is required")
        
        return (
            self.db.query(Document)
            .filter(Document.file_format == file_format)
            .order_by(Document.generated_at.desc())
            .all()
        )

    def get_recently_generated_documents(self, limit: int = 50) -> list[Document]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        
        return (
            self.db.query(Document)
            .options(joinedload(Document.order))
            .order_by(Document.generated_at.desc())
            .limit(limit)
            .all()
        )

    def get_most_downloaded_documents(self, limit: int = 50) -> list[Document]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        
        return (
            self.db.query(Document)
            .options(joinedload(Document.order))
            .filter(Document.downloaded_count > 0)
            .order_by(Document.downloaded_count.desc())
            .limit(limit)
            .all()
        )

    def delete_by_id(self, document_id: int) -> None:
        if not document_id:
            raise ValueError("document_id is required")
        
        document = self.get_by_id_or_fail(document_id)
        self.db.delete(document)
        self.db.commit()
