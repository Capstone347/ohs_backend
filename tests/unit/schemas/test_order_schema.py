import pytest
from pydantic import ValidationError
from app.schemas.order import OrderCreate

valid = {"plan_id": "basic", "user_email": "user@example.com", "company_id": 1}


def test_order_valid():
    o = OrderCreate(**valid)
    assert o.plan_id == "basic"
    assert o.company_id == 1


@pytest.mark.parametrize("email", ["no-at", "bad@ domain.com", "bad@.com", ""])
def test_order_invalid_email(email):
    bad = valid.copy()
    bad["user_email"] = email
    with pytest.raises(ValidationError):
        OrderCreate(**bad)


def test_order_invalid_company_id():
    bad = valid.copy()
    bad["company_id"] = 0
    with pytest.raises(ValidationError):
        OrderCreate(**bad)
