import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        logger.info(
            "Request received",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
            query_params=str(request.query_params) if request.query_params else None
        )
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                duration_seconds=round(duration, 3),
                method=request.method,
                path=request.url.path
            )
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                error_type=e.__class__.__name__,
                duration_seconds=round(duration, 3),
                method=request.method,
                path=request.url.path
            )
            raise
