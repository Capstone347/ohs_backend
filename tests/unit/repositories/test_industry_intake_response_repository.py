import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.order import Order
from app.models.user import User, UserRole
from app.models.company import Company
from app.models.plan import Plan, PlanSlug, PlanName
from app.models.order_status import OrderStatus, OrderStatusEnum, PaymentStatus
from app.models.industry_intake_response import IndustryIntakeResponse
from app.repositories.industry_intake_response_repository import IndustryIntakeResponseRepository
from app.repositories.base_repository import RecordNotFoundError


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def intake_repo(test_db):
    return IndustryIntakeResponseRepository(test_db)


@pytest.fixture
def sample_order(test_db):
    user = User(
        email="test@example.com",
        full_name="Test User",
        role=UserRole.CUSTOMER,
        created_at=datetime.now(timezone.utc),
    )
    test_db.add(user)
    test_db.commit()

    company = Company(name="Test Company")
    test_db.add(company)
    test_db.commit()

    plan = Plan(
        slug=PlanSlug.BASIC,
        name=PlanName.BASIC,
        base_price=99.99,
        description="Basic plan",
    )
    test_db.add(plan)
    test_db.commit()

    order = Order(
        user_id=user.id,
        company_id=company.id,
        plan_id=plan.id,
        jurisdiction="ON",
        total_amount=99.99,
        created_at=datetime.now(timezone.utc),
        is_industry_specific=True,
    )
    test_db.add(order)
    test_db.commit()

    order_status = OrderStatus(
        order_id=order.id,
        order_status=OrderStatusEnum.DRAFT,
        payment_status=PaymentStatus.PENDING,
    )
    test_db.add(order_status)
    test_db.commit()
    test_db.refresh(order)
    return order


class TestIndustryIntakeResponseRepository:
    def test_upsert_creates_new_record(self, intake_repo, sample_order):
        answers = {"worksite_type": "field", "headcount_band": "5-19"}

        record = intake_repo.upsert(sample_order.id, answers)

        assert record.id is not None
        assert record.order_id == sample_order.id
        assert record.answers == answers

    def test_upsert_updates_existing_record(self, intake_repo, sample_order):
        initial_answers = {"worksite_type": "office"}
        intake_repo.upsert(sample_order.id, initial_answers)

        updated_answers = {"worksite_type": "field", "headcount_band": "20-99"}
        record = intake_repo.upsert(sample_order.id, updated_answers)

        assert record.answers == updated_answers

    def test_upsert_does_not_create_duplicate(self, intake_repo, sample_order):
        intake_repo.upsert(sample_order.id, {"worksite_type": "office"})
        intake_repo.upsert(sample_order.id, {"worksite_type": "field"})

        all_records = (
            intake_repo.db.query(IndustryIntakeResponse)
            .filter(IndustryIntakeResponse.order_id == sample_order.id)
            .all()
        )
        assert len(all_records) == 1

    def test_get_by_order_id_returns_record(self, intake_repo, sample_order):
        answers = {"worksite_type": "mixed"}
        intake_repo.upsert(sample_order.id, answers)

        record = intake_repo.get_by_order_id(sample_order.id)

        assert record is not None
        assert record.order_id == sample_order.id
        assert record.answers == answers

    def test_get_by_order_id_returns_none_when_missing(self, intake_repo):
        result = intake_repo.get_by_order_id(99999)
        assert result is None

    def test_get_by_order_id_or_fail_raises_when_missing(self, intake_repo):
        with pytest.raises(RecordNotFoundError, match="order 99999 not found"):
            intake_repo.get_by_order_id_or_fail(99999)

    def test_get_by_order_id_or_fail_returns_record(self, intake_repo, sample_order):
        answers = {"worksite_type": "office"}
        intake_repo.upsert(sample_order.id, answers)

        record = intake_repo.get_by_order_id_or_fail(sample_order.id)

        assert record.order_id == sample_order.id

    def test_upsert_requires_order_id(self, intake_repo):
        with pytest.raises(ValueError, match="order_id is required"):
            intake_repo.upsert(0, {"worksite_type": "office"})

    def test_upsert_requires_answers(self, intake_repo, sample_order):
        with pytest.raises(ValueError, match="answers is required"):
            intake_repo.upsert(sample_order.id, None)

    def test_get_by_order_id_requires_order_id(self, intake_repo):
        with pytest.raises(ValueError, match="order_id is required"):
            intake_repo.get_by_order_id(0)

    def test_upsert_stores_complex_answers(self, intake_repo, sample_order):
        answers = {
            "worksite_type": "field",
            "headcount_band": "5-19",
            "high_risk_flags": ["working_at_heights", "heavy_equipment"],
            "has_subcontractors": True,
            "has_chemicals": False,
        }

        record = intake_repo.upsert(sample_order.id, answers)

        assert record.answers["high_risk_flags"] == ["working_at_heights", "heavy_equipment"]
        assert record.answers["has_subcontractors"] is True
        assert record.answers["has_chemicals"] is False
