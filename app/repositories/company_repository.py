from sqlalchemy.orm import Session, joinedload

from app.models.company import Company
from app.repositories.base_repository import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, db: Session):
        super().__init__(Company, db)

    def get_by_name(self, name: str) -> Company | None:
        if not name:
            raise ValueError("name is required")
        
        return self.db.query(Company).filter(Company.name == name).first()

    def get_by_id_with_users(self, company_id: int) -> Company | None:
        if not company_id:
            raise ValueError("company_id is required")
        
        return (
            self.db.query(Company)
            .options(joinedload(Company.users))
            .filter(Company.id == company_id)
            .first()
        )

    def get_by_id_with_orders(self, company_id: int) -> Company | None:
        if not company_id:
            raise ValueError("company_id is required")
        
        return (
            self.db.query(Company)
            .options(joinedload(Company.orders))
            .filter(Company.id == company_id)
            .first()
        )

    def get_by_id_with_logo(self, company_id: int) -> Company | None:
        if not company_id:
            raise ValueError("company_id is required")
        
        return (
            self.db.query(Company)
            .options(joinedload(Company.logo))
            .filter(Company.id == company_id)
            .first()
        )

    def get_by_id_with_all_relations(self, company_id: int) -> Company | None:
        if not company_id:
            raise ValueError("company_id is required")
        
        return (
            self.db.query(Company)
            .options(
                joinedload(Company.users),
                joinedload(Company.orders),
                joinedload(Company.logo)
            )
            .filter(Company.id == company_id)
            .first()
        )

    def create_company(self, name: str, logo_id: int | None = None) -> Company:
        if not name:
            raise ValueError("name is required")
        
        company = Company(
            name=name,
            logo_id=logo_id
        )
        return self.create(company)

    def update_logo(self, company_id: int, logo_id: int) -> Company:
        if not company_id:
            raise ValueError("company_id is required")
        
        if not logo_id:
            raise ValueError("logo_id is required")
        
        company = self.get_by_id_or_fail(company_id)
        company.logo_id = logo_id
        return self.update(company)

    def update_name(self, company_id: int, name: str) -> Company:
        if not company_id:
            raise ValueError("company_id is required")
        
        if not name:
            raise ValueError("name is required")
        
        company = self.get_by_id_or_fail(company_id)
        company.name = name
        return self.update(company)

    def search_by_name(self, search_term: str, limit: int = 50) -> list[Company]:
        if not search_term:
            raise ValueError("search_term is required")
        
        if limit <= 0:
            raise ValueError("limit must be positive")
        
        search_pattern = f"%{search_term}%"
        return (
            self.db.query(Company)
            .filter(Company.name.like(search_pattern))
            .limit(limit)
            .all()
        )

    def get_companies_with_orders(self) -> list[Company]:
        return (
            self.db.query(Company)
            .join(Company.orders)
            .distinct()
            .all()
        )
