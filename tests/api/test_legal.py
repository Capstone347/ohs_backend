import pytest
from datetime import datetime, date
from unittest.mock import Mock
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_legal_service
from app.models.legal_acknowledgment import LegalAcknowledgement
from app.services.exceptions import (
    ServiceException,
    FileNotFoundServiceException,
)
from app.repositories.base_repository import RecordNotFoundError

client = TestClient(app)


class TestGetLegalDisclaimer:
    def test_get_legal_disclaimer_success(self):
        mock_service = Mock()
        mock_service.get_legal_disclaimer.return_value = "This is a legal disclaimer for Ontario Basic plan..."
        
        app.dependency_overrides[get_legal_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/legal-disclaimers/1/ON")
            
            assert response.status_code == 200
            data = response.json()
            assert data["plan_id"] == 1
            assert data["jurisdiction"] == "ON"
            assert "legal disclaimer" in data["content"]
            assert data["version"] == 1
        finally:
            app.dependency_overrides.clear()
    
    def test_get_legal_disclaimer_lowercase_jurisdiction(self):
        mock_service = Mock()
        mock_service.get_legal_disclaimer.return_value = "Legal disclaimer content..."
        
        app.dependency_overrides[get_legal_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/legal-disclaimers/1/bc")
            
            assert response.status_code == 200
            data = response.json()
            assert data["jurisdiction"] == "BC"
        finally:
            app.dependency_overrides.clear()
    
    def test_get_legal_disclaimer_invalid_plan_id(self):
        response = client.get("/api/v1/legal-disclaimers/0/ON")
        
        assert response.status_code == 400
        assert "plan_id must be greater than 0" in response.json()["detail"]
    
    def test_get_legal_disclaimer_invalid_jurisdiction_length(self):
        response = client.get("/api/v1/legal-disclaimers/1/ONT")
        
        assert response.status_code == 400
        assert "jurisdiction must be a 2-character code" in response.json()["detail"]
    
    def test_get_legal_disclaimer_plan_not_found(self):
        mock_service = Mock()
        mock_service.get_legal_disclaimer.side_effect = RecordNotFoundError("Plan with id 999 not found")
        
        app.dependency_overrides[get_legal_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/legal-disclaimers/999/ON")
            
            assert response.status_code == 404
            assert "Plan with id 999 not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_get_legal_disclaimer_jurisdiction_not_available(self):
        mock_service = Mock()
        mock_service.get_legal_disclaimer.side_effect = FileNotFoundServiceException("No legal disclaimer available for jurisdiction: XX")
        
        app.dependency_overrides[get_legal_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/legal-disclaimers/1/XX")
            
            assert response.status_code == 404
            assert "No legal disclaimer available for jurisdiction: XX" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_get_legal_disclaimer_missing_jurisdiction(self):
        response = client.get("/api/v1/legal-disclaimers/1/")
        
        assert response.status_code == 404


class TestAcknowledgeLegalTerms:
    def test_acknowledge_legal_terms_success(self):
        mock_service = Mock()
        mock_acknowledgment = Mock(spec=LegalAcknowledgement)
        mock_acknowledgment.id = 1
        mock_acknowledgment.order_id = 101
        mock_acknowledgment.jurisdiction = "ON"
        mock_acknowledgment.version = 1
        mock_acknowledgment.effective_date = date.today()
        
        mock_service.record_acknowledgment.return_value = mock_acknowledgment
        
        app.dependency_overrides[get_legal_service] = lambda: mock_service
        
        try:
            request_data = {
                "jurisdiction": "ON",
                "content": "I acknowledge that I have read and agree to the terms...",
                "version": 1
            }
            
            response = client.post("/api/v1/orders/101/acknowledge-terms", json=request_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 1
            assert data["order_id"] == 101
            assert data["jurisdiction"] == "ON"
            assert data["version"] == 1
            assert "acknowledged_at" in data
        finally:
            app.dependency_overrides.clear()
    
    def test_acknowledge_legal_terms_lowercase_jurisdiction(self):
        mock_service = Mock()
        mock_acknowledgment = Mock(spec=LegalAcknowledgement)
        mock_acknowledgment.id = 1
        mock_acknowledgment.order_id = 101
        mock_acknowledgment.jurisdiction = "BC"
        mock_acknowledgment.version = 1
        mock_acknowledgment.effective_date = date.today()
        
        mock_service.record_acknowledgment.return_value = mock_acknowledgment
        
        app.dependency_overrides[get_legal_service] = lambda: mock_service
        
        try:
            request_data = {
                "jurisdiction": "bc",
                "content": "I acknowledge...",
                "version": 1
            }
            
            response = client.post("/api/v1/orders/101/acknowledge-terms", json=request_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["jurisdiction"] == "BC"
        finally:
            app.dependency_overrides.clear()
    
    def test_acknowledge_legal_terms_invalid_order_id(self):
        request_data = {
            "jurisdiction": "ON",
            "content": "I acknowledge...",
            "version": 1
        }
        
        response = client.post("/api/v1/orders/0/acknowledge-terms", json=request_data)
        
        assert response.status_code == 400
        assert "order_id must be greater than 0" in response.json()["detail"]
    
    def test_acknowledge_legal_terms_missing_jurisdiction(self):
        request_data = {
            "jurisdiction": "",
            "content": "I acknowledge...",
            "version": 1
        }
        
        response = client.post("/api/v1/orders/101/acknowledge-terms", json=request_data)
        
        assert response.status_code == 422
    
    def test_acknowledge_legal_terms_invalid_jurisdiction_length(self):
        request_data = {
            "jurisdiction": "ONT",
            "content": "I acknowledge...",
            "version": 1
        }
        
        response = client.post("/api/v1/orders/101/acknowledge-terms", json=request_data)
        
        assert response.status_code == 422
    
    def test_acknowledge_legal_terms_missing_content(self):
        request_data = {
            "jurisdiction": "ON",
            "content": "",
            "version": 1
        }
        
        response = client.post("/api/v1/orders/101/acknowledge-terms", json=request_data)
        
        assert response.status_code == 422
    
    def test_acknowledge_legal_terms_order_not_found(self):
        mock_service = Mock()
        mock_service.record_acknowledgment.side_effect = RecordNotFoundError("Order 999 not found")
        
        app.dependency_overrides[get_legal_service] = lambda: mock_service
        
        try:
            request_data = {
                "jurisdiction": "ON",
                "content": "I acknowledge...",
                "version": 1
            }
            
            response = client.post("/api/v1/orders/999/acknowledge-terms", json=request_data)
            
            assert response.status_code == 404
            assert "Order 999 not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_acknowledge_legal_terms_already_exists(self):
        mock_service = Mock()
        mock_service.record_acknowledgment.side_effect = ServiceException("Legal acknowledgment already exists for order 101")
        
        app.dependency_overrides[get_legal_service] = lambda: mock_service
        
        try:
            request_data = {
                "jurisdiction": "ON",
                "content": "I acknowledge...",
                "version": 1
            }
            
            response = client.post("/api/v1/orders/101/acknowledge-terms", json=request_data)
            
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


class TestGetOrderLegalAcknowledgment:
    def test_get_order_legal_acknowledgment_success(self):
        mock_service = Mock()
        mock_acknowledgment = Mock(spec=LegalAcknowledgement)
        mock_acknowledgment.id = 1
        mock_acknowledgment.order_id = 101
        mock_acknowledgment.jurisdiction = "ON"
        mock_acknowledgment.version = 1
        mock_acknowledgment.effective_date = date.today()
        
        mock_service.get_acknowledgment_by_order.return_value = mock_acknowledgment
        
        app.dependency_overrides[get_legal_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/orders/101/legal-acknowledgment")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["order_id"] == 101
            assert data["jurisdiction"] == "ON"
            assert data["version"] == 1
        finally:
            app.dependency_overrides.clear()
    
    def test_get_order_legal_acknowledgment_not_found(self):
        mock_service = Mock()
        mock_service.get_acknowledgment_by_order.side_effect = RecordNotFoundError("Legal acknowledgment for order 999 not found")
        
        app.dependency_overrides[get_legal_service] = lambda: mock_service
        
        try:
            response = client.get("/api/v1/orders/999/legal-acknowledgment")
            
            assert response.status_code == 404
            assert "Legal acknowledgment for order 999 not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_get_order_legal_acknowledgment_invalid_order_id(self):
        response = client.get("/api/v1/orders/0/legal-acknowledgment")
        
        assert response.status_code == 400
        assert "order_id must be greater than 0" in response.json()["detail"]
