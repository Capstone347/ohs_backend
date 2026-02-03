import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_document_service
from app.models.document import Document, DocumentFormat
from app.models.order import Order
from app.models.company import Company
from app.models.plan import Plan, PlanSlug, PlanName
from app.services.exceptions import (
    FileNotFoundServiceException,
    DocumentGenerationServiceException,
)
from app.repositories.base_repository import RecordNotFoundError

client = TestClient(app)


class TestGenerateDocumentPreview:
    def test_generate_document_preview_success(self):
        mock_service = Mock()
        mock_document = Mock(spec=Document)
        mock_document.document_id = 1
        mock_document.order_id = 101
        mock_document.generated_at = datetime.now(timezone.utc)
        
        mock_service.generate_document_for_order.return_value = mock_document
        
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.post("/api/v1/orders/101/generate-preview")
            
            assert response.status_code == 201
            data = response.json()
            assert data["document_id"] == 1
            assert data["order_id"] == 101
            assert data["message"] == "Document generated successfully"
            assert "generated_at" in data
        finally:
            app.dependency_overrides.clear()
    
    def test_generate_document_preview_invalid_order_id(self):
        response = client.post("/api/v1/orders/0/generate-preview")
        
        assert response.status_code == 400
        assert "order_id must be greater than 0" in response.json()["detail"]
    
    def test_generate_document_preview_order_not_found(self):
        mock_service = Mock()
        mock_service.generate_document_for_order.side_effect = RecordNotFoundError("Order 999 not found")
        
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.post("/api/v1/orders/999/generate-preview")
            
            assert response.status_code == 404
            assert "Order 999 not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_generate_document_preview_generation_error(self):
        mock_service = Mock()
        mock_service.generate_document_for_order.side_effect = DocumentGenerationServiceException("Template not found")
        
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.post("/api/v1/orders/101/generate-preview")
            
            assert response.status_code == 400
            assert "Template not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


class TestGetDocumentPreview:
    def test_get_document_preview_success(self):
        mock_service = Mock()
        mock_path = Path("/tmp/preview_test.pdf")
        mock_path.touch()
        
        try:
            mock_service.get_document_preview_path.return_value = mock_path
            
            app.dependency_overrides[get_document_service] = lambda: mock_service
            
            response = client.get("/api/v1/documents/1/preview")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
        finally:
            if mock_path.exists():
                mock_path.unlink()
            app.dependency_overrides.clear()
    
    def test_get_document_preview_invalid_document_id(self):
        response = client.get("/api/v1/documents/0/preview")
        
        assert response.status_code == 400
        assert "document_id must be greater than 0" in response.json()["detail"]
    
    def test_get_document_preview_document_not_found(self):
        mock_service = Mock()
        mock_service.get_document_preview_path.side_effect = RecordNotFoundError("Document 999 not found")
        
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/documents/999/preview")
            
            assert response.status_code == 404
            assert "Document 999 not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_get_document_preview_file_not_found(self):
        mock_service = Mock()
        mock_service.get_document_preview_path.side_effect = FileNotFoundServiceException("Preview file not found")
        
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/documents/1/preview")
            
            assert response.status_code == 404
            assert "Preview file not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


class TestDownloadDocument:
    def test_download_document_success(self):
        mock_service = Mock()
        mock_path = Path("/tmp/document_test.docx")
        mock_path.touch()
        
        try:
            mock_service.get_document_download_path.return_value = mock_path
            
            app.dependency_overrides[get_document_service] = lambda: mock_service
            
            response = client.get("/api/v1/documents/1/download?token=valid_token_123")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        finally:
            if mock_path.exists():
                mock_path.unlink()
            app.dependency_overrides.clear()
    
    def test_download_document_missing_token(self):
        response = client.get("/api/v1/documents/1/download")
        
        assert response.status_code == 422
    
    def test_download_document_invalid_token(self):
        mock_service = Mock()
        mock_service.get_document_download_path.side_effect = DocumentGenerationServiceException("Invalid access token")
        
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/documents/1/download?token=invalid_token")
            
            assert response.status_code == 403
            assert "Invalid access token" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_download_document_expired_token(self):
        mock_service = Mock()
        mock_service.get_document_download_path.side_effect = DocumentGenerationServiceException("Access token has expired")
        
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/documents/1/download?token=expired_token")
            
            assert response.status_code == 403
            assert "Access token has expired" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_download_document_not_found(self):
        mock_service = Mock()
        mock_service.get_document_download_path.side_effect = RecordNotFoundError("Document 999 not found")
        
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/documents/999/download?token=valid_token")
            
            assert response.status_code == 404
            assert "Document 999 not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_download_document_invalid_document_id(self):
        response = client.get("/api/v1/documents/0/download?token=valid_token")
        
        assert response.status_code == 400
        assert "document_id must be greater than 0" in response.json()["detail"]


class TestGetDocument:
    def test_get_document_success(self):
        mock_service = Mock()
        mock_document = Mock(spec=Document)
        mock_document.document_id = 1
        mock_document.order_id = 101
        mock_document.file_path = "/data/documents/test.docx"
        mock_document.file_format = DocumentFormat.DOCX
        mock_document.access_token = "test_token_123"
        mock_document.token_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        mock_document.generated_at = datetime.now(timezone.utc)
        
        mock_service.get_document_by_id.return_value = mock_document
        
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/documents/1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == 1
            assert data["order_id"] == 101
            assert data["file_path"] == "/data/documents/test.docx"
            assert data["file_format"] == "docx"
            assert data["access_token"] == "test_token_123"
        finally:
            app.dependency_overrides.clear()
    
    def test_get_document_not_found(self):
        mock_service = Mock()
        mock_service.get_document_by_id.side_effect = RecordNotFoundError("Document 999 not found")
        
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/documents/999")
            
            assert response.status_code == 404
            assert "Document 999 not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_get_document_invalid_document_id(self):
        response = client.get("/api/v1/documents/0")
        
        assert response.status_code == 400
        assert "document_id must be greater than 0" in response.json()["detail"]
