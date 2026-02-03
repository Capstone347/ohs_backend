import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.database.base import Base


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_order_request():
    return {
        "plan_id": "basic",
        "user_email": "test@example.com",
        "company_name": "Test Company"
    }


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
