from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    OHSRemoteException,
    ValidationError,
    OrderNotFoundError,
    DocumentGenerationError,
    PaymentProcessingError,
    EmailDeliveryError,
    FileStorageError,
    ConfigurationError,
)
from app.core.logging import get_logger
from app.schemas.responses import ErrorResponse

logger = get_logger(__name__)


def get_request_id(request: Request) -> str:
    if hasattr(request.state, "request_id"):
        return request.state.request_id
    return "unknown"


def build_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, str] | None = None,
    request_id: str | None = None
) -> JSONResponse:
    error_data = ErrorResponse(
        code=error_code,
        message=message,
        details=details
    )
    
    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id
    
    return JSONResponse(
        status_code=status_code,
        content={"error": error_data.model_dump(exclude_none=True)},
        headers=headers
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    request_id = get_request_id(request)
    
    logger.warning(
        "Validation error",
        request_id=request_id,
        error=str(exc),
        path=request.url.path
    )
    
    return build_error_response(
        status_code=400,
        error_code="VALIDATION_ERROR",
        message=str(exc),
        request_id=request_id
    )


async def order_not_found_handler(request: Request, exc: OrderNotFoundError) -> JSONResponse:
    request_id = get_request_id(request)
    
    logger.warning(
        "Order not found",
        request_id=request_id,
        error=str(exc),
        path=request.url.path
    )
    
    return build_error_response(
        status_code=404,
        error_code="ORDER_NOT_FOUND",
        message=str(exc),
        request_id=request_id
    )


async def document_generation_error_handler(request: Request, exc: DocumentGenerationError) -> JSONResponse:
    request_id = get_request_id(request)
    
    logger.error(
        "Document generation error",
        request_id=request_id,
        error=str(exc),
        path=request.url.path
    )
    
    return build_error_response(
        status_code=500,
        error_code="DOCUMENT_GENERATION_ERROR",
        message=str(exc),
        request_id=request_id
    )


async def payment_processing_error_handler(request: Request, exc: PaymentProcessingError) -> JSONResponse:
    request_id = get_request_id(request)
    
    logger.error(
        "Payment processing error",
        request_id=request_id,
        error=str(exc),
        path=request.url.path
    )
    
    return build_error_response(
        status_code=500,
        error_code="PAYMENT_PROCESSING_ERROR",
        message=str(exc),
        request_id=request_id
    )


async def email_delivery_error_handler(request: Request, exc: EmailDeliveryError) -> JSONResponse:
    request_id = get_request_id(request)
    
    logger.error(
        "Email delivery error",
        request_id=request_id,
        error=str(exc),
        path=request.url.path
    )
    
    return build_error_response(
        status_code=500,
        error_code="EMAIL_DELIVERY_ERROR",
        message=str(exc),
        request_id=request_id
    )


async def file_storage_error_handler(request: Request, exc: FileStorageError) -> JSONResponse:
    request_id = get_request_id(request)
    
    logger.error(
        "File storage error",
        request_id=request_id,
        error=str(exc),
        path=request.url.path
    )
    
    return build_error_response(
        status_code=500,
        error_code="FILE_STORAGE_ERROR",
        message=str(exc),
        request_id=request_id
    )


async def configuration_error_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    request_id = get_request_id(request)
    
    logger.error(
        "Configuration error",
        request_id=request_id,
        error=str(exc),
        path=request.url.path
    )
    
    return build_error_response(
        status_code=500,
        error_code="CONFIGURATION_ERROR",
        message=str(exc),
        request_id=request_id
    )


async def ohs_remote_exception_handler(request: Request, exc: OHSRemoteException) -> JSONResponse:
    request_id = get_request_id(request)
    
    logger.error(
        "OHS Remote exception",
        request_id=request_id,
        error=str(exc),
        error_type=exc.__class__.__name__,
        path=request.url.path
    )
    
    return build_error_response(
        status_code=400,
        error_code=exc.__class__.__name__.upper(),
        message=str(exc),
        request_id=request_id
    )


async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = get_request_id(request)
    
    errors = {}
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"][1:])
        if not field_path:
            field_path = "body"
        errors[field_path] = error["msg"]
    
    logger.warning(
        "Request validation error",
        request_id=request_id,
        validation_errors=errors,
        path=request.url.path
    )
    
    return build_error_response(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message="One or more fields failed validation",
        details=errors,
        request_id=request_id
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = get_request_id(request)
    
    logger.warning(
        "HTTP exception",
        request_id=request_id,
        status_code=exc.status_code,
        error=str(exc.detail),
        path=request.url.path
    )
    
    return build_error_response(
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        request_id=request_id
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id(request)
    
    logger.error(
        "Unexpected error",
        request_id=request_id,
        error=str(exc),
        error_type=exc.__class__.__name__,
        path=request.url.path
    )
    
    return build_error_response(
        status_code=500,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        request_id=request_id
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(OrderNotFoundError, order_not_found_handler)
    app.add_exception_handler(DocumentGenerationError, document_generation_error_handler)
    app.add_exception_handler(PaymentProcessingError, payment_processing_error_handler)
    app.add_exception_handler(EmailDeliveryError, email_delivery_error_handler)
    app.add_exception_handler(FileStorageError, file_storage_error_handler)
    app.add_exception_handler(ConfigurationError, configuration_error_handler)
    app.add_exception_handler(OHSRemoteException, ohs_remote_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
