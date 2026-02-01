import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.order import Order
from app.models.user import User, UserRole
from app.models.company import Company
from app.models.plan import Plan, PlanSlug, PlanName
from app.models.order_status import OrderStatus, OrderStatusEnum, PaymentStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.base_repository import RecordNotFoundError


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
def sample_user(test_db):
    user = User(
        email="test@example.com",
        full_name="Test User",
        role=UserRole.CUSTOMER,
        created_at=datetime.utcnow()
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_company(test_db):
    company = Company(name="Test Company")
    test_db.add(company)
    test_db.commit()
    test_db.refresh(company)
    return company


@pytest.fixture
def sample_plan(test_db):
    plan = Plan(
        slug=PlanSlug.BASIC,
        name=PlanName.BASIC,
        base_price=100.00,
        description="Basic plan"
    )
    test_db.add(plan)
    test_db.commit()
    test_db.refresh(plan)
    return plan


@pytest.fixture
def sample_order(test_db, sample_user, sample_company, sample_plan):
    order = Order(
        user_id=sample_user.id,
        company_id=sample_company.id,
        plan_id=sample_plan.id,
        jurisdiction="Ontario",
        total_amount=100.00,
        created_at=datetime.utcnow()
    )
    test_db.add(order)
    test_db.commit()
    test_db.refresh(order)
    
    order_status = OrderStatus(
        order_id=order.id,
        order_status=OrderStatusEnum.DRAFT,
        payment_status=PaymentStatus.PENDING
    )
    test_db.add(order_status)
    test_db.commit()
    
    return order


class TestOrderRepository:
    def test_create_order(self, order_repo, sample_user, sample_company, sample_plan):
        order = Order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="Ontario",
            total_amount=150.00,
            created_at=datetime.utcnow()
        )
        
        created_order = order_repo.create(order)
        
        assert created_order.id is not None
        assert created_order.user_id == sample_user.id
        assert created_order.company_id == sample_company.id
        assert created_order.plan_id == sample_plan.id
        assert created_order.jurisdiction == "Ontario"
        assert float(created_order.total_amount) == 150.00

    def test_get_by_id(self, order_repo, sample_order):
        retrieved_order = order_repo.get_by_id(sample_order.id)
        
        assert retrieved_order is not None
        assert retrieved_order.id == sample_order.id

    def test_get_by_id_or_fail_raises_when_not_found(self, order_repo):
        with pytest.raises(RecordNotFoundError, match="not found"):
            order_repo.get_by_id_or_fail(99999)

    def test_get_orders_by_user_id(self, order_repo, sample_order, sample_user):
        orders = order_repo.get_orders_by_user_id(sample_user.id)
        
        assert len(orders) == 1
        assert orders[0].id == sample_order.id

    def test_get_orders_by_company_id(self, order_repo, sample_order, sample_company):
        orders = order_repo.get_orders_by_company_id(sample_company.id)
        
        assert len(orders) == 1
        assert orders[0].id == sample_order.id

    def test_get_orders_by_status(self, order_repo, sample_order):
        orders = order_repo.get_orders_by_status(OrderStatusEnum.DRAFT)
        
        assert len(orders) == 1
        assert orders[0].id == sample_order.id

    def test_get_orders_by_payment_status(self, order_repo, sample_order):
        orders = order_repo.get_orders_by_payment_status(PaymentStatus.PENDING)
        
        assert len(orders) == 1
        assert orders[0].id == sample_order.id

    def test_update_completed_at(self, order_repo, sample_order):
        completed_time = datetime.utcnow()
        updated_order = order_repo.update_completed_at(sample_order.id, completed_time)
        
        assert updated_order.completed_at == completed_time

    def test_get_pending_orders(self, order_repo, sample_order):
        pending_orders = order_repo.get_pending_orders()
        
        assert len(pending_orders) == 1
        assert pending_orders[0].id == sample_order.id

    def test_get_industry_specific_orders(
        self, 
        order_repo, 
        test_db,
        sample_user, 
        sample_company, 
        sample_plan
    ):
        industry_order = Order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=sample_plan.id,
            jurisdiction="Ontario",
            total_amount=200.00,
            is_industry_specific=True,
            created_at=datetime.utcnow()
        )
        order_repo.create(industry_order)
        
        industry_orders = order_repo.get_industry_specific_orders()
        
        assert len(industry_orders) == 1
        assert industry_orders[0].is_industry_specific is True

    def test_get_orders_by_jurisdiction(self, order_repo, sample_order):
        orders = order_repo.get_orders_by_jurisdiction("Ontario")
        
        assert len(orders) == 1
        assert orders[0].jurisdiction == "Ontario"

    def test_get_completed_orders_by_date_range(
        self, 
        order_repo, 
        sample_order
    ):
        completed_time = datetime.utcnow()
        order_repo.update_completed_at(sample_order.id, completed_time)
        
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2030, 1, 1)
        
        orders = order_repo.get_completed_orders_by_date_range(start_date, end_date)
        
        assert len(orders) == 1
        assert orders[0].id == sample_order.id

    def test_get_completed_orders_by_date_range_invalid_range_fails(self, order_repo):
        start_date = datetime(2030, 1, 1)
        end_date = datetime(2020, 1, 1)
        
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            order_repo.get_completed_orders_by_date_range(start_date, end_date)

    def test_get_orders_by_user_id_without_id_fails(self, order_repo):
        with pytest.raises(ValueError, match="user_id is required"):
            order_repo.get_orders_by_user_id(None)

    def test_get_orders_by_status_without_status_fails(self, order_repo):
        with pytest.raises(ValueError, match="status is required"):
            order_repo.get_orders_by_status(None)
