from datetime import UTC, datetime

from app.models.order import Order
from app.models.order_status import OrderStatusEnum, PaymentStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.services.exceptions import InvalidOrderStateException
from app.services.order_fulfillment_service import OrderFulfillmentService


class AdminOrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        order_status_repo: OrderStatusRepository,
        fulfillment_service: OrderFulfillmentService,
    ):
        self.order_repo = order_repo
        self.order_status_repo = order_status_repo
        self.fulfillment_service = fulfillment_service

    def approve_order(self, order_id: int, admin_id: int) -> Order:
        order = self.order_repo.get_by_id_with_relations(order_id)
        if not order:
            raise InvalidOrderStateException(f"Order {order_id} not found")

        if not order.order_status or order.order_status.order_status != OrderStatusEnum.REVIEW_PENDING.value:
            raise InvalidOrderStateException(
                f"Order {order_id} is not in review_pending status"
            )

        order.reviewed_by_admin_id = admin_id
        order.reviewed_at = datetime.now(UTC)
        self.order_repo.update(order)

        self.fulfillment_service.fulfill_order(order_id)

        return self.order_repo.get_by_id_with_relations(order_id)

    def get_all_orders_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        order_status: str | None = None,
        payment_status: str | None = None,
        plan_id: int | None = None,
        query: str | None = None,
    ) -> tuple[list[Order], int]:
        skip = (page - 1) * page_size
        return self.order_repo.get_all_paginated(
            skip=skip,
            limit=page_size,
            order_status=order_status,
            payment_status=payment_status,
            plan_id=plan_id,
            query=query,
        )

    def get_pending_review_orders(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Order], int]:
        skip = (page - 1) * page_size
        return self.order_repo.get_review_pending_paginated(skip=skip, limit=page_size)

    def get_order_detail(self, order_id: int) -> Order:
        order = self.order_repo.get_by_id_with_relations(order_id)
        if not order:
            raise InvalidOrderStateException(f"Order {order_id} not found")
        return order

    def update_admin_notes(self, order_id: int, admin_notes: str) -> Order:
        order = self.order_repo.get_by_id_with_relations(order_id)
        if not order:
            raise InvalidOrderStateException(f"Order {order_id} not found")

        order.admin_notes = admin_notes
        return self.order_repo.update(order)

    def resend_delivery_email(self, order_id: int) -> None:
        order = self.order_repo.get_by_id_with_relations(order_id)
        if not order:
            raise InvalidOrderStateException(f"Order {order_id} not found")

        if not order.order_status or order.order_status.payment_status != PaymentStatus.PAID.value:
            raise InvalidOrderStateException(f"Order {order_id} payment is not completed")

        self.fulfillment_service.fulfill_order(order_id)

    def regenerate_document(self, order_id: int) -> None:
        order = self.order_repo.get_by_id_with_relations(order_id)
        if not order:
            raise InvalidOrderStateException(f"Order {order_id} not found")

        if not order.order_status or order.order_status.payment_status != PaymentStatus.PAID.value:
            raise InvalidOrderStateException(f"Order {order_id} payment is not completed")

        self.fulfillment_service.document_service.generate_document_for_order(order_id)
