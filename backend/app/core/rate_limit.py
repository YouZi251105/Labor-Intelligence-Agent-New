import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp


@dataclass
class WindowEntry:
    count: int
    reset_at: float


class FixedWindowRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: int = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self._entries: dict[str, WindowEntry] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or now >= entry.reset_at:
                self._entries[key] = WindowEntry(
                    count=1,
                    reset_at=now + self.window_seconds,
                )
                return True
            if entry.count >= self.limit:
                return False
            entry.count += 1
            return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    protected_paths = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
    }

    def __init__(self, app: ASGIApp, limiter: FixedWindowRateLimiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method == "POST" and request.url.path in self.protected_paths:
            client = request.client.host if request.client else "unknown"
            key = f"{client}:{request.url.path}"
            if not self.limiter.allow(key):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "请求过于频繁，请稍后重试"},
                    headers={"Retry-After": "60"},
                )
        return await call_next(request)
