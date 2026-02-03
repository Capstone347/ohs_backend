import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.order import Order
from app.models.user import User, UserRole
from app.models.company import Company
from app.models.plan import Plan, PlanSlug, PlanName
from app.models.order_status import OrderStatus, OrderStatusEnum, PaymentStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.user_repository import UserRepository
from app.repositories.plan_repository import PlanRepository
from app.services.order_service import OrderService
from app.services.validation_service import ValidationService
from app.services.exceptions import (
    OrderNotCreatedException,
    OrderStatusUpdateException,
    InvalidOrderStateException,
    OrderServiceException,
)


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def order_repo(test_db):
    return OrderRepository(test_db)


@pytest.fixture
def order_status_repo(test_db):
    return OrderStatusRepository(test_db)


@pytest.fixture
def company_repo(test_db):
    return CompanyRepository(test_db)


@pytest.fixture
def user_repo(test_db):
    return UserRepository(test_db)


@pytest.fixture
def plan_repo(test_db):
    return PlanRepository(test_db)


@pytest.fixture
def validation_service():
    return ValidationService()


@pytest.fixture
def order_service(order_repo, order_status_repo, company_repo, user_repo, plan_repo, validation_service):
    return OrderService(
        order_repo,
        order_status_repo,
        company_repo,
        user_repo,
        plan_repo,
        validation_service,
    )


@pytest.fixture
def sample_user(user_repo):
    return user_repo.create_user(
        email="test@example.com",
        full_name="Test User",
        role=UserRole.CUSTOMER,
    )


@pytest.fixture
def sample_company(company_repo):
    return company_repo.create_company(name="Test Company")


@pytest.fixture
def sample_plan(plan_repo):
    return plan_repo.create_plan(
        slug=PlanSlug.BASIC,
        name=PlanName.BASIC,
        base_price=99.99,
        description="Basic plan",
    )


class TestOrderService:
    def test_create_order(self, order_service, sample_user, sample_company, sample_plan):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        assert order.id is not None
        assert order.user_id == sample_user.id
        assert order.company_id == sample_company.id
        assert order.plan_id == sample_plan.id
        assert order.jurisdiction == "ON"
        assert order.total_amount == Decimal("99.99")
        assert order.is_industry_specific is False

    def test_create_order_with_industry_specific(self, order_service, sample_user, sample_company, sample_plan):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="BC",
            total_amount=Decimal("149.99"),
            is_industry_specific=True,
        )
        
        assert order.is_industry_specific is True

    def test_create_order_creates_order_status(self, order_service, order_status_repo, sample_user, sample_company, sample_plan):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        order_status = order_status_repo.get_by_id(order.id)
        
        assert order_status is not None
        assert order_status.order_id == order.id
        assert order_status.order_status == OrderStatusEnum.DRAFT
        assert order_status.payment_status == PaymentStatus.PENDING

    def test_create_order_without_user_id_fails(self, order_service, sample_company, sample_plan):
        with pytest.raises(OrderNotCreatedException, match="user_id is required"):
            order_service.create_order(
                user_id=None,
                company_id=sample_company.id,
                plan_id=sample_plan.id,
                jurisdiction="ON",
                total_amount=Decimal("99.99"),
            )

    def test_create_order_without_company_id_fails(self, order_service, sample_user, sample_plan):
        with pytest.raises(OrderNotCreatedException, match="company_id is required"):
            order_service.create_order(
                user_id=sample_user.id,
                company_id=None,
                plan_id=sample_plan.id,
                jurisdiction="ON",
                total_amount=Decimal("99.99"),
            )

    def test_create_order_with_zero_amount_fails(self, order_service, sample_user, sample_company, sample_plan):
        with pytest.raises(OrderNotCreatedException, match="must be greater than zero"):
            order_service.create_order(
                user_id=sample_user.id,
                company_id=sample_company.id,
                plan_id=sample_plan.id,
                jurisdiction="ON",
                total_amount=Decimal("0"),
            )

    def test_create_order_with_invalid_jurisdiction_fails(self, order_service, sample_user, sample_company, sample_plan):
        from app.services.exceptions import InvalidProvinceException
        with pytest.raises(InvalidProvinceException):
            order_service.create_order(
                user_id=sample_user.id,
                company_id=sample_company.id,
                plan_id=sample_plan.id,
                jurisdiction="XX",
                total_amount=Decimal("99.99"),
            )

    def test_get_order(self, order_service, sample_user, sample_company, sample_plan):
        created_order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        retrieved_order = order_service.get_order(created_order.id)
        
        assert retrieved_order.id == created_order.id

    def test_get_order_with_relations(self, order_service, sample_user, sample_company, sample_plan):
        created_order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        order = order_service.get_order_with_relations(created_order.id)
        
        assert order.user is not None
        assert order.company is not None
        assert order.plan is not None

    def test_get_orders_by_user(self, order_service, sample_user, sample_company, sample_plan):
        order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        orders = order_service.get_orders_by_user(sample_user.id)
        
        assert len(orders) == 1
        assert orders[0].user_id == sample_user.id

    def test_mark_order_as_paid(self, order_service, sample_user, sample_company, sample_plan, order_status_repo):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        updated_order = order_service.mark_order_as_paid(order.id, "stripe")
        
        order_status = order_status_repo.get_by_id(order.id)
        assert order_status.payment_status == PaymentStatus.PAID
        assert order_status.payment_provider == "stripe"

    def test_mark_order_as_paid_twice_fails(self, order_service, sample_user, sample_company, sample_plan):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        order_service.mark_order_as_paid(order.id, "stripe")
        
        with pytest.raises(InvalidOrderStateException, match="already marked as paid"):
            order_service.mark_order_as_paid(order.id, "stripe")

    def test_mark_order_as_processing(self, order_service, sample_user, sample_company, sample_plan, order_status_repo):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        order_service.mark_order_as_paid(order.id, "stripe")
        order_service.mark_order_as_processing(order.id)
        
        order_status = order_status_repo.get_by_id(order.id)
        assert order_status.order_status == OrderStatusEnum.PROCESSING

    def test_mark_order_as_processing_without_payment_fails(self, order_service, sample_user, sample_company, sample_plan):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        with pytest.raises(InvalidOrderStateException, match="Payment must be completed"):
            order_service.mark_order_as_processing(order.id)

    def test_mark_order_as_available(self, order_service, sample_user, sample_company, sample_plan, order_status_repo):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        order_service.mark_order_as_paid(order.id, "stripe")
        order_service.mark_order_as_processing(order.id)
        order_service.mark_order_as_available(order.id)
        
        order_status = order_status_repo.get_by_id(order.id)
        assert order_status.order_status == OrderStatusEnum.AVAILABLE
        
        updated_order = order_service.get_order(order.id)
        assert updated_order.completed_at is not None

    def test_mark_order_as_available_without_processing_fails(self, order_service, sample_user, sample_company, sample_plan):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        order_service.mark_order_as_paid(order.id, "stripe")
        
        with pytest.raises(InvalidOrderStateException, match="must be in PROCESSING state"):
            order_service.mark_order_as_available(order.id)

    def test_mark_order_as_cancelled(self, order_service, sample_user, sample_company, sample_plan, order_status_repo):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        order_service.mark_order_as_cancelled(order.id)
        
        order_status = order_status_repo.get_by_id(order.id)
        assert order_status.order_status == OrderStatusEnum.CANCELLED

    def test_mark_order_as_cancelled_when_available_fails(self, order_service, sample_user, sample_company, sample_plan):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        order_service.mark_order_as_paid(order.id, "stripe")
        order_service.mark_order_as_processing(order.id)
        order_service.mark_order_as_available(order.id)
        
        with pytest.raises(InvalidOrderStateException, match="cannot be cancelled"):
            order_service.mark_order_as_cancelled(order.id)

    def test_update_admin_notes(self, order_service, sample_user, sample_company, sample_plan):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        updated_order = order_service.update_admin_notes(order.id, "Special requirements noted")
        
        assert updated_order.admin_notes == "Special requirements noted"

    def test_calculate_order_total_basic(self, order_service, sample_plan):
        total = order_service.calculate_order_total(sample_plan.id)
        
        assert total == Decimal("99.99")

    def test_calculate_order_total_with_industry_specific(self, order_service, sample_plan):
        total = order_service.calculate_order_total(sample_plan.id, is_industry_specific=True)
        
        assert total == Decimal("149.99")

    def test_get_orders_by_status(self, order_service, sample_user, sample_company, sample_plan):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="ON",
            total_amount=Decimal("99.99"),
        )
        
        orders = order_service.get_orders_by_status(OrderStatusEnum.DRAFT)
        
        assert len(orders) == 1
        assert orders[0].id == order.id

    def test_get_orders_by_jurisdiction(self, order_service, sample_user, sample_company, sample_plan):
        order = order_service.create_order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="BC",
            total_amount=Decimal("99.99"),
        )
        
        orders = order_service.get_orders_by_jurisdiction("BC")
        
        assert len(orders) == 1
        assert orders[0].jurisdiction == "BC"
