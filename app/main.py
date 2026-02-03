from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import RequestLoggingMiddleware, register_exception_handlers
from app.api.v1.router import api_router
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup", environment=settings.environment.value)
    
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.logos_dir.mkdir(parents=True, exist_ok=True)
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_documents_dir.mkdir(parents=True, exist_ok=True)
    settings.preview_documents_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Required directories created successfully")
    
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
