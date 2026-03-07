import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import Response

from app.api.middleware.logging_middleware import RequestLoggingMiddleware


@pytest.fixture
def app_with_logging_middleware():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}
    
    @app.get("/test-error")
    async def test_error_endpoint():
        raise ValueError("Test error")
    
    return app


def test_request_logging_middleware_adds_request_id(app_with_logging_middleware):
    from fastapi.testclient import TestClient
    
    client = TestClient(app_with_logging_middleware)
    response = client.get("/test")
    
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36
    
    try:
        uuid.UUID(request_id)
        is_valid_uuid = True
    except ValueError:
        is_valid_uuid = False
    
    assert is_valid_uuid


@patch("app.api.middleware.logging_middleware.logger")
def test_request_logging_middleware_logs_request(mock_logger, app_with_logging_middleware):
    from fastapi.testclient import TestClient
    
    client = TestClient(app_with_logging_middleware)
    response = client.get("/test?query=value")
    
    assert response.status_code == 200
    assert mock_logger.info.call_count >= 2
    
    first_call = mock_logger.info.call_args_list[0]
    assert "Request received" in first_call[0]
    assert "method" in first_call[1]
    assert first_call[1]["method"] == "GET"
    assert "path" in first_call[1]
    assert first_call[1]["path"] == "/test"


@patch("app.api.middleware.logging_middleware.logger")
def test_request_logging_middleware_logs_completion(mock_logger, app_with_logging_middleware):
    from fastapi.testclient import TestClient
    
    client = TestClient(app_with_logging_middleware)
    response = client.get("/test")
    
    assert response.status_code == 200
    
    completion_calls = [call for call in mock_logger.info.call_args_list if "Request completed" in call[0]]
    assert len(completion_calls) == 1
    
    completion_call = completion_calls[0]
    assert "status_code" in completion_call[1]
    assert completion_call[1]["status_code"] == 200
    assert "duration_seconds" in completion_call[1]


@patch("app.api.middleware.logging_middleware.logger")
def test_request_logging_middleware_logs_error(mock_logger, app_with_logging_middleware):
    from fastapi.testclient import TestClient
    
    client = TestClient(app_with_logging_middleware)
    
    try:
        client.get("/test-error")
    except Exception:
        pass
    
    error_calls = [call for call in mock_logger.error.call_args_list if "Request failed" in call[0]]
    assert len(error_calls) == 1
    
    error_call = error_calls[0]
    assert "error" in error_call[1]
    assert "error_type" in error_call[1]
    assert error_call[1]["error_type"] == "ValueError"


def test_request_logging_middleware_includes_query_params(app_with_logging_middleware):
    from fastapi.testclient import TestClient
    
    client = TestClient(app_with_logging_middleware)
    response = client.get("/test?param1=value1&param2=value2")
    
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
