from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.company_logo_repository import CompanyLogoRepository
from app.repositories.user_repository import UserRepository
from app.repositories.plan_repository import PlanRepository
from app.services.validation_service import ValidationService
from app.services.order_service import OrderService
from app.services.file_storage_service import FileStorageService


def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)


def get_order_status_repository(db: Session = Depends(get_db)) -> OrderStatusRepository:
    return OrderStatusRepository(db)


def get_company_repository(db: Session = Depends(get_db)) -> CompanyRepository:
    return CompanyRepository(db)


def get_company_logo_repository(db: Session = Depends(get_db)) -> CompanyLogoRepository:
    return CompanyLogoRepository(db)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_plan_repository(db: Session = Depends(get_db)) -> PlanRepository:
    return PlanRepository(db)


def get_validation_service() -> ValidationService:
    return ValidationService()


def get_file_storage_service() -> FileStorageService:
    return FileStorageService()


def get_order_service(
    order_repo: OrderRepository = Depends(get_order_repository),
    order_status_repo: OrderStatusRepository = Depends(get_order_status_repository),
    company_repo: CompanyRepository = Depends(get_company_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
    validation_service: ValidationService = Depends(get_validation_service),
) -> OrderService:
    return OrderService(
        order_repo,
        order_status_repo,
        company_repo,
        user_repo,
        plan_repo,
        validation_service,
    )
