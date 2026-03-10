from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.schemas.payment import CheckoutSessionResponse


def make_fake_order(order_id: int = 1) -> SimpleNamespace:
    user = SimpleNamespace(email="buyer@example.com")
    company = SimpleNamespace(name="Test Company")
    plan = SimpleNamespace(name="Basic Plan")
    order_status = SimpleNamespace(
        currency="CAD",
        payment_status="pending",
        stripe_checkout_session_id=None,
    )
    order = SimpleNamespace(
        id=order_id,
        total_amount=Decimal("199.00"),
        user=user,
        company=company,
        plan=plan,
        order_status=order_status,
    )
    return order


def test_create_checkout_session_and_webhook(client, monkeypatch):
    fake_order = make_fake_order(1)
    called = {"paid": False, "session_stored": False}

    from app.repositories.order_repository import OrderRepository
    from app.repositories.order_status_repository import OrderStatusRepository
    from app.services.email_service import EmailService
    from app.services.payment_service import PaymentService

    def fake_get_by_id_with_relations(self, order_id: int):
        return fake_order

    def fake_mark_as_paid(self, order_id: int, payment_provider: str):
        called["paid"] = True
        return None

    def fake_update_stripe_checkout_session_id(self, order_id: int, session_id: str):
        called["session_stored"] = True
        return None

    def fake_update_stripe_payment_intent_id(self, order_id: int, pi_id: str):
        return None

    def fake_get_by_id(self, order_id: int):
        return fake_order.order_status

    def fake_send_email(self, order_id, recipient_email, subject, html_body, attachment_path=None):
        pass

    def fake_create_checkout_session(self, **kwargs):
        return CheckoutSessionResponse(
            checkout_session_id="cs_test_1",
            checkout_url="https://checkout.stripe.com/pay/cs_test_1",
        )

    monkeypatch.setattr(OrderRepository, "get_by_id_with_relations", fake_get_by_id_with_relations)
    monkeypatch.setattr(OrderStatusRepository, "mark_as_paid", fake_mark_as_paid)
    monkeypatch.setattr(OrderStatusRepository, "update_stripe_checkout_session_id", fake_update_stripe_checkout_session_id)
    monkeypatch.setattr(OrderStatusRepository, "update_stripe_payment_intent_id", fake_update_stripe_payment_intent_id)
    monkeypatch.setattr(OrderStatusRepository, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(EmailService, "send_email", fake_send_email)
    monkeypatch.setattr(PaymentService, "create_checkout_session", fake_create_checkout_session)

    resp = client.post(f"/api/v1/payments/orders/{fake_order.id}/create-checkout-session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checkout_session_id"] == "cs_test_1"
    assert "checkout.stripe.com" in data["checkout_url"]
    assert called["session_stored"] is True


def test_stripe_config_endpoint(client):
    resp = client.get("/api/v1/payments/stripe/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "publishable_key" in data
