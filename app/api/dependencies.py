from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.company_logo_repository import CompanyLogoRepository
from app.repositories.user_repository import UserRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.industry_profile_repository import IndustryProfileRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.legal_acknowledgment_repository import LegalAcknowledgmentRepository
from app.services.order_service import OrderService
from app.services.validation_service import ValidationService
from app.services.file_storage_service import FileStorageService
from app.services.document_generation_service import DocumentGenerationService
from app.services.preview_service import PreviewService
from app.services.document_service import DocumentService
from app.services.legal_service import LegalService


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


def get_industry_profile_repository(db: Session = Depends(get_db)) -> IndustryProfileRepository:
    return IndustryProfileRepository(db)


def get_document_repository(db: Session = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


def get_legal_acknowledgment_repository(db: Session = Depends(get_db)) -> LegalAcknowledgmentRepository:
    return LegalAcknowledgmentRepository(db)


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




def get_document_generation_service(
    order_repo: OrderRepository = Depends(get_order_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    file_storage_service: FileStorageService = Depends(get_file_storage_service),
) -> DocumentGenerationService:
    return DocumentGenerationService(
        order_repo,
        document_repo,
        file_storage_service,
    )


def get_preview_service(
    document_repo: DocumentRepository = Depends(get_document_repository),
    file_storage_service: FileStorageService = Depends(get_file_storage_service),
) -> PreviewService:
    return PreviewService(
        document_repo,
        file_storage_service,
    )


def get_document_service(
    document_repo: DocumentRepository = Depends(get_document_repository),
    order_repo: OrderRepository = Depends(get_order_repository),
    file_storage_service: FileStorageService = Depends(get_file_storage_service),
    document_generation_service: DocumentGenerationService = Depends(get_document_generation_service),
    preview_service: PreviewService = Depends(get_preview_service),
) -> DocumentService:
    return DocumentService(
        document_repo,
        order_repo,
        file_storage_service,
        document_generation_service,
        preview_service,
    )


def get_legal_service(
    legal_acknowledgment_repo: LegalAcknowledgmentRepository = Depends(get_legal_acknowledgment_repository),
    order_repo: OrderRepository = Depends(get_order_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
) -> LegalService:
    return LegalService(
        legal_acknowledgment_repo,
        order_repo,
        plan_repo,
    )