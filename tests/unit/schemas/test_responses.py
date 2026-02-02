from app.schemas.responses import ErrorResponse, SuccessResponse


def test_error_response_serializes():
    err = ErrorResponse(code="VALIDATION_ERROR", message="invalid", details={"field": "x"})
    data = err.dict()
    assert data["code"] == "VALIDATION_ERROR"
    assert "details" in data


def test_success_response_default():
    s = SuccessResponse()
    assert s.ok is True
    assert s.data is None
