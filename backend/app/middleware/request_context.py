import time
from uuid import uuid4

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.metrics import METRICS

logger = structlog.get_logger()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        with structlog.contextvars.bound_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        ):
            try:
                response = await call_next(request)
            except Exception:
                duration = time.perf_counter() - started
                METRICS.observe(500, duration)
                logger.exception("request_failed", duration=round(duration, 4))
                raise
            duration = time.perf_counter() - started
            response.headers["X-Request-ID"] = request_id
            METRICS.observe(response.status_code, duration)
            logger.info(
                "request_completed",
                status=response.status_code,
                duration=round(duration, 4),
            )
            return response
