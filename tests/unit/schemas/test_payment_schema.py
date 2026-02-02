import pytest
from pydantic import ValidationError
from app.schemas.payment import PaymentCreate

valid = {"order_id": 101, "amount_cents": 19900, "currency": "CAD"}


def test_payment_valid():
    p = PaymentCreate(**valid)
    assert p.currency == "CAD"


@pytest.mark.parametrize("payload", [
    {"order_id": -1, "amount_cents": 100, "currency": "CAD"},
    {"order_id": 1, "amount_cents": -10, "currency": "CAD"},
    {"order_id": 1, "amount_cents": 100, "currency": "US"},
])
def test_payment_invalid(payload):
    with pytest.raises(ValidationError):
        PaymentCreate(**payload)
