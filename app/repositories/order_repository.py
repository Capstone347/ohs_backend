from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order
from app.models.order_status import OrderStatusEnum, PaymentStatus
from app.repositories.base_repository import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: Session):
        super().__init__(Order, db)

    def get_by_id_with_relations(self, order_id: int) -> Order | None:
        if not order_id:
            raise ValueError("order_id is required")
        
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.user),
                joinedload(Order.company),
                joinedload(Order.plan),
                joinedload(Order.order_status),
                joinedload(Order.documents)
            )
            .filter(Order.id == order_id)
            .first()
        )

    def get_orders_by_user_id(self, user_id: int) -> list[Order]:
        if not user_id:
            raise ValueError("user_id is required")
        
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.plan),
                joinedload(Order.order_status),
                joinedload(Order.company)
            )
            .filter(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_orders_by_company_id(self, company_id: int) -> list[Order]:
        if not company_id:
            raise ValueError("company_id is required")
        
        return (
            self.db.query(Order)
            .options(joinedload(Order.user))
            .filter(Order.company_id == company_id)
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_orders_by_status(self, status: OrderStatusEnum) -> list[Order]:
        if not status:
            raise ValueError("status is required")
        
        from app.models.order_status import OrderStatus
        
        return (
            self.db.query(Order)
            .join(OrderStatus, Order.id == OrderStatus.order_id)
            .options(
                joinedload(Order.user),
                joinedload(Order.company),
                joinedload(Order.order_status)
            )
            .filter(OrderStatus.order_status == status)
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_orders_by_payment_status(self, payment_status: PaymentStatus) -> list[Order]:
        if not payment_status:
            raise ValueError("payment_status is required")
        
        from app.models.order_status import OrderStatus
        
        return (
            self.db.query(Order)
            .join(OrderStatus, Order.id == OrderStatus.order_id)
            .options(
                joinedload(Order.user),
                joinedload(Order.company),
                joinedload(Order.order_status)
            )
            .filter(OrderStatus.payment_status == payment_status)
            .order_by(Order.created_at.desc())
            .all()
        )

    def update_completed_at(self, order_id: int, completed_at: datetime) -> Order:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not completed_at:
            raise ValueError("completed_at is required")
        
        order = self.get_by_id_or_fail(order_id)
        order.completed_at = completed_at
        return self.update(order)

    def get_pending_orders(self, limit: int = 100) -> list[Order]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        
        from app.models.order_status import OrderStatus
        
        return (
            self.db.query(Order)
            .join(OrderStatus, Order.id == OrderStatus.order_id)
            .options(
                joinedload(Order.user),
                joinedload(Order.company),
                joinedload(Order.order_status)
            )
            .filter(
                OrderStatus.order_status == OrderStatusEnum.DRAFT,
                OrderStatus.payment_status == PaymentStatus.PENDING
            )
            .order_by(Order.created_at.asc())
            .limit(limit)
            .all()
        )

    def get_completed_orders_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> list[Order]:
        if not start_date:
            raise ValueError("start_date is required")
        
        if not end_date:
            raise ValueError("end_date is required")
        
        if start_date > end_date:
            raise ValueError("start_date must be before end_date")
        
        return (
            self.db.query(Order)
            .filter(
                Order.completed_at.isnot(None),
                Order.completed_at >= start_date,
                Order.completed_at <= end_date
            )
            .order_by(Order.completed_at.desc())
            .all()
        )

    def get_industry_specific_orders(self) -> list[Order]:
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.user),
                joinedload(Order.company),
                joinedload(Order.order_status)
            )
            .filter(Order.is_industry_specific == True)
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_orders_by_jurisdiction(self, jurisdiction: str) -> list[Order]:
        if not jurisdiction:
            raise ValueError("jurisdiction is required")
        
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.user),
                joinedload(Order.company),
                joinedload(Order.order_status)
            )
            .filter(Order.jurisdiction == jurisdiction)
            .order_by(Order.created_at.desc())
            .all()
        )
