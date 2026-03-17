import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.config import settings
from app.database.base import Base
from app.main import app
from app.models.company import Company
from app.models.document import Document
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


def _hash_otp(otp_code: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        otp_code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _insert_auth_otp_request(db_session: Session, email: str, otp_code: str) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO auth_otp_requests (
                email,
                otp_hash,
                expires_at,
                created_at,
                attempt_count,
                last_sent_at,
                request_ip,
                lockout_until
            ) VALUES (
                :email,
                :otp_hash,
                :expires_at,
                :created_at,
                :attempt_count,
                :last_sent_at,
                :request_ip,
                :lockout_until
            )
            """
        ),
        {
            "email": email,
            "otp_hash": _hash_otp(otp_code),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "created_at": datetime.now(timezone.utc),
            "attempt_count": 0,
            "last_sent_at": datetime.now(timezone.utc),
            "request_ip": "203.0.113.9",
            "lockout_until": None,
        },
    )
    db_session.commit()


@pytest.fixture(scope="function")
def db_session(tmp_path):
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    plan = Plan(
        slug=PlanSlug.BASIC,
        name=PlanName.BASIC,
        base_price=Decimal("99.99"),
        description="Basic plan",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    user_one = User(email="owner1@example.com", full_name="Owner One", role=UserRole.CUSTOMER.value)
    user_two = User(email="owner2@example.com", full_name="Owner Two", role=UserRole.CUSTOMER.value)
    db.add(user_one)
    db.add(user_two)
    db.commit()
    db.refresh(user_one)
    db.refresh(user_two)

    company_one = Company(name="Company One")
    company_two = Company(name="Company Two")
    db.add(company_one)
    db.add(company_two)
    db.commit()
    db.refresh(company_one)
    db.refresh(company_two)

    order_one = Order(
        user_id=user_one.id,
        company_id=company_one.id,
        plan_id=plan.id,
        jurisdiction="ON",
        total_amount=Decimal("99.99"),
        is_industry_specific=False,
    )
    order_two = Order(
        user_id=user_two.id,
        company_id=company_two.id,
        plan_id=plan.id,
        jurisdiction="ON",
        total_amount=Decimal("99.99"),
        is_industry_specific=False,
    )
    db.add(order_one)
    db.add(order_two)
    db.commit()
    db.refresh(order_one)
    db.refresh(order_two)

    order_status_one = OrderStatus(
        order_id=order_one.id,
        order_status=OrderStatusEnum.DRAFT.value,
        payment_status=PaymentStatus.PENDING.value,
    )
    order_status_two = OrderStatus(
        order_id=order_two.id,
        order_status=OrderStatusEnum.DRAFT.value,
        payment_status=PaymentStatus.PENDING.value,
    )
    db.add(order_status_one)
    db.add(order_status_two)

    document_one_path = tmp_path / f"order_{order_one.id}.docx"
    document_one_path.write_bytes(b"order one")
    document_two_path = tmp_path / f"order_{order_two.id}.docx"
    document_two_path.write_bytes(b"order two")

    doc_one = Document(
        order_id=order_one.id,
        access_token="a" * 64,
        token_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        file_path=str(document_one_path),
        file_format="docx",
    )
    doc_two = Document(
        order_id=order_two.id,
        access_token="b" * 64,
        token_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        file_path=str(document_two_path),
        file_format="docx",
    )
    db.add(doc_one)
    db.add(doc_two)
    db.commit()

    yield {
        "db": db,
        "order_one_id": order_one.id,
        "order_two_id": order_two.id,
        "owner_one_email": user_one.email,
        "owner_two_email": user_two.email,
        "owner_one_token": doc_one.access_token,
        "owner_two_token": doc_two.access_token,
    }

    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _authenticate(client: TestClient, db_session: Session, email: str) -> None:
    otp_code = "123456"
    _insert_auth_otp_request(db_session, email, otp_code)
    verify_response = client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": otp_code})
    assert verify_response.status_code == 200


def test_order_summary_requires_authentication(client: TestClient, db_session):
    response = client.get(f"/api/v1/orders/{db_session['order_one_id']}/summary")
    assert response.status_code == 401


def test_order_documents_requires_authentication(client: TestClient, db_session):
    response = client.get(f"/api/v1/orders/{db_session['order_one_id']}/documents")
    assert response.status_code == 401


def test_order_download_link_requires_authentication(client: TestClient, db_session):
    response = client.get(
        f"/api/v1/orders/{db_session['order_one_id']}/download",
        params={"token": db_session["owner_one_token"]},
    )
    assert response.status_code == 401


def test_orders_are_scoped_to_authenticated_user(client: TestClient, db_session):
    _authenticate(client, db_session["db"], db_session["owner_one_email"])

    own_response = client.get(f"/api/v1/orders/{db_session['order_one_id']}/summary")
    other_response = client.get(f"/api/v1/orders/{db_session['order_two_id']}/summary")

    assert own_response.status_code == 200
    assert other_response.status_code in {403, 404}


def test_document_endpoints_are_scoped_to_authenticated_user(client: TestClient, db_session):
    _authenticate(client, db_session["db"], db_session["owner_one_email"])

    own_documents_response = client.get(f"/api/v1/orders/{db_session['order_one_id']}/documents")
    other_documents_response = client.get(f"/api/v1/orders/{db_session['order_two_id']}/documents")

    assert own_documents_response.status_code == 200
    assert isinstance(own_documents_response.json(), list)
    assert other_documents_response.status_code in {403, 404}

    own_download_response = client.get(
        f"/api/v1/orders/{db_session['order_one_id']}/download",
        params={"token": db_session["owner_one_token"]},
    )
    other_download_response = client.get(
        f"/api/v1/orders/{db_session['order_two_id']}/download",
        params={"token": db_session["owner_two_token"]},
    )

    assert own_download_response.status_code == 200
    assert other_download_response.status_code in {403, 404}

