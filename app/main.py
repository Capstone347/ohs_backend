import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import RequestLoggingMiddleware, register_exception_handlers
from app.api.v1.router import api_router
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _resume_stuck_sjp_jobs() -> None:
    from app.api.dependencies import (
        get_jurisdiction_service,
        get_llm_provider,
    )
    from app.database.session import SessionLocal
    from app.models.sjp_generation_job import SjpGenerationStatus
    from app.repositories.llm_usage_log_repository import LlmUsageLogRepository
    from app.repositories.order_repository import OrderRepository
    from app.repositories.order_status_repository import OrderStatusRepository
    from app.repositories.sjp_content_repository import SjpContentRepository
    from app.repositories.sjp_generation_job_repository import SjpGenerationJobRepository
    from app.repositories.sjp_toc_entry_repository import SjpTocEntryRepository
    from app.services.sjp_content_generator import SjpContentGenerator
    from app.services.sjp_generation_service import SjpGenerationService
    from app.services.sjp_toc_generator import SjpTocGenerator

    db = SessionLocal()
    try:
        job_repo = SjpGenerationJobRepository(db)
        stuck_statuses = [
            SjpGenerationStatus.PENDING.value,
            SjpGenerationStatus.GENERATING_TOC.value,
            SjpGenerationStatus.GENERATING_SJPS.value,
        ]
        all_jobs = job_repo.get_all_by_statuses(stuck_statuses)
        if not all_jobs:
            return

        logger.info(f"Found {len(all_jobs)} stuck SJP generation jobs, resuming")

        llm_provider = get_llm_provider()
        jurisdiction_service = get_jurisdiction_service()

        service = SjpGenerationService(
            order_repo=OrderRepository(db),
            sjp_job_repo=SjpGenerationJobRepository(db),
            sjp_toc_entry_repo=SjpTocEntryRepository(db),
            sjp_content_repo=SjpContentRepository(db),
            llm_usage_log_repo=LlmUsageLogRepository(db),
            order_status_repo=OrderStatusRepository(db),
            toc_generator=SjpTocGenerator(llm_provider, jurisdiction_service),
            content_generator=SjpContentGenerator(llm_provider, jurisdiction_service),
        )

        for stuck_job in all_jobs:
            logger.info(f"Resuming SJP job {stuck_job.id} for order {stuck_job.order_id}")
            asyncio.create_task(service._run_generation(stuck_job.id, stuck_job.order_id))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup", environment=settings.environment.value)

    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.logos_dir.mkdir(parents=True, exist_ok=True)
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_documents_dir.mkdir(parents=True, exist_ok=True)
    settings.preview_documents_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Required directories created successfully")

    await _resume_stuck_sjp_jobs()

    yield

    logger.info("Application shutdown")


app = FastAPI(
    title="OHS Remote Backend API",
    description="Professional Health & Safety manual generation platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)

app.include_router(api_router, prefix="/api/v1")
