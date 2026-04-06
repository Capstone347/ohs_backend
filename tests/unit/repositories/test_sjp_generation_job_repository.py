import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.company import Company
from app.models.order import Order
from app.models.order_status import OrderStatus, OrderStatusEnum, PaymentStatus
from app.models.plan import Plan, PlanSlug, PlanName
from app.models.sjp_generation_job import SjpGenerationJob, SjpGenerationStatus
from app.models.user import User, UserRole
from app.repositories.base_repository import RecordNotFoundError
from app.repositories.sjp_generation_job_repository import SjpGenerationJobRepository


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def sjp_repo(test_db):
    return SjpGenerationJobRepository(test_db)


@pytest.fixture
def sample_order(test_db):
    user = User(
        email="test@example.com",
        full_name="Test User",
        role="customer",
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
        is_industry_specific=False,
    )
    test_db.add(order)
    test_db.commit()

    order_status = OrderStatus(
        order_id=order.id,
        order_status=OrderStatusEnum.DRAFT.value,
        payment_status=PaymentStatus.PENDING.value,
    )
    test_db.add(order_status)
    test_db.commit()
    test_db.refresh(order)
    return order


@pytest.fixture
def sample_job(test_db, sample_order):
    job = SjpGenerationJob(
        order_id=sample_order.id,
        province="ON",
        naics_codes=["238210", "238220"],
        business_description="Electrical and plumbing contractor",
        status=SjpGenerationStatus.PENDING.value,
        idempotency_key="test-idempotency-key-001",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)
    return job


class TestSjpGenerationJobRepository:
    def test_create_job(self, sjp_repo, sample_order):
        job = SjpGenerationJob(
            order_id=sample_order.id,
            province="BC",
            naics_codes=["236110"],
            status=SjpGenerationStatus.PENDING.value,
            idempotency_key="unique-key-create-001",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        created_job = sjp_repo.create(job)

        assert created_job.id is not None
        assert created_job.order_id == sample_order.id
        assert created_job.province == "BC"
        assert created_job.naics_codes == ["236110"]
        assert created_job.status == SjpGenerationStatus.PENDING.value

    def test_get_by_id_returns_job(self, sjp_repo, sample_job):
        result = sjp_repo.get_by_id(sample_job.id)

        assert result is not None
        assert result.id == sample_job.id

    def test_get_by_id_returns_none_when_missing(self, sjp_repo):
        result = sjp_repo.get_by_id(99999)

        assert result is None

    def test_get_by_id_or_fail_raises_when_missing(self, sjp_repo):
        with pytest.raises(RecordNotFoundError, match="not found"):
            sjp_repo.get_by_id_or_fail(99999)

    def test_get_by_order_id_returns_jobs(self, sjp_repo, sample_order, sample_job):
        second_job = SjpGenerationJob(
            order_id=sample_order.id,
            province="ON",
            naics_codes=["541310"],
            status=SjpGenerationStatus.COMPLETED.value,
            idempotency_key="unique-key-second-001",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        sjp_repo.create(second_job)

        results = sjp_repo.get_by_order_id(sample_order.id)

        assert len(results) == 2
        assert all(j.order_id == sample_order.id for j in results)

    def test_get_by_order_id_returns_empty_list_when_none(self, sjp_repo):
        results = sjp_repo.get_by_order_id(99999)

        assert results == []

    def test_get_by_order_id_orders_by_created_at_desc(self, sjp_repo, sample_order):
        earlier = SjpGenerationJob(
            order_id=sample_order.id,
            province="ON",
            naics_codes=["236110"],
            status=SjpGenerationStatus.PENDING.value,
            idempotency_key="key-earlier",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        later = SjpGenerationJob(
            order_id=sample_order.id,
            province="ON",
            naics_codes=["236110"],
            status=SjpGenerationStatus.COMPLETED.value,
            idempotency_key="key-later",
            created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        sjp_repo.create(earlier)
        sjp_repo.create(later)

        results = sjp_repo.get_by_order_id(sample_order.id)

        assert results[0].idempotency_key == "key-later"
        assert results[1].idempotency_key == "key-earlier"

    def test_get_by_order_id_requires_order_id(self, sjp_repo):
        with pytest.raises(ValueError, match="order_id is required"):
            sjp_repo.get_by_order_id(0)

    def test_get_by_idempotency_key_returns_job(self, sjp_repo, sample_job):
        result = sjp_repo.get_by_idempotency_key("test-idempotency-key-001")

        assert result is not None
        assert result.id == sample_job.id
        assert result.idempotency_key == "test-idempotency-key-001"

    def test_get_by_idempotency_key_returns_none_when_missing(self, sjp_repo):
        result = sjp_repo.get_by_idempotency_key("nonexistent-key")

        assert result is None

    def test_get_by_idempotency_key_requires_key(self, sjp_repo):
        with pytest.raises(ValueError, match="idempotency_key is required"):
            sjp_repo.get_by_idempotency_key("")

    def test_update_job_status(self, sjp_repo, sample_job):
        sample_job.status = SjpGenerationStatus.GENERATING_TOC.value
        sample_job.toc_generated_at = datetime.now(timezone.utc)

        updated = sjp_repo.update(sample_job)

        assert updated.status == SjpGenerationStatus.GENERATING_TOC.value
        assert updated.toc_generated_at is not None

    def test_delete_job(self, sjp_repo, sample_job):
        job_id = sample_job.id

        sjp_repo.delete(job_id)

        assert sjp_repo.get_by_id(job_id) is None

    def test_job_stores_naics_codes_as_list(self, sjp_repo, sample_order):
        naics_codes = ["238210", "238220", "238290"]
        job = SjpGenerationJob(
            order_id=sample_order.id,
            province="AB",
            naics_codes=naics_codes,
            status=SjpGenerationStatus.PENDING.value,
            idempotency_key="key-naics-list-test",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        created = sjp_repo.create(job)

        assert created.naics_codes == naics_codes

    def test_job_stores_nullable_business_description(self, sjp_repo, sample_order):
        job = SjpGenerationJob(
            order_id=sample_order.id,
            province="ON",
            naics_codes=["238210"],
            business_description=None,
            status=SjpGenerationStatus.PENDING.value,
            idempotency_key="key-no-description",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        created = sjp_repo.create(job)

        assert created.business_description is None

    def test_all_status_values_are_valid(self):
        expected_values = {"pending", "generating_toc", "generating_sjps", "completed", "failed"}
        actual_values = {s.value for s in SjpGenerationStatus}

        assert actual_values == expected_values

