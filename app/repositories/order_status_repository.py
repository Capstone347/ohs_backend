from sqlalchemy.orm import Session, joinedload

from app.models.order_status import OrderStatus, OrderStatusEnum, PaymentStatus
from app.repositories.base_repository import BaseRepository


class OrderStatusRepository(BaseRepository[OrderStatus]):
    def __init__(self, db: Session):
        super().__init__(OrderStatus, db)

    def get_by_id(self, order_id: int) -> OrderStatus | None:
        if not order_id:
            raise ValueError("order_id is required")
        
        return self.db.query(OrderStatus).filter(OrderStatus.order_id == order_id).first()

    def get_by_id_or_fail(self, order_id: int) -> OrderStatus:
        order_status = self.get_by_id(order_id)
        if not order_status:
            from app.repositories.base_repository import RecordNotFoundError
            raise RecordNotFoundError(f"OrderStatus for order {order_id} not found")
        return order_status

    def get_by_order_id_with_order(self, order_id: int) -> OrderStatus | None:
        if not order_id:
            raise ValueError("order_id is required")
        
        return (
            self.db.query(OrderStatus)
            .options(joinedload(OrderStatus.order))
            .filter(OrderStatus.order_id == order_id)
            .first()
        )

    def create_order_status(
        self,
        order_id: int,
        order_status: OrderStatusEnum = OrderStatusEnum.DRAFT,
        payment_status: PaymentStatus = PaymentStatus.PENDING,
        currency: str = "CAD",
        payment_provider: str | None = None
    ) -> OrderStatus:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not currency:
            raise ValueError("currency is required")
        
        from app.repositories.base_repository import DuplicateRecordError
        
        if self.get_by_id(order_id):
            raise DuplicateRecordError(f"OrderStatus for order {order_id} already exists")
        
        status = OrderStatus(
            order_id=order_id,
            order_status=order_status,
            payment_status=payment_status,
            currency=currency,
            payment_provider=payment_provider
        )
        return self.create(status)

    def update_order_status(self, order_id: int, new_status: OrderStatusEnum) -> OrderStatus:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not new_status:
            raise ValueError("new_status is required")
        
        order_status = self.get_by_id_or_fail(order_id)
        order_status.order_status = new_status
        return self.update(order_status)

    def update_payment_status(self, order_id: int, new_status: PaymentStatus) -> OrderStatus:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not new_status:
            raise ValueError("new_status is required")
        
        order_status = self.get_by_id_or_fail(order_id)
        order_status.payment_status = new_status
        return self.update(order_status)

    def update_payment_provider(self, order_id: int, payment_provider: str) -> OrderStatus:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not payment_provider:
            raise ValueError("payment_provider is required")
        
        order_status = self.get_by_id_or_fail(order_id)
        order_status.payment_provider = payment_provider
        return self.update(order_status)

    def get_by_status(self, status: OrderStatusEnum) -> list[OrderStatus]:
        if not status:
            raise ValueError("status is required")
        
        return (
            self.db.query(OrderStatus)
            .options(joinedload(OrderStatus.order))
            .filter(OrderStatus.order_status == status)
            .all()
        )

    def get_by_payment_status(self, payment_status: PaymentStatus) -> list[OrderStatus]:
        if not payment_status:
            raise ValueError("payment_status is required")
        
        return (
            self.db.query(OrderStatus)
            .options(joinedload(OrderStatus.order))
            .filter(OrderStatus.payment_status == payment_status)
            .all()
        )

    def get_pending_payments(self) -> list[OrderStatus]:
        return self.get_by_payment_status(PaymentStatus.PENDING)

    def get_failed_payments(self) -> list[OrderStatus]:
        return self.get_by_payment_status(PaymentStatus.FAILED)

    def get_draft_orders(self) -> list[OrderStatus]:
        return self.get_by_status(OrderStatusEnum.DRAFT)

    def get_processing_orders(self) -> list[OrderStatus]:
        return self.get_by_status(OrderStatusEnum.PROCESSING)

    def get_available_orders(self) -> list[OrderStatus]:
        return self.get_by_status(OrderStatusEnum.AVAILABLE)

    def mark_as_paid(self, order_id: int, payment_provider: str) -> OrderStatus:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not payment_provider:
            raise ValueError("payment_provider is required")
        
        order_status = self.get_by_id_or_fail(order_id)
        order_status.payment_status = PaymentStatus.PAID
        order_status.payment_provider = payment_provider
        return self.update(order_status)

    def mark_as_processing(self, order_id: int) -> OrderStatus:
        if not order_id:
            raise ValueError("order_id is required")
        
        return self.update_order_status(order_id, OrderStatusEnum.PROCESSING)

    def mark_as_available(self, order_id: int) -> OrderStatus:
        if not order_id:
            raise ValueError("order_id is required")
        
        return self.update_order_status(order_id, OrderStatusEnum.AVAILABLE)

    def mark_as_cancelled(self, order_id: int) -> OrderStatus:
        if not order_id:
            raise ValueError("order_id is required")
        
        return self.update_order_status(order_id, OrderStatusEnum.CANCELLED)

    def delete_by_order_id(self, order_id: int) -> None:
        if not order_id:
            raise ValueError("order_id is required")
        
        order_status = self.get_by_id_or_fail(order_id)
        self.db.delete(order_status)
        self.db.commit()
