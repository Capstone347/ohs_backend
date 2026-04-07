from datetime import datetime, timezone
from threading import Thread
from uuid import uuid4
from app.models.sjp_content import SjpContentStatus
from app.models.sjp_generation_job import SjpGenerationJob, SjpGenerationStatus
from app.models.order_status import PaymentStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.sjp_content_repository import SjpContentRepository
from app.repositories.sjp_generation_job_repository import SjpGenerationJobRepository
from app.repositories.sjp_toc_entry_repository import SjpTocEntryRepository
from app.repositories.base_repository import RecordNotFoundError
from app.database.session import SessionLocal
from app.schemas.sjp import (
    SjpGenerationStatusResponse,
    SjpProgressSummaryResponse,
    SjpTocEntryStatusResponse,
)
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


class SjpGenerationJobNotFound(SjpGenerationServiceException):
    """Generation job does not exist for this order."""
    pass


class SjpGenerationService:
    """Service for managing SJP generation jobs for paid industry-specific orders."""

    def __init__(
        self,
        order_repo: OrderRepository,
        sjp_job_repo: SjpGenerationJobRepository,
        sjp_toc_entry_repo: SjpTocEntryRepository,
        sjp_content_repo: SjpContentRepository,
    ):
        self.order_repo = order_repo
        self.sjp_job_repo = sjp_job_repo
        self.sjp_toc_entry_repo = sjp_toc_entry_repo
        self.sjp_content_repo = sjp_content_repo

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

        # Check if job already exists for this order or idempotency key
        existing_job = self._get_existing_job(order_id, idempotency_key)
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

        self._kickoff_async_generation(job.id)

        return job

    def _get_existing_job(self, order_id: int, idempotency_key: str) -> SjpGenerationJob | None:
        existing_jobs = self.sjp_job_repo.get_by_order_id(order_id)
        if existing_jobs:
            return existing_jobs[0]

        existing_job = self.sjp_job_repo.get_by_idempotency_key(idempotency_key)
        if existing_job and existing_job.order_id == order_id:
            return existing_job

        return None

    def _kickoff_async_generation(self, job_id: int) -> None:
        def run_generation() -> None:
            db = SessionLocal()
            try:
                job_repo = SjpGenerationJobRepository(db)
                job = job_repo.get_by_id(job_id)
                if not job:
                    return

                job.status = SjpGenerationStatus.GENERATING_TOC.value
                job.updated_at = datetime.now(timezone.utc)
                job_repo.update(job)
            finally:
                db.close()

        Thread(target=run_generation, daemon=True).start()

    def get_generation_status(self, order_id: int, user_id: int) -> SjpGenerationStatusResponse:
        order = self.order_repo.get_by_id(order_id)
        if not order or order.user_id != user_id:
            raise OrderNotFound(f"Order {order_id} not found")

        jobs = self.sjp_job_repo.get_by_order_id(order_id)
        if not jobs:
            raise SjpGenerationJobNotFound(f"No SJP generation job found for order {order_id}")

        latest_job = jobs[0]
        toc_entries = self.sjp_toc_entry_repo.get_by_job_id(latest_job.id)

        toc_ids = [entry.id for entry in toc_entries]
        contents = self.sjp_content_repo.get_by_toc_entry_ids(toc_ids) if toc_ids else []
        content_by_toc_id = {content.toc_entry_id: content for content in contents}

        completed_count = 0
        toc_statuses: list[SjpTocEntryStatusResponse] = []

        for entry in toc_entries:
            content = content_by_toc_id.get(entry.id)
            entry_status = content.status if content else SjpContentStatus.PENDING.value
            is_completed = entry_status == SjpContentStatus.COMPLETED.value

            if is_completed:
                completed_count += 1

            toc_statuses.append(
                SjpTocEntryStatusResponse(
                    toc_entry_id=entry.id,
                    title=entry.title,
                    status=entry_status,
                    is_completed=is_completed,
                    generated_at=content.generated_at if content else None,
                    error_message=content.error_message if content else None,
                )
            )

        total_sjps = len(toc_entries)
        progress_ratio = (completed_count / total_sjps) if total_sjps > 0 else 0.0

        return SjpGenerationStatusResponse(
            job_id=latest_job.id,
            order_id=latest_job.order_id,
            status=latest_job.status,
            created_at=latest_job.created_at,
            updated_at=latest_job.updated_at,
            toc_generated_at=latest_job.toc_generated_at,
            completed_at=latest_job.completed_at,
            failed_at=latest_job.failed_at,
            error_message=latest_job.error_message,
            progress=SjpProgressSummaryResponse(
                completed_sjps=completed_count,
                total_sjps=total_sjps,
                progress_ratio=progress_ratio,
            ),
            toc_entries=toc_statuses,
        )
