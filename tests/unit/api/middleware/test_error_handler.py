import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.api.middleware.error_handler import register_exception_handlers
from app.core.exceptions import (
    ValidationError,
    OrderNotFoundError,
    DocumentGenerationError,
    PaymentProcessingError,
    EmailDeliveryError,
    FileStorageError,
    ConfigurationError,
    OHSRemoteException,
)


@pytest.fixture
def app_with_error_handlers():
    app = FastAPI()
    register_exception_handlers(app)
    
    @app.get("/validation-error")
    async def validation_error_endpoint():
        raise ValidationError("Invalid input data")
    
    @app.get("/order-not-found")
    async def order_not_found_endpoint():
        raise OrderNotFoundError("Order 123 not found")
    
    @app.get("/document-generation-error")
    async def document_generation_error_endpoint():
        raise DocumentGenerationError("Failed to generate document")
    
    @app.get("/payment-processing-error")
    async def payment_processing_error_endpoint():
        raise PaymentProcessingError("Payment gateway timeout")
    
    @app.get("/email-delivery-error")
    async def email_delivery_error_endpoint():
        raise EmailDeliveryError("SMTP connection failed")
    
    @app.get("/file-storage-error")
    async def file_storage_error_endpoint():
        raise FileStorageError("Failed to save file to disk")
    
    @app.get("/configuration-error")
    async def configuration_error_endpoint():
        raise ConfigurationError("Missing required configuration")
    
    @app.get("/generic-exception")
    async def generic_exception_endpoint():
        raise Exception("Something went wrong")
    
    @app.get("/http-404")
    async def http_404_endpoint():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Resource not found")
    
    class TestModel(BaseModel):
        name: str = Field(..., min_length=3)
        age: int = Field(..., gt=0)
    
    @app.post("/pydantic-validation")
    async def pydantic_validation_endpoint(data: TestModel):
        return {"ok": True}
    
    return app


def test_validation_error_handler_returns_400(app_with_error_handlers):
    client = TestClient(app_with_error_handlers)
    response = client.get("/validation-error")
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "Invalid input data"


def test_order_not_found_handler_returns_404(app_with_error_handlers):
    client = TestClient(app_with_error_handlers)
    response = client.get("/order-not-found")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "ORDER_NOT_FOUND"
    assert "Order 123 not found" in data["error"]["message"]


def test_document_generation_error_handler_returns_500(app_with_error_handlers):
    client = TestClient(app_with_error_handlers)
    response = client.get("/document-generation-error")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DOCUMENT_GENERATION_ERROR"


def test_payment_processing_error_handler_returns_500(app_with_error_handlers):
    client = TestClient(app_with_error_handlers)
    response = client.get("/payment-processing-error")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "PAYMENT_PROCESSING_ERROR"


def test_email_delivery_error_handler_returns_500(app_with_error_handlers):
    client = TestClient(app_with_error_handlers)
    response = client.get("/email-delivery-error")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "EMAIL_DELIVERY_ERROR"


def test_file_storage_error_handler_returns_500(app_with_error_handlers):
    client = TestClient(app_with_error_handlers)
    response = client.get("/file-storage-error")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "FILE_STORAGE_ERROR"


def test_configuration_error_handler_returns_500(app_with_error_handlers):
    client = TestClient(app_with_error_handlers)
    response = client.get("/configuration-error")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "CONFIGURATION_ERROR"


def test_generic_exception_handler_returns_500(app_with_error_handlers):
    client = TestClient(app_with_error_handlers, raise_server_exceptions=False)
    response = client.get("/generic-exception")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert data["error"]["message"] == "An unexpected error occurred"


def test_http_exception_handler_returns_correct_status(app_with_error_handlers):
    client = TestClient(app_with_error_handlers)
    response = client.get("/http-404")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"


def test_request_validation_error_handler_returns_422(app_with_error_handlers):
    client = TestClient(app_with_error_handlers)
    response = client.post("/pydantic-validation", json={"name": "ab", "age": -5})
    
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "One or more fields failed validation"
    assert "details" in data["error"]
    assert isinstance(data["error"]["details"], dict)


def test_error_responses_include_request_id_when_available(app_with_error_handlers):
    from app.api.middleware import RequestLoggingMiddleware
    
    app_with_error_handlers.add_middleware(RequestLoggingMiddleware)
    client = TestClient(app_with_error_handlers)
    
    response = client.get("/validation-error")
    
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36


def test_pydantic_validation_error_includes_field_details(app_with_error_handlers):
    client = TestClient(app_with_error_handlers)
    response = client.post("/pydantic-validation", json={})
    
    assert response.status_code == 422
    data = response.json()
    assert "details" in data["error"]
    
    details = data["error"]["details"]
    assert "name" in details or any("name" in key for key in details.keys())
    assert "age" in details or any("age" in key for key in details.keys())
