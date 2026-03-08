from decimal import Decimal
from types import SimpleNamespace

import pytest


def make_fake_order(order_id: int = 1) -> SimpleNamespace:
    user = SimpleNamespace(email="buyer@example.com")
    company = SimpleNamespace(name="Test Company")
    order_status = SimpleNamespace(currency="CAD")
    order = SimpleNamespace(
        id=order_id,
        total_amount=Decimal("199.00"),
        user=user,
        company=company,
        order_status=order_status,
    )
    return order


def test_payment_flow_creates_intent_and_triggers_webhook(client, monkeypatch):
    fake_order = make_fake_order(1)

    called = {"paid": False, "delivered": False}

    from app.repositories.order_repository import OrderRepository
    from app.repositories.order_status_repository import OrderStatusRepository
    from app.services.email_service import EmailService

    def fake_get_by_id_or_fail(self, order_id: int):
        assert order_id == fake_order.id
        return fake_order

    def fake_get_by_id_with_relations(self, order_id: int):
        assert order_id == fake_order.id
        return fake_order

    def fake_mark_as_paid(self, order_id: int, payment_provider: str):
        assert order_id == fake_order.id
        called["paid"] = True
        return None

    def fake_send_email(self, order_id: int, recipient_email: str, subject: str, html_body: str, attachment_path=None):
        assert order_id == fake_order.id
        called["delivered"] = True

    monkeypatch.setattr(OrderRepository, "get_by_id_or_fail", fake_get_by_id_or_fail)
    monkeypatch.setattr(OrderRepository, "get_by_id_with_relations", fake_get_by_id_with_relations)
    monkeypatch.setattr(OrderStatusRepository, "mark_as_paid", fake_mark_as_paid)
    monkeypatch.setattr(EmailService, "send_email", fake_send_email)

    resp = client.post(f"/api/v1/orders/{fake_order.id}/payment-intent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"].startswith("pi_mock_")
    assert data["status"] == "succeeded"
    assert data["amount_cents"] == 19900

    webhook_payload = {
        "event_type": "payment_intent.succeeded",
        "payment_intent_id": data["id"],
        "metadata": {"order_id": str(fake_order.id)}
    }

    resp2 = client.post("/api/v1/webhooks/payment-confirmation", json=webhook_payload)
    assert resp2.status_code == 200
    assert called["paid"] is True
    assert called["delivered"] is True


def test_webhook_ignored_on_non_succeeded_event(client):
    payload = {
        "event_type": "payment_intent.failed",
        "payment_intent_id": "pi_mock_1",
        "metadata": {"order_id": "1"}
    }

    resp = client.post("/api/v1/webhooks/payment-confirmation", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_webhook_errors_on_missing_or_invalid_order_id(client):
    payload_missing = {
        "event_type": "payment_intent.succeeded",
        "payment_intent_id": "pi_mock_1",
        "metadata": {}
    }

    resp_missing = client.post("/api/v1/webhooks/payment-confirmation", json=payload_missing)
    assert resp_missing.status_code == 400
    assert resp_missing.json()["detail"] == "order_id missing from metadata"

    payload_invalid = {
        "event_type": "payment_intent.succeeded",
        "payment_intent_id": "pi_mock_1",
        "metadata": {"order_id": "notanint"}
    }

    resp_invalid = client.post("/api/v1/webhooks/payment-confirmation", json=payload_invalid)
    assert resp_invalid.status_code == 400
    assert resp_invalid.json()["detail"] == "Invalid order_id in metadata"
