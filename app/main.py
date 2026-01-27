from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import OHSRemoteException


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create directories
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.logos_dir.mkdir(parents=True, exist_ok=True)
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_documents_dir.mkdir(parents=True, exist_ok=True)
    settings.preview_documents_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown: Clean up resources (if needed)


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
    allow_headers=["*"]
)


@app.exception_handler(OHSRemoteException)
async def ohs_remote_exception_handler(request: Request, exc: OHSRemoteException) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.__class__.__name__,
                "message": str(exc)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )


app.include_router(api_router, prefix="/api/v1")
