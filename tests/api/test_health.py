from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "environment" in data
    assert "timestamp" in data


def test_health_check_response_structure():
    response = client.get("/api/v1/health")
    data = response.json()
    
    required_fields = ["status", "version", "environment", "timestamp"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
