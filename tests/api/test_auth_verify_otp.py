import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.config import settings
from app.database.base import Base
from app.main import app

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


def _insert_otp_request(
    db_session: Session,
    email: str,
    otp_code: str,
    expires_at: datetime,
    attempt_count: int = 0,
) -> None:
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
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
            "attempt_count": attempt_count,
            "last_sent_at": datetime.now(timezone.utc),
            "request_ip": "203.0.113.1",
            "lockout_until": None,
        },
    )
    db_session.commit()


def _get_latest_attempt_count(db_session: Session, email: str) -> int:
    row = db_session.execute(
        text(
            """
            SELECT attempt_count
            FROM auth_otp_requests
            WHERE email = :email
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"email": email},
    ).mappings().first()
    return int(row["attempt_count"]) if row else -1


def _get_user_by_email(db_session: Session, email: str) -> dict | None:
    return db_session.execute(
        text(
            """
            SELECT id, email, created_at, last_login
            FROM users
            WHERE email = :email
            LIMIT 1
            """
        ),
        {"email": email},
    ).mappings().first()


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


def test_verify_otp_valid_code_creates_authenticated_session_and_user(
    client: TestClient,
    db_session: Session,
):
    email = "new-auth-user@example.com"
    otp_code = "123456"
    _insert_otp_request(
        db_session,
        email=email,
        otp_code=otp_code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": email, "otp": otp_code},
    )

    assert response.status_code == 200
    assert "user" in response.json()
    assert response.json()["user"]["email"] == email

    set_cookie_header = response.headers.get("set-cookie", "")
    assert set_cookie_header
    assert "httponly" in set_cookie_header.lower()

    created_user = _get_user_by_email(db_session, email)
    assert created_user is not None


def test_verify_otp_invalid_code_fails_with_generic_error_and_counts_attempt(
    client: TestClient,
    db_session: Session,
):
    email = "verify-invalid@example.com"
    _insert_otp_request(
        db_session,
        email=email,
        otp_code="123456",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": email, "otp": "000000"},
    )

    assert response.status_code == 401
    assert "detail" in response.json()

    latest_attempt_count = _get_latest_attempt_count(db_session, email)
    assert latest_attempt_count == 1


def test_verify_otp_expired_code_fails_with_generic_error(
    client: TestClient,
    db_session: Session,
):
    email = "verify-expired@example.com"
    _insert_otp_request(
        db_session,
        email=email,
        otp_code="123456",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": email, "otp": "123456"},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


def test_verify_otp_reaches_max_attempts_and_invalidates_code(
    client: TestClient,
    db_session: Session,
):
    email = "verify-max-attempts@example.com"
    correct_otp = "123456"

    _insert_otp_request(
        db_session,
        email=email,
        otp_code=correct_otp,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        attempt_count=4,
    )

    wrong_response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": email, "otp": "000000"},
    )
    assert wrong_response.status_code == 401

    subsequent_response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": email, "otp": correct_otp},
    )
    assert subsequent_response.status_code == 401


def test_verify_otp_unknown_email_fails_with_generic_error(client: TestClient):
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "unknown@example.com", "otp": "123456"},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


def test_logout_invalidates_session_cookie(client: TestClient):
    response = client.post(
        "/api/v1/auth/logout",
        cookies={"auth_session": "dummy-session-token"},
    )

    assert response.status_code == 200
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "auth_session=" in set_cookie_header
    assert "max-age=0" in set_cookie_header.lower() or "expires=" in set_cookie_header.lower()

