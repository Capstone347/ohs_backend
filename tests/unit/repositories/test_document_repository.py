import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.document import Document, DocumentFormat
from app.models.order import Order
from app.models.user import User, UserRole
from app.models.company import Company
from app.repositories.document_repository import DocumentRepository
from app.repositories.base_repository import RecordNotFoundError


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def document_repo(test_db):
    return DocumentRepository(test_db)


@pytest.fixture
def sample_order(test_db):
    user = User(
        email="test@example.com",
        full_name="Test User",
        role=UserRole.CUSTOMER,
        created_at=datetime.now(timezone.utc)
    )
    test_db.add(user)
    test_db.commit()
    
    company = Company(name="Test Company")
    test_db.add(company)
    test_db.commit()
    
    order = Order(
        user_id=user.id,
        company_id=company.id,
        jurisdiction="Ontario",
        total_amount=100.00,
        created_at=datetime.now(timezone.utc)
    )
    test_db.add(order)
    test_db.commit()
    test_db.refresh(order)
    return order


class TestDocumentRepository:
    def test_create_document(self, document_repo, sample_order):
        token_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        document = document_repo.create_document(
            order_id=sample_order.id,
            access_token="test_token_123",
            token_expires_at=token_expires,
            file_path="/path/to/document.docx",
            file_format=DocumentFormat.DOCX
        )
        
        assert document.document_id is not None
        assert document.order_id == sample_order.id
        assert document.access_token == "test_token_123"
        assert document.token_expires_at == token_expires
        assert document.file_path == "/path/to/document.docx"
        assert document.file_format == DocumentFormat.DOCX

    def test_get_by_access_token(self, document_repo, sample_order):
        token_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        created_doc = document_repo.create_document(
            order_id=sample_order.id,
            access_token="unique_token",
            token_expires_at=token_expires
        )
        
        retrieved_doc = document_repo.get_by_access_token("unique_token")
        
        assert retrieved_doc is not None
        assert retrieved_doc.document_id == created_doc.document_id
        assert retrieved_doc.access_token == "unique_token"

    def test_get_by_access_token_not_found_returns_none(self, document_repo):
        result = document_repo.get_by_access_token("nonexistent")
        assert result is None

    def test_get_documents_by_order_id(self, document_repo, sample_order):
        token_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        document_repo.create_document(
            order_id=sample_order.id,
            access_token="token_1",
            token_expires_at=token_expires
        )
        document_repo.create_document(
            order_id=sample_order.id,
            access_token="token_2",
            token_expires_at=token_expires
        )
        
        documents = document_repo.get_documents_by_order_id(sample_order.id)
        
        assert len(documents) == 2

    def test_increment_download_count(self, document_repo, sample_order):
        token_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        document = document_repo.create_document(
            order_id=sample_order.id,
            access_token="token",
            token_expires_at=token_expires
        )
        
        assert document.downloaded_count == 0
        assert document.last_downloaded_at is None
        
        updated_doc = document_repo.increment_download_count(document.document_id)
        
        assert updated_doc.downloaded_count == 1
        assert updated_doc.last_downloaded_at is not None

    def test_update_file_path(self, document_repo, sample_order):
        token_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        document = document_repo.create_document(
            order_id=sample_order.id,
            access_token="token",
            token_expires_at=token_expires,
            file_path="/old/path.docx"
        )
        
        updated_doc = document_repo.update_file_path(
            document.document_id,
            "/new/path.docx"
        )
        
        assert updated_doc.file_path == "/new/path.docx"

    def test_update_content(self, document_repo, sample_order):
        token_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        document = document_repo.create_document(
            order_id=sample_order.id,
            access_token="token",
            token_expires_at=token_expires
        )
        
        new_content = {"company_name": "Test Company", "sections": []}
        updated_doc = document_repo.update_content(document.document_id, new_content)
        
        assert updated_doc.content == new_content

    def test_is_token_valid_returns_true_for_valid_token(self, document_repo, sample_order):
        token_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        document_repo.create_document(
            order_id=sample_order.id,
            access_token="valid_token",
            token_expires_at=token_expires
        )
        
        assert document_repo.is_token_valid("valid_token") is True

    def test_is_token_valid_returns_false_for_expired_token(self, document_repo, sample_order):
        token_expires = datetime.now(timezone.utc) - timedelta(days=1)
        
        document_repo.create_document(
            order_id=sample_order.id,
            access_token="expired_token",
            token_expires_at=token_expires
        )
        
        assert document_repo.is_token_valid("expired_token") is False

    def test_is_token_valid_returns_false_for_nonexistent_token(self, document_repo):
        assert document_repo.is_token_valid("nonexistent") is False

    def test_get_expired_documents(self, document_repo, sample_order):
        expired_time = datetime.now(timezone.utc) - timedelta(days=1)
        valid_time = datetime.now(timezone.utc) + timedelta(days=7)
        
        document_repo.create_document(
            order_id=sample_order.id,
            access_token="expired",
            token_expires_at=expired_time
        )
        document_repo.create_document(
            order_id=sample_order.id,
            access_token="valid",
            token_expires_at=valid_time
        )
        
        expired_docs = document_repo.get_expired_documents()
        
        assert len(expired_docs) == 1
        assert expired_docs[0].access_token == "expired"

    def test_get_documents_by_format(self, document_repo, sample_order):
        token_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        document_repo.create_document(
            order_id=sample_order.id,
            access_token="docx_token",
            token_expires_at=token_expires,
            file_format=DocumentFormat.DOCX
        )
        document_repo.create_document(
            order_id=sample_order.id,
            access_token="pdf_token",
            token_expires_at=token_expires,
            file_format=DocumentFormat.PDF
        )
        
        docx_docs = document_repo.get_documents_by_format(DocumentFormat.DOCX)
        pdf_docs = document_repo.get_documents_by_format(DocumentFormat.PDF)
        
        assert len(docx_docs) == 1
        assert len(pdf_docs) == 1

    def test_create_document_without_order_id_fails(self, document_repo):
        with pytest.raises(ValueError, match="order_id is required"):
            document_repo.create_document(
                order_id=None,
                access_token="token",
                token_expires_at=datetime.now(timezone.utc)
            )

    def test_create_document_without_access_token_fails(self, document_repo, sample_order):
        with pytest.raises(ValueError, match="access_token is required"):
            document_repo.create_document(
                order_id=sample_order.id,
                access_token="",
                token_expires_at=datetime.now(timezone.utc)
            )

    def test_get_by_id_or_fail_raises_when_not_found(self, document_repo):
        with pytest.raises(RecordNotFoundError, match="not found"):
            document_repo.get_by_id_or_fail(99999)
