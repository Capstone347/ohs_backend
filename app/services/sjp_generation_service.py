import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.config import settings
from app.database.session import SessionLocal
from app.models.llm_usage_log import LlmUsageLog, LlmUsageStage
from app.models.order_status import OrderStatusEnum, PaymentStatus
from app.models.sjp_content import SjpContent, SjpContentStatus
from app.models.sjp_generation_job import SjpGenerationJob, SjpGenerationStatus
from app.models.sjp_toc_entry import SjpTocEntry
from app.repositories.llm_usage_log_repository import LlmUsageLogRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_repository import OrderStatusRepository
from app.repositories.sjp_content_repository import SjpContentRepository
from app.repositories.sjp_generation_job_repository import SjpGenerationJobRepository
from app.repositories.sjp_toc_entry_repository import SjpTocEntryRepository
from app.schemas.sjp import (
    SjpContentResponse,
    SjpContentSections,
    SjpFullContentResponse,
    SjpGenerationStatusResponse,
    SjpProgressSummaryResponse,
    SjpTocEntryStatusResponse,
)
from app.services.exceptions import ServiceException
from app.services.llm_provider import LlmResponse
from app.services.sjp_content_generator import SjpContentGenerator
from app.services.sjp_toc_generator import SjpTocGenerator

logger = logging.getLogger(__name__)

MAX_RETRY_ATTEMPTS = 2


class SjpGenerationServiceException(ServiceException):
    pass


class OrderNotFound(SjpGenerationServiceException):
    pass


class InvalidOrderState(SjpGenerationServiceException):
    pass


class MissingIndustryProfile(SjpGenerationServiceException):
    pass


class SjpGenerationJobNotFound(SjpGenerationServiceException):
    pass


class SjpGenerationService:
    def __init__(
        self,
        order_repo: OrderRepository,
        sjp_job_repo: SjpGenerationJobRepository,
        sjp_toc_entry_repo: SjpTocEntryRepository,
        sjp_content_repo: SjpContentRepository,
        llm_usage_log_repo: LlmUsageLogRepository,
        order_status_repo: OrderStatusRepository,
        toc_generator: SjpTocGenerator,
        content_generator: SjpContentGenerator,
    ):
        self.order_repo = order_repo
        self.sjp_job_repo = sjp_job_repo
        self.sjp_toc_entry_repo = sjp_toc_entry_repo
        self.sjp_content_repo = sjp_content_repo
        self.llm_usage_log_repo = llm_usage_log_repo
        self.order_status_repo = order_status_repo
        self.toc_generator = toc_generator
        self.content_generator = content_generator

    def start_generation(
        self,
        order_id: int,
        user_id: int,
        idempotency_key: str | None = None,
    ) -> SjpGenerationJob:
        if not idempotency_key:
            idempotency_key = str(uuid4())

        existing_job = self._get_existing_job(order_id, idempotency_key)
        if existing_job:
            return existing_job

        try:
            order = self.order_repo.get_by_id(order_id)
        except Exception as e:
            raise OrderNotFound(f"Order {order_id} not found") from e

        if not order:
            raise OrderNotFound(f"Order {order_id} not found")

        if order.user_id != user_id:
            raise OrderNotFound(f"Order {order_id} does not belong to user {user_id}")

        if not order.order_status or order.order_status.payment_status != PaymentStatus.PAID.value:
            raise InvalidOrderState(
                f"Order {order_id} is not paid. Current payment status: "
                f"{order.order_status.payment_status if order.order_status else 'unknown'}"
            )

        if not order.is_industry_specific:
            raise InvalidOrderState(f"Order {order_id} is not industry-specific")

        if not order.company or not order.company.industry_profile:
            raise MissingIndustryProfile(f"Order {order_id} is missing industry profile")

        industry_profile = order.company.industry_profile
        if not industry_profile.province:
            raise MissingIndustryProfile(f"Order {order_id} industry profile is missing province")

        if not industry_profile.naics_codes or len(industry_profile.naics_codes) == 0:
            raise MissingIndustryProfile(f"Order {order_id} industry profile is missing NAICS codes")

        naics_codes = [code.code for code in industry_profile.naics_codes]

        job = SjpGenerationJob(
            order_id=order_id,
            province=industry_profile.province,
            naics_codes=naics_codes,
            business_description=industry_profile.business_description,
            status=SjpGenerationStatus.PENDING.value,
            idempotency_key=idempotency_key,
        )

        job = self.sjp_job_repo.create(job)

        asyncio.create_task(self._run_generation(job.id, order_id))

        return job

    def start_generation_for_webhook(self, order_id: int) -> SjpGenerationJob:
        order = self.order_repo.get_by_id_with_relations(order_id)
        if not order:
            raise OrderNotFound(f"Order {order_id} not found")

        restartable_statuses = {
            SjpGenerationStatus.FAILED.value,
            SjpGenerationStatus.GENERATING_TOC.value,
            SjpGenerationStatus.GENERATING_SJPS.value,
            SjpGenerationStatus.PENDING.value,
        }

        existing_jobs = self.sjp_job_repo.get_by_order_id(order_id)
        if existing_jobs:
            latest = existing_jobs[0]
            if latest.status == SjpGenerationStatus.COMPLETED.value:
                return latest
            if latest.status in restartable_statuses:
                asyncio.create_task(self._run_generation(latest.id, order_id))
                return latest
            return latest

        if not order.company or not order.company.industry_profile:
            raise MissingIndustryProfile(f"Order {order_id} is missing industry profile")

        industry_profile = order.company.industry_profile
        naics_codes = [code.code for code in industry_profile.naics_codes]

        job = SjpGenerationJob(
            order_id=order_id,
            province=industry_profile.province,
            naics_codes=naics_codes,
            business_description=industry_profile.business_description,
            status=SjpGenerationStatus.PENDING.value,
            idempotency_key=str(uuid4()),
        )

        job = self.sjp_job_repo.create(job)

        asyncio.create_task(self._run_generation(job.id, order_id))

        return job

    async def _run_generation(self, job_id: int, order_id: int) -> None:
        db = SessionLocal()
        try:
            job_repo = SjpGenerationJobRepository(db)
            toc_entry_repo = SjpTocEntryRepository(db)
            content_repo = SjpContentRepository(db)
            usage_log_repo = LlmUsageLogRepository(db)
            order_status_repo = OrderStatusRepository(db)

            job = job_repo.get_by_id(job_id)
            if not job:
                logger.error("SJP generation job %d not found", job_id)
                return

            existing_toc_entries = toc_entry_repo.get_by_job_id(job_id)

            if not existing_toc_entries:
                try:
                    await self._stage_a_generate_toc(job, job_repo, toc_entry_repo, usage_log_repo)
                except Exception as e:
                    logger.error("TOC generation failed for job %d: %s", job_id, str(e), exc_info=True)
                    self._mark_job_failed(job, job_repo, str(e))
                    return
                existing_toc_entries = toc_entry_repo.get_by_job_id(job_id)
            else:
                logger.info("Resuming job %d — TOC already exists with %d entries", job_id, len(existing_toc_entries))

            toc_ids = [e.id for e in existing_toc_entries]
            existing_contents = content_repo.get_by_toc_entry_ids(toc_ids) if toc_ids else []
            completed_toc_ids = {
                c.toc_entry_id for c in existing_contents
                if c.status == SjpContentStatus.COMPLETED.value
            }
            failed_toc_ids = {
                c.toc_entry_id for c in existing_contents
                if c.status == SjpContentStatus.FAILED.value
            }
            for fid in failed_toc_ids:
                failed_content = next(c for c in existing_contents if c.toc_entry_id == fid)
                content_repo.delete(failed_content.id)

            pending_entries = [e for e in existing_toc_entries if e.id not in completed_toc_ids]

            if pending_entries:
                logger.info(
                    "Job %d: %d/%d entries pending, resuming content generation",
                    job_id, len(pending_entries), len(existing_toc_entries),
                )
                try:
                    await self._stage_b_generate_content(
                        job, pending_entries, job_repo, content_repo, usage_log_repo
                    )
                except Exception as e:
                    logger.error("Content generation failed for job %d: %s", job_id, str(e), exc_info=True)
                    self._mark_job_failed(job, job_repo, str(e))
                    return

            job.status = SjpGenerationStatus.COMPLETED.value
            job.completed_at = datetime.now(UTC)
            job.updated_at = datetime.now(UTC)
            job_repo.update(job)

            order_status_repo.update_order_status(order_id, OrderStatusEnum.REVIEW_PENDING)
            logger.info("SJP generation completed for job %d, order %d moved to review_pending", job_id, order_id)

        except Exception as e:
            logger.error("Unexpected error in SJP generation for job %d: %s", job_id, str(e), exc_info=True)
        finally:
            db.close()

    async def _stage_a_generate_toc(
        self,
        job: SjpGenerationJob,
        job_repo: SjpGenerationJobRepository,
        toc_entry_repo: SjpTocEntryRepository,
        usage_log_repo: LlmUsageLogRepository,
    ) -> None:
        job.status = SjpGenerationStatus.GENERATING_TOC.value
        job.updated_at = datetime.now(UTC)
        job_repo.update(job)

        result = await self.toc_generator.generate_toc(
            province=job.province,
            naics_codes=job.naics_codes,
            business_description=job.business_description,
        )

        for position, title in enumerate(result.titles, start=1):
            entry = SjpTocEntry(
                job_id=job.id,
                position=position,
                title=title,
            )
            toc_entry_repo.create(entry)

        self._log_llm_usage(
            usage_log_repo=usage_log_repo,
            job_id=job.id,
            toc_entry_id=None,
            stage=LlmUsageStage.TOC,
            llm_response=result.llm_response,
        )

        job.toc_generated_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        job_repo.update(job)

    async def _stage_b_generate_content(
        self,
        job: SjpGenerationJob,
        toc_entries: list[SjpTocEntry],
        job_repo: SjpGenerationJobRepository,
        content_repo: SjpContentRepository,
        usage_log_repo: LlmUsageLogRepository,
    ) -> None:
        job.status = SjpGenerationStatus.GENERATING_SJPS.value
        job.updated_at = datetime.now(UTC)
        job_repo.update(job)

        semaphore = asyncio.Semaphore(settings.llm_max_concurrent_requests)

        async def generate_single_sjp(entry: SjpTocEntry) -> None:
            async with semaphore:
                await self._generate_single_sjp_content(
                    entry, job, content_repo, usage_log_repo
                )

        tasks = [generate_single_sjp(entry) for entry in toc_entries]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _generate_single_sjp_content(
        self,
        entry: SjpTocEntry,
        job: SjpGenerationJob,
        content_repo: SjpContentRepository,
        usage_log_repo: LlmUsageLogRepository,
    ) -> None:
        for attempt in range(MAX_RETRY_ATTEMPTS + 1):
            try:
                result = await self.content_generator.generate_content(
                    title=entry.title,
                    province=job.province,
                    naics_codes=job.naics_codes,
                    business_description=job.business_description,
                )

                content = SjpContent(
                    toc_entry_id=entry.id,
                    task_description=result.sections.task_description,
                    required_ppe=result.sections.required_ppe,
                    step_by_step_instructions=result.sections.step_by_step_instructions,
                    identified_hazards=result.sections.identified_hazards,
                    control_measures=result.sections.control_measures,
                    training_requirements=result.sections.training_requirements,
                    emergency_procedures=result.sections.emergency_procedures,
                    legislative_references=result.sections.legislative_references,
                    raw_ai_response=result.llm_response.content,
                    status=SjpContentStatus.COMPLETED.value,
                    generated_at=datetime.now(UTC),
                )
                content_repo.create(content)

                self._log_llm_usage(
                    usage_log_repo=usage_log_repo,
                    job_id=job.id,
                    toc_entry_id=entry.id,
                    stage=LlmUsageStage.SJP_CONTENT,
                    llm_response=result.llm_response,
                )

                logger.info("SJP content generated for entry '%s' (job %d)", entry.title, job.id)
                return

            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS:
                    logger.warning(
                        "SJP generation attempt %d failed for '%s' (job %d): %s. Retrying.",
                        attempt + 1, entry.title, job.id, str(e),
                    )
                    continue

                logger.error(
                    "SJP generation failed after %d attempts for '%s' (job %d): %s",
                    MAX_RETRY_ATTEMPTS + 1, entry.title, job.id, str(e),
                )
                content = SjpContent(
                    toc_entry_id=entry.id,
                    task_description="",
                    required_ppe=[],
                    step_by_step_instructions=[],
                    identified_hazards=[],
                    control_measures=[],
                    training_requirements=[],
                    emergency_procedures="",
                    raw_ai_response="",
                    status=SjpContentStatus.FAILED.value,
                    error_message=str(e),
                )
                content_repo.create(content)

    def _log_llm_usage(
        self,
        usage_log_repo: LlmUsageLogRepository,
        job_id: int,
        toc_entry_id: int | None,
        stage: LlmUsageStage,
        llm_response: LlmResponse,
    ) -> None:
        input_cost = (Decimal(llm_response.prompt_tokens) / 1000) * settings.llm_input_cost_per_1k_tokens
        output_cost = (Decimal(llm_response.completion_tokens) / 1000) * settings.llm_output_cost_per_1k_tokens
        estimated_cost = input_cost + output_cost

        log = LlmUsageLog(
            job_id=job_id,
            toc_entry_id=toc_entry_id,
            stage=stage.value,
            model=llm_response.model,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            estimated_cost_usd=estimated_cost,
        )
        usage_log_repo.create(log)

    def _mark_job_failed(
        self,
        job: SjpGenerationJob,
        job_repo: SjpGenerationJobRepository,
        error_message: str,
    ) -> None:
        job.status = SjpGenerationStatus.FAILED.value
        job.error_message = error_message
        job.failed_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        job_repo.update(job)

    def _get_existing_job(self, order_id: int, idempotency_key: str) -> SjpGenerationJob | None:
        restartable_statuses = {
            SjpGenerationStatus.FAILED.value,
            SjpGenerationStatus.GENERATING_TOC.value,
            SjpGenerationStatus.GENERATING_SJPS.value,
            SjpGenerationStatus.PENDING.value,
        }

        existing_jobs = self.sjp_job_repo.get_by_order_id(order_id)
        if existing_jobs:
            latest = existing_jobs[0]
            if latest.status in restartable_statuses:
                asyncio.create_task(self._run_generation(latest.id, order_id))
                return latest
            if latest.status == SjpGenerationStatus.COMPLETED.value:
                return latest
            return latest

        existing_job = self.sjp_job_repo.get_by_idempotency_key(idempotency_key)
        if existing_job and existing_job.order_id == order_id:
            if existing_job.status == SjpGenerationStatus.COMPLETED.value:
                return existing_job

        return None

    def get_generation_status(self, order_id: int, user_id: int | None = None) -> SjpGenerationStatusResponse:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFound(f"Order {order_id} not found")
        if user_id and order.user_id != user_id:
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

    def get_full_content(self, order_id: int, user_id: int | None = None) -> SjpFullContentResponse:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFound(f"Order {order_id} not found")
        if user_id and order.user_id != user_id:
            raise OrderNotFound(f"Order {order_id} not found")

        is_customer_request = user_id is not None
        order_approved = (
            order.order_status
            and order.order_status.order_status == OrderStatusEnum.AVAILABLE.value
        )
        hide_sections = is_customer_request and not order_approved

        jobs = self.sjp_job_repo.get_by_order_id(order_id)
        if not jobs:
            raise SjpGenerationJobNotFound(f"No SJP generation job found for order {order_id}")

        job = jobs[0]
        toc_entries = self.sjp_toc_entry_repo.get_by_job_id(job.id)
        toc_ids = [entry.id for entry in toc_entries]
        contents = self.sjp_content_repo.get_by_toc_entry_ids(toc_ids) if toc_ids else []
        content_by_toc_id = {c.toc_entry_id: c for c in contents}

        entries: list[SjpContentResponse] = []
        for entry in toc_entries:
            content = content_by_toc_id.get(entry.id)
            sections = None
            if not hide_sections and content and content.status == SjpContentStatus.COMPLETED.value:
                sections = SjpContentSections(
                    task_description=content.task_description,
                    required_ppe=content.required_ppe,
                    step_by_step_instructions=content.step_by_step_instructions,
                    identified_hazards=content.identified_hazards,
                    control_measures=content.control_measures,
                    training_requirements=content.training_requirements,
                    emergency_procedures=content.emergency_procedures,
                    legislative_references=content.legislative_references,
                )

            entries.append(SjpContentResponse(
                toc_entry_id=entry.id,
                title=entry.title,
                position=entry.position,
                status=content.status if content else SjpContentStatus.PENDING.value,
                sections=sections,
                generated_at=content.generated_at if content else None,
                error_message=content.error_message if content and not hide_sections else None,
            ))

        disclaimer = (
            f"Content is intended to reflect requirements under {job.province} "
            f"occupational health and safety legislation as of the generation date. "
            f"This does not constitute legal advice."
        )

        return SjpFullContentResponse(
            job_id=job.id,
            order_id=job.order_id,
            province=job.province,
            naics_codes=job.naics_codes,
            status=job.status,
            disclaimer=disclaimer,
            entries=entries,
        )

    def get_single_sjp_content(
        self, order_id: int, toc_entry_id: int, user_id: int | None = None
    ) -> SjpContentResponse:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFound(f"Order {order_id} not found")
        if user_id and order.user_id != user_id:
            raise OrderNotFound(f"Order {order_id} not found")

        is_customer_request = user_id is not None
        order_approved = (
            order.order_status
            and order.order_status.order_status == OrderStatusEnum.AVAILABLE.value
        )
        hide_sections = is_customer_request and not order_approved

        jobs = self.sjp_job_repo.get_by_order_id(order_id)
        if not jobs:
            raise SjpGenerationJobNotFound(f"No SJP generation job found for order {order_id}")

        job = jobs[0]
        toc_entries = self.sjp_toc_entry_repo.get_by_job_id(job.id)
        entry = next((e for e in toc_entries if e.id == toc_entry_id), None)
        if not entry:
            raise SjpGenerationJobNotFound(f"TOC entry {toc_entry_id} not found for order {order_id}")

        content = self.sjp_content_repo.get_by_toc_entry_id(entry.id)
        sections = None
        if not hide_sections and content and content.status == SjpContentStatus.COMPLETED.value:
            sections = SjpContentSections(
                task_description=content.task_description,
                required_ppe=content.required_ppe,
                step_by_step_instructions=content.step_by_step_instructions,
                identified_hazards=content.identified_hazards,
                control_measures=content.control_measures,
                training_requirements=content.training_requirements,
                emergency_procedures=content.emergency_procedures,
                legislative_references=content.legislative_references,
            )

        return SjpContentResponse(
            toc_entry_id=entry.id,
            title=entry.title,
            position=entry.position,
            status=content.status if content else SjpContentStatus.PENDING.value,
            sections=sections,
            generated_at=content.generated_at if content else None,
            error_message=content.error_message if content and not hide_sections else None,
        )

    def update_sjp_content(self, toc_entry_id: int, updates: dict) -> SjpContent:
        content = self.sjp_content_repo.get_by_toc_entry_id(toc_entry_id)
        if not content:
            raise SjpGenerationJobNotFound(f"Content not found for TOC entry {toc_entry_id}")

        for field, value in updates.items():
            if value is not None and hasattr(content, field):
                setattr(content, field, value)

        return self.sjp_content_repo.update(content)

    async def regenerate_single_sjp(self, toc_entry_id: int) -> None:
        entry = self.sjp_toc_entry_repo.get_by_id(toc_entry_id)
        if not entry:
            raise SjpGenerationJobNotFound(f"TOC entry {toc_entry_id} not found")

        job = self.sjp_job_repo.get_by_id(entry.job_id)
        if not job:
            raise SjpGenerationJobNotFound(f"Job not found for TOC entry {toc_entry_id}")

        existing_content = self.sjp_content_repo.get_by_toc_entry_id(toc_entry_id)
        if existing_content:
            self.sjp_content_repo.delete(existing_content.id)

        await self._generate_single_sjp_content(
            entry, job, self.sjp_content_repo, self.llm_usage_log_repo
        )
