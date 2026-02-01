import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.user import User, UserRole
from app.repositories.base_repository import BaseRepository, RecordNotFoundError


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def base_repo(test_db):
    return BaseRepository(User, test_db)


class TestBaseRepository:
    def test_create(self, base_repo, test_db):
        user = User(
            email="test@example.com",
            full_name="Test User",
            role=UserRole.CUSTOMER
        )
        
        created_user = base_repo.create(user)
        
        assert created_user.id is not None
        assert created_user.email == "test@example.com"

    def test_get_by_id(self, base_repo, test_db):
        user = User(
            email="test@example.com",
            full_name="Test User",
            role=UserRole.CUSTOMER
        )
        created_user = base_repo.create(user)
        
        retrieved_user = base_repo.get_by_id(created_user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id

    def test_get_by_id_not_found_returns_none(self, base_repo):
        result = base_repo.get_by_id(99999)
        assert result is None

    def test_get_by_id_or_fail(self, base_repo, test_db):
        user = User(
            email="test@example.com",
            full_name="Test User",
            role=UserRole.CUSTOMER
        )
        created_user = base_repo.create(user)
        
        retrieved_user = base_repo.get_by_id_or_fail(created_user.id)
        
        assert retrieved_user.id == created_user.id

    def test_get_by_id_or_fail_raises_when_not_found(self, base_repo):
        with pytest.raises(RecordNotFoundError, match="not found"):
            base_repo.get_by_id_or_fail(99999)

    def test_get_all(self, base_repo, test_db):
        for i in range(5):
            user = User(
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                role=UserRole.CUSTOMER
            )
            base_repo.create(user)
        
        all_users = base_repo.get_all()
        
        assert len(all_users) == 5

    def test_get_all_with_skip_and_limit(self, base_repo, test_db):
        for i in range(10):
            user = User(
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                role=UserRole.CUSTOMER
            )
            base_repo.create(user)
        
        users = base_repo.get_all(skip=2, limit=3)
        
        assert len(users) == 3

    def test_update(self, base_repo, test_db):
        user = User(
            email="test@example.com",
            full_name="Test User",
            role=UserRole.CUSTOMER
        )
        created_user = base_repo.create(user)
        
        created_user.full_name = "Updated Name"
        updated_user = base_repo.update(created_user)
        
        assert updated_user.full_name == "Updated Name"

    def test_delete(self, base_repo, test_db):
        user = User(
            email="test@example.com",
            full_name="Test User",
            role=UserRole.CUSTOMER
        )
        created_user = base_repo.create(user)
        
        base_repo.delete(created_user.id)
        
        result = base_repo.get_by_id(created_user.id)
        assert result is None

    def test_delete_nonexistent_raises(self, base_repo):
        with pytest.raises(RecordNotFoundError, match="not found"):
            base_repo.delete(99999)

    def test_exists(self, base_repo, test_db):
        user = User(
            email="test@example.com",
            full_name="Test User",
            role=UserRole.CUSTOMER
        )
        created_user = base_repo.create(user)
        
        assert base_repo.exists(created_user.id) is True
        assert base_repo.exists(99999) is False

    def test_count(self, base_repo, test_db):
        for i in range(7):
            user = User(
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                role=UserRole.CUSTOMER
            )
            base_repo.create(user)
        
        count = base_repo.count()
        
        assert count == 7

    def test_get_by_id_without_id_fails(self, base_repo):
        with pytest.raises(ValueError, match="record_id is required"):
            base_repo.get_by_id(None)

    def test_create_without_entity_fails(self, base_repo):
        with pytest.raises(ValueError, match="entity cannot be None"):
            base_repo.create(None)

    def test_get_all_with_negative_skip_fails(self, base_repo):
        with pytest.raises(ValueError, match="skip must be non-negative"):
            base_repo.get_all(skip=-1)

    def test_get_all_with_zero_limit_fails(self, base_repo):
        with pytest.raises(ValueError, match="limit must be positive"):
            base_repo.get_all(limit=0)
