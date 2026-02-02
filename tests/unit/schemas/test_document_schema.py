import pytest
from pydantic import ValidationError
from app.schemas.document import DocumentResponse
from datetime import datetime


def test_document_parse_and_orm_mode():
    data = {
        "id": 7,
        "order_id": 101,
        "filename": "ohs_manual.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "path": "/data/documents/ohs_manual.docx",
        "created_at": "2026-02-02T12:00:00Z",
    }
    d = DocumentResponse.parse_obj(data)
    assert d.id == 7
    assert isinstance(d.created_at, datetime)


def test_document_invalid_missing_filename():
    data = {
        "id": 7,
        "order_id": 101,
        "mime_type": "application/msword",
        "path": "/x",
        "created_at": "2026-02-02T12:00:00Z",
    }
    with pytest.raises(ValidationError):
        DocumentResponse.parse_obj(data)
