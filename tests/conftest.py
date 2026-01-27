import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_order_request():
    return {
        "plan_id": "basic",
        "user_email": "test@example.com",
        "company_name": "Test Company"
    }
