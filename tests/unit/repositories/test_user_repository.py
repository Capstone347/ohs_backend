import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.repositories.base_repository import RecordNotFoundError, DuplicateRecordError


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def user_repo(test_db):
    return UserRepository(test_db)


class TestUserRepository:
    def test_create_user(self, user_repo):
        user = user_repo.create_user(
            email="test@example.com",
            full_name="Test User",
            role=UserRole.CUSTOMER
        )
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.CUSTOMER
        assert user.created_at is not None

    def test_create_user_duplicate_email_fails(self, user_repo):
        user_repo.create_user(
            email="test@example.com",
            full_name="Test User"
        )
        
        with pytest.raises(DuplicateRecordError, match="already exists"):
            user_repo.create_user(
                email="test@example.com",
                full_name="Another User"
            )

    def test_get_by_email(self, user_repo):
        created_user = user_repo.create_user(
            email="test@example.com",
            full_name="Test User"
        )
        
        retrieved_user = user_repo.get_by_email("test@example.com")
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email

    def test_get_by_email_not_found_returns_none(self, user_repo):
        result = user_repo.get_by_email("nonexistent@example.com")
        assert result is None

    def test_get_by_email_or_fail_raises_when_not_found(self, user_repo):
        with pytest.raises(RecordNotFoundError, match="not found"):
            user_repo.get_by_email_or_fail("nonexistent@example.com")

    def test_email_exists(self, user_repo):
        user_repo.create_user(
            email="test@example.com",
            full_name="Test User"
        )
        
        assert user_repo.email_exists("test@example.com") is True
        assert user_repo.email_exists("nonexistent@example.com") is False

    def test_update_last_login(self, user_repo):
        user = user_repo.create_user(
            email="test@example.com",
            full_name="Test User"
        )
        
        login_time = datetime.now(timezone.utc)
        updated_user = user_repo.update_last_login(user.id, login_time)
        
        assert updated_user.last_login == login_time

    def test_set_otp_token(self, user_repo):
        user = user_repo.create_user(
            email="test@example.com",
            full_name="Test User"
        )
        
        otp_token = "123456"
        otp_expires = datetime.now(timezone.utc)
        
        updated_user = user_repo.set_otp_token(user.id, otp_token, otp_expires)
        
        assert updated_user.otp_token == otp_token
        assert updated_user.otp_expires == otp_expires

    def test_clear_otp_token(self, user_repo):
        user = user_repo.create_user(
            email="test@example.com",
            full_name="Test User"
        )
        
        otp_expires = datetime.now(timezone.utc)
        user_repo.set_otp_token(user.id, "123456", otp_expires)
        
        updated_user = user_repo.clear_otp_token(user.id)
        
        assert updated_user.otp_token is None
        assert updated_user.otp_expires is None

    def test_verify_otp_success(self, user_repo):
        user = user_repo.create_user(
            email="test@example.com",
            full_name="Test User"
        )
        
        otp_token = "123456"
        otp_expires = datetime(2030, 1, 1)
        user_repo.set_otp_token(user.id, otp_token, otp_expires)
        
        verified_user = user_repo.verify_otp("test@example.com", "123456")
        
        assert verified_user is not None
        assert verified_user.id == user.id

    def test_verify_otp_wrong_token(self, user_repo):
        user = user_repo.create_user(
            email="test@example.com",
            full_name="Test User"
        )
        
        otp_expires = datetime(2030, 1, 1)
        user_repo.set_otp_token(user.id, "123456", otp_expires)
        
        result = user_repo.verify_otp("test@example.com", "wrong")
        
        assert result is None

    def test_verify_otp_expired(self, user_repo):
        user = user_repo.create_user(
            email="test@example.com",
            full_name="Test User"
        )
        
        otp_expires = datetime(2020, 1, 1)
        user_repo.set_otp_token(user.id, "123456", otp_expires)
        
        result = user_repo.verify_otp("test@example.com", "123456")
        
        assert result is None

    def test_get_users_by_role(self, user_repo):
        user_repo.create_user(
            email="admin@example.com",
            full_name="Admin User",
            role=UserRole.ADMIN
        )
        user_repo.create_user(
            email="customer@example.com",
            full_name="Customer User",
            role=UserRole.CUSTOMER
        )
        
        admins = user_repo.get_users_by_role(UserRole.ADMIN)
        customers = user_repo.get_users_by_role(UserRole.CUSTOMER)
        
        assert len(admins) == 1
        assert admins[0].email == "admin@example.com"
        assert len(customers) == 1
        assert customers[0].email == "customer@example.com"

    def test_assign_to_company(self, user_repo):
        user = user_repo.create_user(
            email="test@example.com",
            full_name="Test User"
        )
        
        updated_user = user_repo.assign_to_company(user.id, 123)
        
        assert updated_user.company_id == 123

    def test_create_user_without_email_fails(self, user_repo):
        with pytest.raises(ValueError, match="email is required"):
            user_repo.create_user(email="", full_name="Test User")

    def test_create_user_without_full_name_fails(self, user_repo):
        with pytest.raises(ValueError, match="full_name is required"):
            user_repo.create_user(email="test@example.com", full_name="")
