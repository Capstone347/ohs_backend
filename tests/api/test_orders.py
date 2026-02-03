import io
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db, get_file_storage_service
from app.database.base import Base
from app.main import app
from app.models.company import Company
from app.models.order import Order
from app.models.order_status import OrderStatus, OrderStatusEnum, PaymentStatus
from app.models.plan import Plan, PlanName, PlanSlug
from app.models.user import User, UserRole
from app.services.file_storage_service import FileStorageService

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


def override_file_storage_service(tmp_path: Path) -> FileStorageService:
    return FileStorageService(base_data_dir=tmp_path)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session, tmp_path: Path):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_file_storage_service] = lambda: override_file_storage_service(tmp_path)
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_plan(db_session):
    plan = Plan(
        slug=PlanSlug.BASIC,
        name=PlanName.BASIC,
        base_price=Decimal("199.99"),
        description="Basic plan",
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def sample_user(db_session):
    user = User(
        email="existing@example.com",
        full_name="Existing User",
        role=UserRole.CUSTOMER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_company(db_session):
    company = Company(name="Test Company")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def sample_order(db_session, sample_user, sample_company, sample_plan):
    order = Order(
        user_id=sample_user.id,
        company_id=sample_company.id,
        plan_id=sample_plan.id,
        jurisdiction="ON",
        total_amount=Decimal("199.99"),
        is_industry_specific=False,
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


def test_create_order_success(client, sample_plan):
    request_data = {
        "plan_id": sample_plan.id,
        "user_email": "newuser@example.com",
        "full_name": "New User",
        "jurisdiction": "ON",
    }
    response = client.post("/api/v1/orders", json=request_data)
    assert response.status_code == 201
    data = response.json()
    assert "order_id" in data
    assert data["status"] == OrderStatusEnum.DRAFT.value
    assert data["message"] == "Order created successfully"


def test_create_order_plan_not_found(client):
    request_data = {
        "plan_id": 999,
        "user_email": "newuser@example.com",
        "full_name": "New User",
        "jurisdiction": "ON",
    }
    response = client.post("/api/v1/orders", json=request_data)
    assert response.status_code == 404


def test_update_company_details_success_without_logo(client, sample_order):
    form_data = {
        "company_name": "Updated Company",
        "province": "ON",
        "naics_codes": "123456,234567",
    }
    response = client.patch(
        f"/api/v1/orders/{sample_order.id}/company-details",
        data=form_data,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == sample_order.id
    assert data["company"]["name"] == "Updated Company"


def test_update_company_details_success_with_logo(client, sample_order):
    form_data = {
        "company_name": "Company With Logo",
        "province": "ON",
        "naics_codes": "123456",
    }
    logo_content = b"fake image content"
    files = {
        "logo": ("test_logo.png", io.BytesIO(logo_content), "image/png"),
    }
    response = client.patch(
        f"/api/v1/orders/{sample_order.id}/company-details",
        data=form_data,
        files=files,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["company"]["name"] == "Company With Logo"
    assert data["company"]["logo_id"] is not None


def test_update_company_details_order_not_found(client):
    form_data = {
        "company_name": "Updated Company",
        "province": "ON",
        "naics_codes": "123456",
    }
    response = client.patch(
        "/api/v1/orders/999/company-details",
        data=form_data,
    )
    assert response.status_code == 404


def test_get_order_summary_success(client, sample_order):
    response = client.get(f"/api/v1/orders/{sample_order.id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == sample_order.id
    assert data["user_email"] == sample_order.user.email
    assert data["full_name"] == sample_order.user.full_name
    assert data["order_status"] == OrderStatusEnum.DRAFT.value
    assert data["payment_status"] == PaymentStatus.PENDING.value


def test_get_order_summary_order_not_found(client):
    response = client.get("/api/v1/orders/999/summary")
    assert response.status_code == 404
