from fastapi import Cookie, Depends, HTTPException, Request, status
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
from app.repositories.industry_intake_response_repository import IndustryIntakeResponseRepository
from app.repositories.email_log_repository import EmailLogRepository
from app.repositories.auth_otp_request_repository import AuthOtpRequestRepository
from app.repositories.sjp_generation_job_repository import SjpGenerationJobRepository
from app.repositories.sjp_toc_entry_repository import SjpTocEntryRepository
from app.repositories.sjp_content_repository import SjpContentRepository
from app.services.order_service import OrderService
from app.services.sjp_generation_service import SjpGenerationService
from app.services.validation_service import ValidationService
from app.services.file_storage_service import FileStorageService
from app.services.document_generation_service import DocumentGenerationService
from app.services.preview_service import PreviewService
from app.services.document_service import DocumentService
from app.services.legal_service import LegalService
from app.services.industry_intake_service import IndustryIntakeService
from app.services.email_service import EmailService
from app.services.email_template_renderer import EmailTemplateRenderer
from app.services.payment_service import PaymentService
from app.services.auth_service import AuthService
from app.services.stripe_provider import StripePaymentProvider
from app.services.order_fulfillment_service import OrderFulfillmentService
from app.services.admin_order_service import AdminOrderService
from app.services.admin_auth_service import AdminAuthService
from app.services.llm_provider import OpenAiLlmProvider
from app.services.jurisdiction_service import JurisdictionService
from app.repositories.admin_user_repository import AdminUserRepository
from app.repositories.llm_usage_log_repository import LlmUsageLogRepository
from app.models.admin_user import AdminRole
from app.config import settings


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


def get_email_log_repository(db: Session = Depends(get_db)) -> EmailLogRepository:
    return EmailLogRepository(db)


def get_auth_otp_request_repository(db: Session = Depends(get_db)) -> AuthOtpRequestRepository:
    return AuthOtpRequestRepository(db)


def get_sjp_generation_job_repository(db: Session = Depends(get_db)) -> SjpGenerationJobRepository:
    return SjpGenerationJobRepository(db)


def get_sjp_toc_entry_repository(db: Session = Depends(get_db)) -> SjpTocEntryRepository:
    return SjpTocEntryRepository(db)


def get_sjp_content_repository(db: Session = Depends(get_db)) -> SjpContentRepository:
    return SjpContentRepository(db)


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


def get_industry_intake_response_repository(
    db: Session = Depends(get_db),
) -> IndustryIntakeResponseRepository:
    return IndustryIntakeResponseRepository(db)


def get_industry_intake_service(
    order_repo: OrderRepository = Depends(get_order_repository),
    intake_repo: IndustryIntakeResponseRepository = Depends(get_industry_intake_response_repository),
) -> IndustryIntakeService:
    return IndustryIntakeService(order_repo, intake_repo)


def get_llm_provider() -> OpenAiLlmProvider:
    return OpenAiLlmProvider(
        api_key=settings.openai_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )


def get_jurisdiction_service() -> JurisdictionService:
    return JurisdictionService()


def get_llm_usage_log_repository(db: Session = Depends(get_db)) -> LlmUsageLogRepository:
    return LlmUsageLogRepository(db)


def get_sjp_toc_generator(
    llm_provider: OpenAiLlmProvider = Depends(get_llm_provider),
    jurisdiction_service: JurisdictionService = Depends(get_jurisdiction_service),
) -> "SjpTocGenerator":
    from app.services.sjp_toc_generator import SjpTocGenerator
    return SjpTocGenerator(llm_provider, jurisdiction_service)


def get_sjp_content_generator(
    llm_provider: OpenAiLlmProvider = Depends(get_llm_provider),
    jurisdiction_service: JurisdictionService = Depends(get_jurisdiction_service),
) -> "SjpContentGenerator":
    from app.services.sjp_content_generator import SjpContentGenerator
    return SjpContentGenerator(llm_provider, jurisdiction_service)


def get_sjp_generation_service(
    order_repo: OrderRepository = Depends(get_order_repository),
    sjp_job_repo: SjpGenerationJobRepository = Depends(get_sjp_generation_job_repository),
    sjp_toc_entry_repo: SjpTocEntryRepository = Depends(get_sjp_toc_entry_repository),
    sjp_content_repo: SjpContentRepository = Depends(get_sjp_content_repository),
    llm_usage_log_repo: LlmUsageLogRepository = Depends(get_llm_usage_log_repository),
    order_status_repo: OrderStatusRepository = Depends(get_order_status_repository),
    toc_generator: "SjpTocGenerator" = Depends(get_sjp_toc_generator),
    content_generator: "SjpContentGenerator" = Depends(get_sjp_content_generator),
) -> SjpGenerationService:
    return SjpGenerationService(
        order_repo=order_repo,
        sjp_job_repo=sjp_job_repo,
        sjp_toc_entry_repo=sjp_toc_entry_repo,
        sjp_content_repo=sjp_content_repo,
        llm_usage_log_repo=llm_usage_log_repo,
        order_status_repo=order_status_repo,
        toc_generator=toc_generator,
        content_generator=content_generator,
    )


def get_sjp_document_service(
    sjp_job_repo: SjpGenerationJobRepository = Depends(get_sjp_generation_job_repository),
    sjp_toc_entry_repo: SjpTocEntryRepository = Depends(get_sjp_toc_entry_repository),
    sjp_content_repo: SjpContentRepository = Depends(get_sjp_content_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    file_storage_service: FileStorageService = Depends(get_file_storage_service),
    jurisdiction_service: JurisdictionService = Depends(get_jurisdiction_service),
) -> "SjpDocumentService":
    from app.services.sjp_document_service import SjpDocumentService
    return SjpDocumentService(
        sjp_job_repo, sjp_toc_entry_repo, sjp_content_repo,
        document_repo, file_storage_service, jurisdiction_service,
    )


def get_email_template_renderer() -> EmailTemplateRenderer:
    return EmailTemplateRenderer()


def get_email_service(
    email_log_repo: EmailLogRepository = Depends(get_email_log_repository),
) -> EmailService:
    return EmailService(email_log_repo, settings)


def get_auth_service(
    auth_otp_request_repo: AuthOtpRequestRepository = Depends(get_auth_otp_request_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    email_service: EmailService = Depends(get_email_service),
    email_template_renderer: EmailTemplateRenderer = Depends(get_email_template_renderer),
) -> AuthService:
    return AuthService(
        auth_otp_request_repo=auth_otp_request_repo,
        user_repo=user_repo,
        email_service=email_service,
        email_template_renderer=email_template_renderer,
        settings=settings,
    )


def get_authenticated_user_context(
    request: Request,
    auth_session: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, int | str]:
    try:
        user_data = auth_service.get_authenticated_user(auth_session)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth session",
        )

    request.state.user_id = user_data["id"]
    request.state.user_email = user_data["email"]
    return user_data


def get_order_fulfillment_service(
    order_repo: OrderRepository = Depends(get_order_repository),
    order_status_repo: OrderStatusRepository = Depends(get_order_status_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    document_service: DocumentService = Depends(get_document_service),
    email_service: EmailService = Depends(get_email_service),
    renderer: EmailTemplateRenderer = Depends(get_email_template_renderer),
    sjp_document_service: "SjpDocumentService" = Depends(get_sjp_document_service),
    sjp_job_repo: SjpGenerationJobRepository = Depends(get_sjp_generation_job_repository),
) -> OrderFulfillmentService:
    return OrderFulfillmentService(
        order_repo,
        order_status_repo,
        document_repo,
        document_service,
        email_service,
        renderer,
        sjp_document_service,
        sjp_job_repo,
    )


def get_admin_order_service(
    order_repo: OrderRepository = Depends(get_order_repository),
    order_status_repo: OrderStatusRepository = Depends(get_order_status_repository),
    fulfillment_service: OrderFulfillmentService = Depends(get_order_fulfillment_service),
    sjp_job_repo: SjpGenerationJobRepository = Depends(get_sjp_generation_job_repository),
) -> AdminOrderService:
    return AdminOrderService(order_repo, order_status_repo, fulfillment_service, sjp_job_repo)


def get_admin_user_repository(db: Session = Depends(get_db)) -> AdminUserRepository:
    return AdminUserRepository(db)


def get_admin_auth_service(
    admin_user_repo: AdminUserRepository = Depends(get_admin_user_repository),
) -> AdminAuthService:
    return AdminAuthService(
        admin_user_repo=admin_user_repo,
        settings=settings,
    )


def get_authenticated_admin_context(
    request: Request,
    admin_session: str | None = Cookie(default=None),
    admin_auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> dict[str, int | str]:
    try:
        admin_data = admin_auth_service.get_authenticated_admin(admin_session)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin session",
        )

    request.state.admin_id = admin_data["id"]
    request.state.admin_email = admin_data["email"]
    return admin_data


def get_owner_admin_context(
    admin_context: dict[str, int | str] = Depends(get_authenticated_admin_context),
) -> dict[str, int | str]:
    if admin_context.get("role") != AdminRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required",
        )
    return admin_context


def get_stripe_payment_provider() -> StripePaymentProvider:
    if not settings.stripe_api_key:
        raise ValueError("STRIPE_API_KEY is not configured")
    
    return StripePaymentProvider(
        api_key=settings.stripe_api_key,
        webhook_secret=settings.stripe_webhook_secret
    )


def get_payment_service(
    provider: StripePaymentProvider = Depends(get_stripe_payment_provider),
) -> PaymentService:
    return PaymentService(provider=provider)
