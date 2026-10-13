import time, logging
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from collections import defaultdict

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        request_id = f"req-{int(start * 1000)}"
        try:
            response = await call_next(request)
        except Exception as e:
            duration = time.time() - start
            logger.error("Request %s %s failed: %s (%.3fs)", request.method, request.url.path, e, duration)
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
        duration = time.time() - start
        logger.info("%s %s → %s (%.3fs)", request.method, request.url.path, response.status_code, duration)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.limit = requests_per_minute
        self._store = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        client = request.client.host if request.client else "unknown"
        now = time.time()
        window = [t for t in self._store[client] if now - t < 60]
        if len(window) >= self.limit:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        window.append(now)
        self._store[client] = window
        return await call_next(request)
