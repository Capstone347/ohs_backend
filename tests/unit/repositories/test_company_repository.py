import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.repositories.base_repository import RecordNotFoundError


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def company_repo(test_db):
    return CompanyRepository(test_db)


class TestCompanyRepository:
    def test_create_company(self, company_repo):
        company = company_repo.create_company(name="Test Company")
        
        assert company.id is not None
        assert company.name == "Test Company"
        assert company.logo_id is None

    def test_create_company_with_logo(self, company_repo):
        company = company_repo.create_company(name="Test Company", logo_id=123)
        
        assert company.logo_id == 123

    def test_get_by_name(self, company_repo):
        created_company = company_repo.create_company(name="Unique Company")
        
        retrieved_company = company_repo.get_by_name("Unique Company")
        
        assert retrieved_company is not None
        assert retrieved_company.id == created_company.id

    def test_get_by_name_not_found_returns_none(self, company_repo):
        result = company_repo.get_by_name("Nonexistent Company")
        assert result is None

    def test_update_logo(self, company_repo):
        company = company_repo.create_company(name="Test Company")
        
        updated_company = company_repo.update_logo(company.id, 456)
        
        assert updated_company.logo_id == 456

    def test_update_name(self, company_repo):
        company = company_repo.create_company(name="Old Name")
        
        updated_company = company_repo.update_name(company.id, "New Name")
        
        assert updated_company.name == "New Name"

    def test_search_by_name(self, company_repo):
        company_repo.create_company(name="ABC Corporation")
        company_repo.create_company(name="ABC Industries")
        company_repo.create_company(name="XYZ Company")
        
        results = company_repo.search_by_name("ABC")
        
        assert len(results) == 2
        assert all("ABC" in company.name for company in results)

    def test_search_by_name_case_insensitive(self, company_repo):
        company_repo.create_company(name="Test Company")
        
        results = company_repo.search_by_name("test")
        
        assert len(results) == 1

    def test_search_by_name_with_limit(self, company_repo):
        for i in range(10):
            company_repo.create_company(name=f"Company {i}")
        
        results = company_repo.search_by_name("Company", limit=5)
        
        assert len(results) == 5

    def test_get_by_id_or_fail_raises_when_not_found(self, company_repo):
        with pytest.raises(RecordNotFoundError, match="not found"):
            company_repo.get_by_id_or_fail(99999)

    def test_create_company_without_name_fails(self, company_repo):
        with pytest.raises(ValueError, match="name is required"):
            company_repo.create_company(name="")

    def test_update_name_without_name_fails(self, company_repo):
        company = company_repo.create_company(name="Test Company")
        
        with pytest.raises(ValueError, match="name is required"):
            company_repo.update_name(company.id, "")

    def test_search_by_name_without_term_fails(self, company_repo):
        with pytest.raises(ValueError, match="search_term is required"):
            company_repo.search_by_name("")
