from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict


@dataclass
class PaymentIntent:
    id: str
    client_secret: str | None
    status: str
    currency: str
    amount_cents: int


class BasePaymentProvider(ABC):
    @abstractmethod
    def create_payment_intent(self, order_id: int, amount_cents: int, currency: str) -> Dict[str, str]:
        pass

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> Dict:
        pass


class MockPaymentProvider(BasePaymentProvider):
    def create_payment_intent(self, order_id: int, amount_cents: int, currency: str = "cad") -> Dict[str, str]:
        if amount_cents <= 0:
            raise ValueError("amount_cents must be greater than zero")
        return {
            "id": f"pi_mock_{order_id}",
            "client_secret": f"cs_mock_{order_id}",
            "status": "succeeded",
            "currency": currency,
            "amount": str(amount_cents),
        }

    def verify_webhook_signature(self, payload: bytes, signature: str) -> Dict:
        return {
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_mock", "metadata": {}}},
        }


class PaymentService:
    def __init__(self, provider: BasePaymentProvider | None = None):
        self.provider = provider or MockPaymentProvider()

    def create_payment_intent(self, order_id: int, amount_cents: int, currency: str = "cad") -> Dict[str, str]:
        return self.provider.create_payment_intent(order_id, amount_cents, currency)

    def verify_webhook_signature(self, payload: bytes, signature: str) -> Dict:
        return self.provider.verify_webhook_signature(payload, signature)
