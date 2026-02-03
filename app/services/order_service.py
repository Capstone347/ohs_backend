from datetime import datetime, timezone
from decimal import Decimal

from app.models.order import Order
from app.models.order_status import OrderStatusEnum, PaymentStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.user_repository import UserRepository
from app.repositories.plan_repository import PlanRepository
from app.services.validation_service import ValidationService
from app.services.exceptions import (
    OrderServiceException,
    OrderNotCreatedException,
    OrderStatusUpdateException,
    InvalidOrderStateException,
)


class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        order_status_repo: OrderStatusRepository,
        company_repo: CompanyRepository,
        user_repo: UserRepository,
        plan_repo: PlanRepository,
        validation_service: ValidationService,
    ):
        self.order_repo = order_repo
        self.order_status_repo = order_status_repo
        self.company_repo = company_repo
        self.user_repo = user_repo
        self.plan_repo = plan_repo
        self.validation_service = validation_service

    def create_order(
        self,
        user_id: int,
        company_id: int,
        plan_id: int,
        jurisdiction: str,
        total_amount: Decimal,
        is_industry_specific: bool = False,
        admin_notes: str | None = None,
    ) -> Order:
        if not user_id:
            raise OrderNotCreatedException("user_id is required")
        
        if not company_id:
            raise OrderNotCreatedException("company_id is required")
        
        if not plan_id:
            raise OrderNotCreatedException("plan_id is required")
        
        if not jurisdiction:
            raise OrderNotCreatedException("jurisdiction is required")
        
        if total_amount <= 0:
            raise OrderNotCreatedException("total_amount must be greater than zero")
        
        user = self.user_repo.get_by_id_or_fail(user_id)
        company = self.company_repo.get_by_id_or_fail(company_id)
        plan = self.plan_repo.get_by_id_or_fail(plan_id)
        
        self.validation_service.validate_jurisdiction(jurisdiction)
        
        order = Order(
            user_id=user_id,
            company_id=company_id,
            plan_id=plan_id,
            jurisdiction=jurisdiction,
            total_amount=total_amount,
            is_industry_specific=is_industry_specific,
            admin_notes=admin_notes,
            created_at=datetime.now(timezone.utc),
        )
        
        created_order = self.order_repo.create(order)
        
        self.order_status_repo.create_order_status(
            order_id=created_order.id,
            order_status=OrderStatusEnum.DRAFT,
            payment_status=PaymentStatus.PENDING,
        )
        
        return created_order

    def get_order(self, order_id: int) -> Order:
        if not order_id:
            raise OrderServiceException("order_id is required")
        
        return self.order_repo.get_by_id_or_fail(order_id)

    def get_order_with_relations(self, order_id: int) -> Order:
        if not order_id:
            raise OrderServiceException("order_id is required")
        
        order = self.order_repo.get_by_id_with_relations(order_id)
        
        if not order:
            from app.repositories.base_repository import RecordNotFoundError
            raise RecordNotFoundError(f"Order {order_id} not found")
        
        return order

    def get_orders_by_user(self, user_id: int) -> list[Order]:
        if not user_id:
            raise OrderServiceException("user_id is required")
        
        self.user_repo.get_by_id_or_fail(user_id)
        
        return self.order_repo.get_orders_by_user_id(user_id)

    def get_orders_by_company(self, company_id: int) -> list[Order]:
        if not company_id:
            raise OrderServiceException("company_id is required")
        
        self.company_repo.get_by_id_or_fail(company_id)
        
        return self.order_repo.get_orders_by_company_id(company_id)

    def update_order_status(self, order_id: int, new_status: OrderStatusEnum) -> Order:
        if not order_id:
            raise OrderStatusUpdateException("order_id is required")
        
        if not new_status:
            raise OrderStatusUpdateException("new_status is required")
        
        order = self.order_repo.get_by_id_or_fail(order_id)
        
        self.order_status_repo.update_order_status(order_id, new_status)
        
        return self.order_repo.get_by_id_or_fail(order_id)

    def mark_order_as_paid(self, order_id: int, payment_provider: str) -> Order:
        if not order_id:
            raise OrderStatusUpdateException("order_id is required")
        
        if not payment_provider:
            raise OrderStatusUpdateException("payment_provider is required")
        
        order = self.order_repo.get_by_id_or_fail(order_id)
        
        order_status = self.order_status_repo.get_by_id_or_fail(order_id)
        
        if order_status.payment_status == PaymentStatus.PAID:
            raise InvalidOrderStateException(f"Order {order_id} is already marked as paid")
        
        self.order_status_repo.mark_as_paid(order_id, payment_provider)
        
        return self.order_repo.get_by_id_or_fail(order_id)

    def mark_order_as_processing(self, order_id: int) -> Order:
        if not order_id:
            raise OrderStatusUpdateException("order_id is required")
        
        order = self.order_repo.get_by_id_or_fail(order_id)
        
        order_status = self.order_status_repo.get_by_id_or_fail(order_id)
        
        if order_status.payment_status != PaymentStatus.PAID:
            raise InvalidOrderStateException(
                f"Order {order_id} cannot be marked as processing. Payment must be completed first."
            )
        
        self.order_status_repo.mark_as_processing(order_id)
        
        return self.order_repo.get_by_id_or_fail(order_id)

    def mark_order_as_available(self, order_id: int) -> Order:
        if not order_id:
            raise OrderStatusUpdateException("order_id is required")
        
        order = self.order_repo.get_by_id_or_fail(order_id)
        
        order_status = self.order_status_repo.get_by_id_or_fail(order_id)
        
        if order_status.order_status != OrderStatusEnum.PROCESSING:
            raise InvalidOrderStateException(
                f"Order {order_id} must be in PROCESSING state before marking as AVAILABLE"
            )
        
        self.order_status_repo.mark_as_available(order_id)
        
        completed_time = datetime.now(timezone.utc)
        self.order_repo.update_completed_at(order_id, completed_time)
        
        return self.order_repo.get_by_id_or_fail(order_id)

    def mark_order_as_cancelled(self, order_id: int) -> Order:
        if not order_id:
            raise OrderStatusUpdateException("order_id is required")
        
        order = self.order_repo.get_by_id_or_fail(order_id)
        
        order_status = self.order_status_repo.get_by_id_or_fail(order_id)
        
        if order_status.order_status == OrderStatusEnum.AVAILABLE:
            raise InvalidOrderStateException(
                f"Order {order_id} cannot be cancelled. Document is already available."
            )
        
        self.order_status_repo.mark_as_cancelled(order_id)
        
        return self.order_repo.get_by_id_or_fail(order_id)

    def update_admin_notes(self, order_id: int, admin_notes: str) -> Order:
        if not order_id:
            raise OrderServiceException("order_id is required")
        
        order = self.order_repo.get_by_id_or_fail(order_id)
        order.admin_notes = admin_notes
        
        return self.order_repo.update(order)

    def get_pending_orders(self, limit: int = 100) -> list[Order]:
        if limit <= 0:
            raise OrderServiceException("limit must be positive")
        
        return self.order_repo.get_pending_orders(limit)

    def get_orders_by_status(self, status: OrderStatusEnum) -> list[Order]:
        if not status:
            raise OrderServiceException("status is required")
        
        return self.order_repo.get_orders_by_status(status)

    def get_orders_by_payment_status(self, payment_status: PaymentStatus) -> list[Order]:
        if not payment_status:
            raise OrderServiceException("payment_status is required")
        
        return self.order_repo.get_orders_by_payment_status(payment_status)

    def get_industry_specific_orders(self) -> list[Order]:
        return self.order_repo.get_industry_specific_orders()

    def get_orders_by_jurisdiction(self, jurisdiction: str) -> list[Order]:
        if not jurisdiction:
            raise OrderServiceException("jurisdiction is required")
        
        self.validation_service.validate_jurisdiction(jurisdiction)
        
        return self.order_repo.get_orders_by_jurisdiction(jurisdiction)

    def calculate_order_total(self, plan_id: int, is_industry_specific: bool = False) -> Decimal:
        if not plan_id:
            raise OrderServiceException("plan_id is required")
        
        plan = self.plan_repo.get_by_id_or_fail(plan_id)
        
        total = Decimal(plan.base_price)
        
        if is_industry_specific:
            industry_addon = Decimal("50.00")
            total += industry_addon
        
        return total
