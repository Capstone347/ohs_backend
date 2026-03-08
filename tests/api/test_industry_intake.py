import pytest
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.database.base import Base
from app.main import app
from app.models.company import Company
from app.models.industry_intake_response import IndustryIntakeResponse
from app.models.order import Order
from app.models.order_status import OrderStatus, OrderStatusEnum, PaymentStatus
from app.models.plan import Plan, PlanName, PlanSlug
from app.models.user import User, UserRole

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_order(db_session):
    user = User(
        email="test@example.com",
        full_name="Test User",
        role=UserRole.CUSTOMER,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()

    company = Company(name="Test Company")
    db_session.add(company)
    db_session.commit()

    plan = Plan(
        slug=PlanSlug.BASIC,
        name=PlanName.BASIC,
        base_price=Decimal("99.99"),
        description="Basic plan",
    )
    db_session.add(plan)
    db_session.commit()

    order = Order(
        user_id=user.id,
        company_id=company.id,
        plan_id=plan.id,
        jurisdiction="ON",
        total_amount=Decimal("99.99"),
        created_at=datetime.now(timezone.utc),
        is_industry_specific=True,
    )
    db_session.add(order)
    db_session.commit()

    order_status = OrderStatus(
        order_id=order.id,
        order_status=OrderStatusEnum.DRAFT,
        payment_status=PaymentStatus.PENDING,
    )
    db_session.add(order_status)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def sample_order_with_answers(db_session, sample_order):
    record = IndustryIntakeResponse(
        order_id=sample_order.id,
        answers={
            "worksite_type": "field",
            "headcount_band": "5-19",
            "high_risk_flags": ["working_at_heights"],
            "has_subcontractors": True,
        },
    )
    db_session.add(record)
    db_session.commit()
    return sample_order


class TestGetIntakeQuestionsEndpoint:
    def test_returns_200_with_valid_naics(self, client):
        response = client.get("/api/v1/industry/intake-questions?naics=236110")

        assert response.status_code == 200

    def test_response_contains_naics_codes(self, client):
        response = client.get("/api/v1/industry/intake-questions?naics=236110,238210")
        data = response.json()

        assert "naics_codes" in data
        assert "236110" in data["naics_codes"]
        assert "238210" in data["naics_codes"]

    def test_response_contains_core_questions(self, client):
        response = client.get("/api/v1/industry/intake-questions?naics=236110")
        data = response.json()

        assert "core_questions" in data
        assert len(data["core_questions"]) >= 3

    def test_response_contains_conditional_questions(self, client):
        response = client.get("/api/v1/industry/intake-questions?naics=236110")
        data = response.json()

        assert "conditional_questions" in data

    def test_returns_400_when_naics_missing(self, client):
        response = client.get("/api/v1/industry/intake-questions")

        assert response.status_code == 422

    def test_returns_400_for_invalid_naics_code(self, client):
        response = client.get("/api/v1/industry/intake-questions?naics=12345")

        assert response.status_code == 400

    def test_returns_400_for_non_numeric_naics(self, client):
        response = client.get("/api/v1/industry/intake-questions?naics=abcdef")

        assert response.status_code == 400

    def test_returns_400_for_empty_naics_string(self, client):
        response = client.get("/api/v1/industry/intake-questions?naics=")

        assert response.status_code == 400

    def test_multiple_naics_codes_accepted(self, client):
        response = client.get(
            "/api/v1/industry/intake-questions?naics=236110,238210,311111"
        )

        assert response.status_code == 200

    def test_question_shape_has_required_fields(self, client):
        response = client.get("/api/v1/industry/intake-questions?naics=236110")
        data = response.json()

        for q in data["core_questions"]:
            assert "id" in q
            assert "tier" in q
            assert "question_type" in q
            assert "text" in q


class TestSaveIntakeAnswersEndpoint:
    def test_returns_200_on_success(self, client, sample_order):
        payload = {"answers": {"worksite_type": "field", "headcount_band": "5-19"}}

        response = client.put(
            f"/api/v1/industry/{sample_order.id}/intake-answers", json=payload
        )

        assert response.status_code == 200

    def test_response_contains_order_id(self, client, sample_order):
        payload = {"answers": {"worksite_type": "office"}}

        response = client.put(
            f"/api/v1/industry/{sample_order.id}/intake-answers", json=payload
        )
        data = response.json()

        assert data["order_id"] == sample_order.id

    def test_response_contains_answers(self, client, sample_order):
        payload = {
            "answers": {
                "worksite_type": "mixed",
                "headcount_band": "100+",
                "has_subcontractors": False,
            }
        }

        response = client.put(
            f"/api/v1/industry/{sample_order.id}/intake-answers", json=payload
        )
        data = response.json()

        assert data["answers"]["worksite_type"] == "mixed"
        assert data["answers"]["headcount_band"] == "100+"

    def test_response_contains_conditional_questions_unlocked(self, client, sample_order):
        payload = {"answers": {"has_subcontractors": True}}

        response = client.put(
            f"/api/v1/industry/{sample_order.id}/intake-answers", json=payload
        )
        data = response.json()

        assert "conditional_questions_unlocked" in data

    def test_second_save_overwrites_first(self, client, sample_order):
        client.put(
            f"/api/v1/industry/{sample_order.id}/intake-answers",
            json={"answers": {"worksite_type": "office"}},
        )

        response = client.put(
            f"/api/v1/industry/{sample_order.id}/intake-answers",
            json={"answers": {"worksite_type": "field"}},
        )
        data = response.json()

        assert data["answers"]["worksite_type"] == "field"

    def test_returns_404_when_order_not_found(self, client):
        payload = {"answers": {"worksite_type": "office"}}

        response = client.put(
            "/api/v1/industry/99999/intake-answers", json=payload
        )

        assert response.status_code == 404

    def test_returns_422_when_answers_missing_from_body(self, client, sample_order):
        response = client.put(
            f"/api/v1/industry/{sample_order.id}/intake-answers", json={}
        )

        assert response.status_code == 422


class TestGetIntakeAnswersEndpoint:
    def test_returns_200_when_answers_exist(self, client, sample_order_with_answers):
        response = client.get(
            f"/api/v1/industry/{sample_order_with_answers.id}/intake-answers"
        )

        assert response.status_code == 200

    def test_response_contains_saved_answers(self, client, sample_order_with_answers):
        response = client.get(
            f"/api/v1/industry/{sample_order_with_answers.id}/intake-answers"
        )
        data = response.json()

        assert data["answers"]["worksite_type"] == "field"
        assert data["answers"]["headcount_band"] == "5-19"
        assert data["answers"]["has_subcontractors"] is True

    def test_returns_404_when_no_answers_saved(self, client, sample_order):
        response = client.get(
            f"/api/v1/industry/{sample_order.id}/intake-answers"
        )

        assert response.status_code == 404

    def test_returns_404_when_order_not_found(self, client):
        response = client.get("/api/v1/industry/99999/intake-answers")

        assert response.status_code == 404

    def test_response_shape_has_required_fields(self, client, sample_order_with_answers):
        response = client.get(
            f"/api/v1/industry/{sample_order_with_answers.id}/intake-answers"
        )
        data = response.json()

        assert "order_id" in data
        assert "answers" in data
        assert "conditional_questions_unlocked" in data
