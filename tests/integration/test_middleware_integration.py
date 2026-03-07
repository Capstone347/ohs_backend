import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check_includes_request_id(client):
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36


def test_cors_headers_present(client):
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-credentials" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_exposes_request_id_header(client):
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    
    assert "X-Request-ID" in response.headers
    assert "access-control-expose-headers" in response.headers
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]


def test_invalid_endpoint_returns_structured_error(client):
    response = client.get("/api/v1/nonexistent")
    
    assert response.status_code == 404
    assert "X-Request-ID" in response.headers
    
    data = response.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]


def test_validation_error_returns_structured_response(client):
    response = client.post("/api/v1/orders", json={})
    
    assert response.status_code == 422
    assert "X-Request-ID" in response.headers
    
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]


def test_multiple_requests_have_different_request_ids(client):
    response1 = client.get("/api/v1/health")
    response2 = client.get("/api/v1/health")
    
    request_id_1 = response1.headers["X-Request-ID"]
    request_id_2 = response2.headers["X-Request-ID"]
    
    assert request_id_1 != request_id_2


def test_error_response_format_consistency(client):
    response1 = client.get("/api/v1/nonexistent")
    response2 = client.post("/api/v1/orders", json={})
    
    data1 = response1.json()
    data2 = response2.json()
    
    assert "error" in data1
    assert "error" in data2
    
    assert "code" in data1["error"]
    assert "message" in data1["error"]
    
    assert "code" in data2["error"]
    assert "message" in data2["error"]
