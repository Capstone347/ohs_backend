from uuid import uuid4
from app.models.sjp_generation_job import SjpGenerationJob, SjpGenerationStatus
from app.models.order_status import PaymentStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.sjp_generation_job_repository import SjpGenerationJobRepository
from app.repositories.base_repository import RecordNotFoundError
from app.services.exceptions import ServiceException


class SjpGenerationServiceException(ServiceException):
    """Base exception for SJP generation service errors."""
    pass


class OrderNotFound(SjpGenerationServiceException):
    """Order not found or does not belong to user."""
    pass


class InvalidOrderState(SjpGenerationServiceException):
    """Order is not in a valid state for SJP generation."""
    pass


class MissingIndustryProfile(SjpGenerationServiceException):
    """Order lacks required industry profile data."""
    pass


class SjpGenerationService:
    """Service for managing SJP generation jobs for paid industry-specific orders."""

    def __init__(
        self,
        order_repo: OrderRepository,
        sjp_job_repo: SjpGenerationJobRepository,
    ):
        self.order_repo = order_repo
        self.sjp_job_repo = sjp_job_repo

    def start_generation(
        self,
        order_id: int,
        user_id: int,
        idempotency_key: str | None = None,
    ) -> SjpGenerationJob:
        """
        Initiate SJP generation for a paid industry-specific order.

        Args:
            order_id: ID of the order to generate SJP for
            user_id: ID of the authenticated user (for ownership validation)
            idempotency_key: Optional unique key for idempotent requests. 
                           Auto-generated if omitted.

        Returns:
            SjpGenerationJob: The created or existing generation job

        Raises:
            OrderNotFound: If order doesn't exist or doesn't belong to user
            InvalidOrderState: If order is not paid or not industry-specific
            MissingIndustryProfile: If industry profile is missing required data
        """
        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = str(uuid4())

        # Check if job already exists by idempotency_key (idempotency)
        existing_job = self.sjp_job_repo.get_by_idempotency_key(idempotency_key)
        if existing_job:
            return existing_job

        # Validate order exists and belongs to user
        try:
            order = self.order_repo.get_by_id(order_id)
        except RecordNotFoundError:
            raise OrderNotFound(f"Order {order_id} not found")

        if not order:
            raise OrderNotFound(f"Order {order_id} not found")

        if order.user_id != user_id:
            raise OrderNotFound(f"Order {order_id} does not belong to user {user_id}")

        # Validate order is paid
        if not order.order_status or order.order_status.payment_status != PaymentStatus.PAID.value:
            raise InvalidOrderState(f"Order {order_id} is not paid. Current payment status: {order.order_status.payment_status if order.order_status else 'unknown'}")

        # Validate order is industry-specific
        if not order.is_industry_specific:
            raise InvalidOrderState(f"Order {order_id} is not industry-specific")

        # Validate industry profile exists with required data
        if not order.company or not order.company.industry_profile:
            raise MissingIndustryProfile(f"Order {order_id} is missing industry profile")

        industry_profile = order.company.industry_profile
        if not industry_profile.province:
            raise MissingIndustryProfile(f"Order {order_id} industry profile is missing province")

        if not industry_profile.naics_codes or len(industry_profile.naics_codes) == 0:
            raise MissingIndustryProfile(f"Order {order_id} industry profile is missing NAICS codes")

        # Extract NAICS codes from relationship
        naics_codes = [code.code for code in industry_profile.naics_codes]

        # Create new SJP generation job
        job = SjpGenerationJob(
            order_id=order_id,
            province=industry_profile.province,
            naics_codes=naics_codes,
            business_description=industry_profile.business_description,
            status=SjpGenerationStatus.PENDING.value,
            idempotency_key=idempotency_key,
        )

        job = self.sjp_job_repo.create(job)

        # TODO: Kick off async generation here (e.g., queue task, emit event, etc.)

        return job
