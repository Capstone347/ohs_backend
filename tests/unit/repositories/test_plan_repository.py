import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.plan import Plan, PlanSlug, PlanName
from app.repositories.plan_repository import PlanRepository
from app.repositories.base_repository import RecordNotFoundError, DuplicateRecordError


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def plan_repo(test_db):
    return PlanRepository(test_db)


class TestPlanRepository:
    def test_create_plan(self, plan_repo):
        plan = plan_repo.create_plan(
            slug=PlanSlug.BASIC,
            name=PlanName.BASIC,
            base_price=99.99,
            description="Basic OHS manual"
        )
        
        assert plan.id is not None
        assert plan.slug == PlanSlug.BASIC
        assert plan.name == PlanName.BASIC
        assert float(plan.base_price) == 99.99
        assert plan.description == "Basic OHS manual"

    def test_create_plan_duplicate_slug_fails(self, plan_repo):
        plan_repo.create_plan(
            slug=PlanSlug.BASIC,
            name=PlanName.BASIC,
            base_price=99.99
        )
        
        with pytest.raises(DuplicateRecordError, match="already exists"):
            plan_repo.create_plan(
                slug=PlanSlug.BASIC,
                name=PlanName.BASIC,
                base_price=149.99
            )

    def test_get_by_slug(self, plan_repo):
        created_plan = plan_repo.create_plan(
            slug=PlanSlug.COMPREHENSIVE,
            name=PlanName.COMPREHENSIVE,
            base_price=199.99
        )
        
        retrieved_plan = plan_repo.get_by_slug(PlanSlug.COMPREHENSIVE)
        
        assert retrieved_plan is not None
        assert retrieved_plan.id == created_plan.id
        assert retrieved_plan.slug == PlanSlug.COMPREHENSIVE

    def test_get_by_slug_not_found_returns_none(self, plan_repo):
        result = plan_repo.get_by_slug(PlanSlug.BASIC)
        assert result is None

    def test_get_by_slug_or_fail_raises_when_not_found(self, plan_repo):
        with pytest.raises(RecordNotFoundError, match="not found"):
            plan_repo.get_by_slug_or_fail(PlanSlug.BASIC)

    def test_get_by_name(self, plan_repo):
        plan_repo.create_plan(
            slug=PlanSlug.BASIC,
            name=PlanName.BASIC,
            base_price=99.99
        )
        
        retrieved_plan = plan_repo.get_by_name(PlanName.BASIC)
        
        assert retrieved_plan is not None
        assert retrieved_plan.name == PlanName.BASIC

    def test_get_all_plans(self, plan_repo):
        plan_repo.create_plan(
            slug=PlanSlug.BASIC,
            name=PlanName.BASIC,
            base_price=99.99
        )
        plan_repo.create_plan(
            slug=PlanSlug.COMPREHENSIVE,
            name=PlanName.COMPREHENSIVE,
            base_price=199.99
        )
        
        plans = plan_repo.get_all_plans()
        
        assert len(plans) == 2
        assert plans[0].base_price < plans[1].base_price

    def test_update_base_price(self, plan_repo):
        plan = plan_repo.create_plan(
            slug=PlanSlug.BASIC,
            name=PlanName.BASIC,
            base_price=99.99
        )
        
        updated_plan = plan_repo.update_base_price(plan.id, 149.99)
        
        assert float(updated_plan.base_price) == 149.99

    def test_update_description(self, plan_repo):
        plan = plan_repo.create_plan(
            slug=PlanSlug.BASIC,
            name=PlanName.BASIC,
            base_price=99.99,
            description="Old description"
        )
        
        updated_plan = plan_repo.update_description(plan.id, "New description")
        
        assert updated_plan.description == "New description"

    def test_slug_exists(self, plan_repo):
        plan_repo.create_plan(
            slug=PlanSlug.BASIC,
            name=PlanName.BASIC,
            base_price=99.99
        )
        
        assert plan_repo.slug_exists(PlanSlug.BASIC) is True
        assert plan_repo.slug_exists(PlanSlug.COMPREHENSIVE) is False

    def test_get_basic_plan(self, plan_repo):
        plan_repo.create_plan(
            slug=PlanSlug.BASIC,
            name=PlanName.BASIC,
            base_price=99.99
        )
        
        basic_plan = plan_repo.get_basic_plan()
        
        assert basic_plan is not None
        assert basic_plan.slug == PlanSlug.BASIC

    def test_get_comprehensive_plan(self, plan_repo):
        plan_repo.create_plan(
            slug=PlanSlug.COMPREHENSIVE,
            name=PlanName.COMPREHENSIVE,
            base_price=199.99
        )
        
        comprehensive_plan = plan_repo.get_comprehensive_plan()
        
        assert comprehensive_plan is not None
        assert comprehensive_plan.slug == PlanSlug.COMPREHENSIVE

    def test_get_plans_by_price_range(self, plan_repo):
        plan_repo.create_plan(
            slug=PlanSlug.BASIC,
            name=PlanName.BASIC,
            base_price=99.99
        )
        plan_repo.create_plan(
            slug=PlanSlug.COMPREHENSIVE,
            name=PlanName.COMPREHENSIVE,
            base_price=199.99
        )
        
        plans = plan_repo.get_plans_by_price_range(90.00, 150.00)
        
        assert len(plans) == 1
        assert plans[0].slug == PlanSlug.BASIC

    def test_create_plan_with_negative_price_fails(self, plan_repo):
        with pytest.raises(ValueError, match="cannot be negative"):
            plan_repo.create_plan(
                slug=PlanSlug.BASIC,
                name=PlanName.BASIC,
                base_price=-10.00
            )

    def test_get_plans_by_price_range_invalid_range_fails(self, plan_repo):
        with pytest.raises(ValueError, match="must be less than or equal to"):
            plan_repo.get_plans_by_price_range(200.00, 100.00)

    def test_create_plan_without_slug_fails(self, plan_repo):
        with pytest.raises(ValueError, match="slug is required"):
            plan_repo.create_plan(
                slug=None,
                name=PlanName.BASIC,
                base_price=99.99
            )
