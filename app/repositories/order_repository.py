from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.company import Company
from app.models.industry_profile import IndustryProfile
from app.models.order import Order
from app.models.order_status import OrderStatus, OrderStatusEnum, PaymentStatus
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
                joinedload(Order.company)
                .joinedload(Company.industry_profile)
                .joinedload(IndustryProfile.naics_codes),
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
                OrderStatus.order_status == OrderStatusEnum.DRAFT.value,
                OrderStatus.payment_status == PaymentStatus.PENDING.value
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

    def get_paginated_by_user_id(
        self,
        user_id: int,
        skip: int,
        limit: int,
        order_status: OrderStatusEnum | None = None,
        query: str | None = None,
    ) -> tuple[list[Order], int]:
        base_filter = [Order.user_id == user_id]

        needs_status_join = order_status is not None
        needs_company_join = query is not None and not query.isdigit()

        if query is not None:
            if query.isdigit():
                base_filter.append(Order.id == int(query))
            else:
                base_filter.append(Company.name.ilike(f"%{query}%"))

        if order_status is not None:
            base_filter.append(OrderStatus.order_status == order_status.value)

        count_q = select(func.count()).select_from(Order)
        if needs_status_join:
            count_q = count_q.join(OrderStatus, Order.id == OrderStatus.order_id)
        if needs_company_join:
            count_q = count_q.join(Company, Order.company_id == Company.id)
        count_q = count_q.where(*base_filter)
        total = self.db.execute(count_q).scalar_one()

        list_q = self.db.query(Order)
        if needs_status_join:
            list_q = list_q.join(OrderStatus, Order.id == OrderStatus.order_id)
        if needs_company_join:
            list_q = list_q.join(Company, Order.company_id == Company.id)
        list_q = (
            list_q.options(
                joinedload(Order.order_status),
                joinedload(Order.company)
                .joinedload(Company.industry_profile)
                .joinedload(IndustryProfile.naics_codes),
                joinedload(Order.plan),
                joinedload(Order.documents),
            )
            .filter(*base_filter)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        results = list_q.all()

        return results, total

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

    def get_all_paginated(
        self,
        skip: int,
        limit: int,
        order_status: str | None = None,
        payment_status: str | None = None,
        plan_id: int | None = None,
        query: str | None = None,
    ) -> tuple[list[Order], int]:
        base_filter = []
        needs_status_join = order_status is not None or payment_status is not None
        needs_company_join = query is not None and not query.isdigit()

        if query is not None:
            if query.isdigit():
                base_filter.append(Order.id == int(query))
            else:
                base_filter.append(Company.name.ilike(f"%{query}%"))

        if order_status is not None:
            base_filter.append(OrderStatus.order_status == order_status)

        if payment_status is not None:
            base_filter.append(OrderStatus.payment_status == payment_status)

        if plan_id is not None:
            base_filter.append(Order.plan_id == plan_id)

        count_q = select(func.count()).select_from(Order)
        if needs_status_join:
            count_q = count_q.join(OrderStatus, Order.id == OrderStatus.order_id)
        if needs_company_join:
            count_q = count_q.join(Company, Order.company_id == Company.id)
        if base_filter:
            count_q = count_q.where(*base_filter)
        total = self.db.execute(count_q).scalar_one()

        list_q = self.db.query(Order)
        if needs_status_join:
            list_q = list_q.join(OrderStatus, Order.id == OrderStatus.order_id)
        if needs_company_join:
            list_q = list_q.join(Company, Order.company_id == Company.id)
        list_q = (
            list_q.options(
                joinedload(Order.user),
                joinedload(Order.order_status),
                joinedload(Order.company),
                joinedload(Order.plan),
                joinedload(Order.documents),
            )
            .filter(*base_filter)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list_q.all(), total

    def get_review_pending_paginated(
        self,
        skip: int,
        limit: int,
    ) -> tuple[list[Order], int]:
        count_q = (
            select(func.count())
            .select_from(Order)
            .join(OrderStatus, Order.id == OrderStatus.order_id)
            .where(OrderStatus.order_status == OrderStatusEnum.REVIEW_PENDING.value)
        )
        total = self.db.execute(count_q).scalar_one()

        items = (
            self.db.query(Order)
            .join(OrderStatus, Order.id == OrderStatus.order_id)
            .options(
                joinedload(Order.user),
                joinedload(Order.order_status),
                joinedload(Order.company),
                joinedload(Order.plan),
            )
            .filter(OrderStatus.order_status == OrderStatusEnum.REVIEW_PENDING.value)
            .order_by(Order.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def get_revenue_stats(self) -> dict:
        from app.models.plan import Plan

        total_revenue = (
            self.db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .join(OrderStatus, Order.id == OrderStatus.order_id)
            .filter(OrderStatus.payment_status == PaymentStatus.PAID.value)
            .scalar()
        )

        total_orders = self.db.query(func.count(Order.id)).scalar()

        status_counts = (
            self.db.query(OrderStatus.order_status, func.count(OrderStatus.order_id))
            .group_by(OrderStatus.order_status)
            .all()
        )

        plan_stats = (
            self.db.query(
                Plan.name,
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_amount), 0),
            )
            .join(Order, Plan.id == Order.plan_id)
            .join(OrderStatus, Order.id == OrderStatus.order_id)
            .filter(OrderStatus.payment_status == PaymentStatus.PAID.value)
            .group_by(Plan.name)
            .all()
        )

        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "orders_by_status": {row[0]: row[1] for row in status_counts},
            "orders_by_plan": {row[0]: row[1] for row in plan_stats},
            "revenue_by_plan": {row[0]: row[2] for row in plan_stats},
        }

    def update_review_info(
        self,
        order_id: int,
        admin_id: int,
        reviewed_at: datetime,
    ) -> Order:
        order = self.get_by_id_or_fail(order_id)
        order.reviewed_by_admin_id = admin_id
        order.reviewed_at = reviewed_at
        return self.update(order)
