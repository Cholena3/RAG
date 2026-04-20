import uuid
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        start = time.perf_counter()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        logger.info("request_started", method=request.method, path=request.url.path)

        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info("request_completed", method=request.method, path=request.url.path,
                     status=response.status_code, latency_ms=round(elapsed_ms, 2))
        response.headers["X-Correlation-ID"] = correlation_id
        return response
