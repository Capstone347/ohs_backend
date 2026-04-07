# Database package initialization
# Import all models here to ensure they're registered with Alembic

# When models are created, import them here:
# from app.models.order import Order
# from app.models.company import Company
# from app.models.document import Document
# etc.
from .plan import Plan, PlanSlug, PlanName
from .company import Company
from .user import User, UserRole
from .order import Order
from .document import Document, DocumentFormat
from .company_logo import CompanyLogo
from .email_log import EmailLog, EmailStatus
from .system_log import SystemLog, LogLevel
from .legal_acknowledgment import LegalAcknowledgement
from .industry_profile import IndustryProfile
from .industry_naics_code import IndustryNAICSCode
from .naics_code import NAICSCode
from .naics_user_content import NAICSUserContent
from .order_status import OrderStatus, OrderStatusEnum, PaymentStatus
from .industry_intake_response import IndustryIntakeResponse
from .auth_otp_request import AuthOtpRequest
from .sjp_generation_job import SjpGenerationJob, SjpGenerationStatus
from .admin_user import AdminUser, AdminRole
from .sjp_toc_entry import SjpTocEntry
from .sjp_content import SjpContent, SjpContentStatus
from .llm_usage_log import LlmUsageLog, LlmUsageStage

__all__ = [
    "Plan",
    "PlanSlug",
    "PlanName",
    "Company",
    "User",
    "UserRole",
    "Order",
    "Document",
    "DocumentFormat",
    "CompanyLogo",
    "EmailLog",
    "EmailStatus",
    "SystemLog",
    "LogLevel",
    "LegalAcknowledgement",
    "IndustryProfile",
    "IndustryNAICSCode",
    "NAICSCode",
    "NAICSUserContent",
    "OrderStatus",
    "OrderStatusEnum",
    "PaymentStatus",
    "IndustryIntakeResponse",
    "AuthOtpRequest",
    "SjpGenerationJob",
    "SjpGenerationStatus",
    "AdminUser",
    "AdminRole",
    "SjpTocEntry",
    "SjpContent",
    "SjpContentStatus",
    "LlmUsageLog",
    "LlmUsageStage",
]