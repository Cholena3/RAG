import time
import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiter backed by Redis."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and docs
        if request.url.path in ("/api/v1/health", "/docs", "/openapi.json"):
            return await call_next(request)

        # Identify client by auth token or IP
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            key = f"rl:{auth[7:20]}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            key = f"rl:{client_ip}"

        now = int(time.time())
        window_key = f"{key}:{now // 60}"

        pipe = self.redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, 120)
        results = await pipe.execute()
        count = results[0]

        if count > self.rpm:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again shortly.",
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.rpm - count))
        return response
