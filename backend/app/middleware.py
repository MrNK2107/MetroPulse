"""HTTP middleware: correlation IDs, structured request logs, a per-IP rate limit.

Ported from the June 2026 simulator-era API hardening and adapted to the desk's
`/api` routes (the desk never adopted `/api/v1`). Request bodies are not logged:
they can carry free text from the agent and twin search.
"""
from __future__ import annotations

import collections
import json
import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("app.main")

# The health routes in app/routes/health.py (Fly's check polls /api/health).
HEALTH_PATHS = frozenset({"/api/health", "/api/health/data", "/api/health/llm"})
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def client_ip(request: Request) -> str:
    """The caller's IP for rate limiting.

    Behind Fly every request arrives from Fly's proxy, so the socket peer is the
    same for all clients; Fly sets ``Fly-Client-IP`` to the real client address
    (and overwrites any value the client sent). Off Fly, use the socket peer.
    """
    fly_ip = request.headers.get("fly-client-ip", "").strip()
    if fly_ip:
        return fly_ip
    return request.client.host if request.client else "unknown"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Give every request an X-Request-ID (echo a well-formed client one, else a UUID)."""

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _REQUEST_ID_RE.match(incoming) else str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """One JSON log line per request (method, path, status, latency, request id). Skips health checks."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in HEALTH_PATHS:
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        entry = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "response_time_ms": round((time.perf_counter() - start) * 1000, 2),
        }
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            entry["request_id"] = request_id
        logger.info(json.dumps(entry))
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window limit of `limit` requests per minute per client IP
    (``Fly-Client-IP`` when present). Health checks are exempt."""

    WINDOW_SECONDS = 60.0

    def __init__(self, app, limit: int = 240):
        super().__init__(app)
        self.limit = limit
        self._requests: dict[str, collections.deque[float]] = {}
        self._last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next):
        if self.limit <= 0 or request.url.path in HEALTH_PATHS:
            return await call_next(request)

        key = client_ip(request)
        now = time.time()
        if now - self._last_cleanup > self.WINDOW_SECONDS:
            stale = [ip for ip, q in self._requests.items() if not q or now - q[-1] > self.WINDOW_SECONDS]
            for ip in stale:
                del self._requests[ip]
            self._last_cleanup = now

        timestamps = self._requests.setdefault(key, collections.deque())
        while timestamps and now - timestamps[0] > self.WINDOW_SECONDS:
            timestamps.popleft()

        if len(timestamps) >= self.limit:
            retry_after = self.WINDOW_SECONDS - (now - timestamps[0])
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "data": None,
                    "error": f"Rate limit exceeded. Max {self.limit} requests per minute.",
                    "meta": {"retry_after_seconds": round(retry_after, 1)},
                },
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
        timestamps.append(now)
        return await call_next(request)
