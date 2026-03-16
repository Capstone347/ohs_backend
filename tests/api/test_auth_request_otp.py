import re
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.database.base import Base
from app.main import app
from app.models.user import User, UserRole

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

GENERIC_RESPONSE = {"message": "If the email is registered, an OTP has been sent."}


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_db_datetime(raw_value: object) -> datetime:
    if isinstance(raw_value, datetime):
        return raw_value
    if isinstance(raw_value, str):
        return datetime.fromisoformat(raw_value)
    raise ValueError(f"unsupported datetime value: {type(raw_value)}")


def _fetch_latest_auth_otp_request(db: Session, email: str) -> dict | None:
    query = text(
        """
        SELECT
            email,
            otp_hash,
            expires_at,
            created_at,
            attempt_count,
            last_sent_at,
            request_ip,
            lockout_until
        FROM auth_otp_requests
        WHERE email = :email
        ORDER BY id DESC
        LIMIT 1
        """
    )
    return db.execute(query, {"email": email}).mappings().first()


def _count_auth_otp_requests(db: Session, email: str) -> int:
    query = text("SELECT COUNT(*) FROM auth_otp_requests WHERE email = :email")
    return int(db.execute(query, {"email": email}).scalar_one())


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session):
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def existing_user(db_session: Session) -> User:
    user = User(
        email="existing@example.com",
        full_name="Existing User",
        role=UserRole.CUSTOMER.value,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_request_otp_existing_email_returns_generic_success(client: TestClient, existing_user: User):
    response = client.post(
        "/api/v1/auth/request-otp",
        json={"email": existing_user.email},
    )

    assert response.status_code == 200
    assert response.json() == GENERIC_RESPONSE


def test_request_otp_unknown_email_returns_same_generic_success(client: TestClient, existing_user: User):
    known_email_response = client.post(
        "/api/v1/auth/request-otp",
        json={"email": existing_user.email},
    )
    unknown_email_response = client.post(
        "/api/v1/auth/request-otp",
        json={"email": "unknown@example.com"},
    )

    assert known_email_response.status_code == unknown_email_response.status_code == 200
    assert known_email_response.json() == unknown_email_response.json() == GENERIC_RESPONSE


def test_request_otp_persists_hashed_otp_with_ttl_and_metadata(
    client: TestClient,
    db_session: Session,
    existing_user: User,
):
    response = client.post(
        "/api/v1/auth/request-otp",
        json={"email": existing_user.email},
    )

    assert response.status_code == 200

    otp_request_row = _fetch_latest_auth_otp_request(db_session, existing_user.email)
    assert otp_request_row is not None

    otp_hash = otp_request_row["otp_hash"]
    assert otp_hash
    assert not re.fullmatch(r"\d{6}", otp_hash)

    created_at = _parse_db_datetime(otp_request_row["created_at"])
    expires_at = _parse_db_datetime(otp_request_row["expires_at"])
    ttl = expires_at - created_at

    assert timedelta(minutes=9, seconds=30) <= ttl <= timedelta(minutes=10, seconds=30)
    assert otp_request_row["attempt_count"] == 0
    assert otp_request_row["last_sent_at"] is not None
    assert otp_request_row["email"] == existing_user.email


def test_request_otp_resend_within_cooldown_keeps_generic_response_and_does_not_create_new_request(
    client: TestClient,
    db_session: Session,
    existing_user: User,
):
    first_response = client.post(
        "/api/v1/auth/request-otp",
        json={"email": existing_user.email},
    )
    second_response = client.post(
        "/api/v1/auth/request-otp",
        json={"email": existing_user.email},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json() == GENERIC_RESPONSE

    request_count = _count_auth_otp_requests(db_session, existing_user.email)
    assert request_count == 1


def test_request_otp_repeated_requests_trigger_lockout_metadata(
    client: TestClient,
    db_session: Session,
    existing_user: User,
):
    for _ in range(6):
        response = client.post(
            "/api/v1/auth/request-otp",
            json={"email": existing_user.email},
        )
        assert response.status_code == 200
        assert response.json() == GENERIC_RESPONSE

        db_session.execute(
            text(
                """
                UPDATE auth_otp_requests
                SET last_sent_at = :cooled_down_at
                WHERE email = :email
                """
            ),
            {
                "email": existing_user.email,
                "cooled_down_at": datetime.utcnow() - timedelta(minutes=2),
            },
        )
        db_session.commit()

    otp_request_row = _fetch_latest_auth_otp_request(db_session, existing_user.email)
    assert otp_request_row is not None
    assert otp_request_row["lockout_until"] is not None


def test_request_otp_enforces_ip_rate_limit_without_account_enumeration(
    client: TestClient,
    db_session: Session,
    existing_user: User,
):
    client_ip = "203.0.113.10"

    for request_index in range(12):
        target_email = existing_user.email if request_index % 2 == 0 else f"unknown{request_index}@example.com"
        response = client.post(
            "/api/v1/auth/request-otp",
            json={"email": target_email},
            headers={"X-Forwarded-For": client_ip},
        )

        assert response.status_code == 200
        assert response.json() == GENERIC_RESPONSE

    otp_request_row = _fetch_latest_auth_otp_request(db_session, existing_user.email)
    assert otp_request_row is not None
    assert otp_request_row["request_ip"] == client_ip
    assert otp_request_row["lockout_until"] is not None

