import pytest
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.order import Order
from app.models.user import User, UserRole
from app.models.company import Company
from app.models.plan import Plan, PlanSlug, PlanName
from app.models.order_status import OrderStatus, OrderStatusEnum, PaymentStatus
from app.models.industry_intake_response import IndustryIntakeResponse
from app.repositories.order_repository import OrderRepository
from app.repositories.industry_intake_response_repository import IndustryIntakeResponseRepository
from app.repositories.base_repository import RecordNotFoundError
from app.services.industry_intake_service import IndustryIntakeService
from app.services.exceptions import OrderServiceException
from app.schemas.industry_intake import (
    IntakeQuestionsResponse,
    IndustryIntakeAnswersResponse,
    QuestionTier,
    QuestionType,
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
def intake_repo(test_db):
    return IndustryIntakeResponseRepository(test_db)


@pytest.fixture
def intake_service(order_repo, intake_repo):
    return IndustryIntakeService(order_repo, intake_repo)


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
        base_price=Decimal("99.99"),
        description="Basic plan",
    )
    test_db.add(plan)
    test_db.commit()

    order = Order(
        user_id=user.id,
        company_id=company.id,
        plan_id=plan.id,
        jurisdiction="ON",
        total_amount=Decimal("99.99"),
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


class TestGetIntakeQuestions:
    def test_returns_intake_questions_response(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        assert isinstance(result, IntakeQuestionsResponse)

    def test_response_contains_naics_codes(self, intake_service):
        naics_codes = ["236110", "238210"]
        result = intake_service.get_intake_questions(naics_codes)

        assert result.naics_codes == naics_codes

    def test_core_questions_always_present(self, intake_service):
        result = intake_service.get_intake_questions(["999999"])

        assert len(result.core_questions) >= 3

    def test_all_core_questions_have_core_tier(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        for q in result.core_questions:
            assert q.tier == QuestionTier.CORE

    def test_all_conditional_questions_have_conditional_tier(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        for q in result.conditional_questions:
            assert q.tier == QuestionTier.CONDITIONAL

    def test_core_questions_include_worksite_type(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        ids = [q.id for q in result.core_questions]
        assert "worksite_type" in ids

    def test_core_questions_include_headcount_band(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        ids = [q.id for q in result.core_questions]
        assert "headcount_band" in ids

    def test_core_questions_include_high_risk_flags(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        ids = [q.id for q in result.core_questions]
        assert "high_risk_flags" in ids

    def test_core_questions_include_has_subcontractors(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        ids = [q.id for q in result.core_questions]
        assert "has_subcontractors" in ids

    def test_core_questions_include_emergency_readiness(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        ids = [q.id for q in result.core_questions]
        assert "emergency_readiness" in ids

    def test_questions_have_options_for_single_choice(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        single_choice_questions = [
            q for q in result.core_questions
            if q.question_type == QuestionType.SINGLE_CHOICE
        ]
        for q in single_choice_questions:
            assert q.options is not None
            assert len(q.options) > 0

    def test_construction_naics_includes_working_at_heights_flag(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        high_risk_q = next(
            (q for q in result.core_questions if q.id == "high_risk_flags"), None
        )
        assert high_risk_q is not None
        option_values = [o.value for o in high_risk_q.options]
        assert "working_at_heights" in option_values

    def test_manufacturing_naics_includes_chemicals_flag(self, intake_service):
        result = intake_service.get_intake_questions(["311111"])

        high_risk_q = next(
            (q for q in result.core_questions if q.id == "high_risk_flags"), None
        )
        assert high_risk_q is not None
        option_values = [o.value for o in high_risk_q.options]
        assert "chemicals_or_hazardous_materials" in option_values

    def test_high_risk_flags_question_is_multi_choice(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        high_risk_q = next(
            (q for q in result.core_questions if q.id == "high_risk_flags"), None
        )
        assert high_risk_q is not None
        assert high_risk_q.question_type == QuestionType.MULTI_CHOICE

    def test_subcontractors_question_triggers_conditional(self, intake_service):
        result = intake_service.get_intake_questions(["236110"])

        subcontractors_q = next(
            (q for q in result.core_questions if q.id == "has_subcontractors"), None
        )
        assert subcontractors_q is not None
        assert subcontractors_q.triggers_conditional is not None
        assert len(subcontractors_q.triggers_conditional) > 0

    def test_multiple_naics_codes_returns_union_of_questions(self, intake_service):
        result_single = intake_service.get_intake_questions(["236110"])
        result_multi = intake_service.get_intake_questions(["236110", "311111"])

        single_ids = {q.id for q in result_single.core_questions}
        multi_ids = {q.id for q in result_multi.core_questions}

        assert single_ids.issubset(multi_ids) or single_ids == multi_ids


class TestSaveIntakeAnswers:
    def test_save_answers_returns_response(self, intake_service, sample_order):
        answers = {"worksite_type": "field", "headcount_band": "5-19"}

        result = intake_service.save_intake_answers(sample_order.id, answers)

        assert isinstance(result, IndustryIntakeAnswersResponse)
        assert result.order_id == sample_order.id

    def test_save_answers_persists_answers(self, intake_service, sample_order):
        answers = {
            "worksite_type": "field",
            "headcount_band": "5-19",
            "high_risk_flags": ["working_at_heights"],
            "has_subcontractors": True,
        }

        result = intake_service.save_intake_answers(sample_order.id, answers)

        assert result.answers["worksite_type"] == "field"
        assert result.answers["headcount_band"] == "5-19"
        assert result.answers["high_risk_flags"] == ["working_at_heights"]
        assert result.answers["has_subcontractors"] is True

    def test_save_answers_overwrites_previous(self, intake_service, sample_order):
        intake_service.save_intake_answers(sample_order.id, {"worksite_type": "office"})

        result = intake_service.save_intake_answers(
            sample_order.id, {"worksite_type": "field", "headcount_band": "20-99"}
        )

        assert result.answers["worksite_type"] == "field"
        assert result.answers["headcount_band"] == "20-99"

    def test_save_answers_raises_when_order_not_found(self, intake_service):
        with pytest.raises(RecordNotFoundError):
            intake_service.save_intake_answers(99999, {"worksite_type": "office"})

    def test_save_answers_raises_when_order_id_missing(self, intake_service):
        with pytest.raises(OrderServiceException, match="order_id is required"):
            intake_service.save_intake_answers(0, {"worksite_type": "office"})

    def test_save_answers_raises_when_answers_empty(self, intake_service, sample_order):
        with pytest.raises(OrderServiceException, match="answers cannot be empty"):
            intake_service.save_intake_answers(sample_order.id, {})

    def test_save_answers_unlocks_conditional_questions_for_subcontractors(
        self, intake_service, sample_order
    ):
        answers = {"has_subcontractors": True}

        result = intake_service.save_intake_answers(sample_order.id, answers)

        assert len(result.conditional_questions_unlocked) > 0

    def test_save_answers_no_conditionals_when_no_triggers(
        self, intake_service, sample_order
    ):
        answers = {
            "worksite_type": "office",
            "headcount_band": "1-4",
            "has_subcontractors": False,
            "has_chemicals": False,
        }

        result = intake_service.save_intake_answers(sample_order.id, answers)

        assert result.conditional_questions_unlocked == []


class TestGetIntakeAnswers:
    def test_get_answers_returns_saved_answers(self, intake_service, sample_order):
        answers = {"worksite_type": "mixed", "headcount_band": "100+"}
        intake_service.save_intake_answers(sample_order.id, answers)

        result = intake_service.get_intake_answers(sample_order.id)

        assert isinstance(result, IndustryIntakeAnswersResponse)
        assert result.order_id == sample_order.id
        assert result.answers == answers

    def test_get_answers_raises_when_no_answers_saved(self, intake_service, sample_order):
        with pytest.raises(RecordNotFoundError):
            intake_service.get_intake_answers(sample_order.id)

    def test_get_answers_raises_when_order_not_found(self, intake_service):
        with pytest.raises(RecordNotFoundError):
            intake_service.get_intake_answers(99999)

    def test_get_answers_raises_when_order_id_missing(self, intake_service):
        with pytest.raises(OrderServiceException, match="order_id is required"):
            intake_service.get_intake_answers(0)
