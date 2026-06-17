# c:\Mood_Market\middleware.py
import time
import logging
import uuid
from datetime import datetime, timezone
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as aioredis

from config import api_settings
from authenticator import JWTAuthenticator
from utils.request_context import set_request_id, set_user_id, clear_context

logger = logging.getLogger("api.logger")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware generating tracing IDs, extracting bearer tokens,
    and structured JSON logging for response latencies.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        # 1. Tracing ID Setup
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        
        # 2. Extract and Verify JWT Bearer User Token
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                user_id = JWTAuthenticator.verify_token(token)
                if user_id:
                    set_user_id(user_id)
            except Exception:
                pass
                
        # Query parameter fallback (for WebSocket authentications)
        if not user_id:
            token_param = request.query_params.get("token")
            if token_param:
                user_id = JWTAuthenticator.verify_token(token_param)
                if user_id:
                    set_user_id(user_id)

        try:
            response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000
            
            # Record structural API latency
            logger.info(
                "HTTP request completed",
                extra={
                    "endpoint": request.url.path,
                    "context": {
                        "method": request.method,
                        "status_code": response.status_code,
                        "latency_ms": round(process_time, 2)
                    }
                }
            )
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
            return response
            
        except Exception as e:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"HTTP request failed: {str(e)}",
                exc_info=True,
                extra={
                    "endpoint": request.url.path,
                    "context": {
                        "method": request.method,
                        "status_code": 500,
                        "latency_ms": round(process_time, 2)
                    }
                }
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "Internal server error during request execution.",
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        "request_id": request_id
                    }
                }
            )
        finally:
            clear_context()


class RedisRateLimiterMiddleware(BaseHTTPMiddleware):
    """Enforces API rate limits (100 req/min per IP/API Key) in Redis."""
    def __init__(self, app, redis_uri: str, limit: int = 100):
        super().__init__(app)
        self.redis_pool = aioredis.ConnectionPool.from_url(
            redis_uri, encoding="utf-8", decode_responses=True
        )
        self.limit = limit

    async def get_redis_client(self) -> aioredis.Redis:
        return aioredis.Redis(connection_pool=self.redis_pool)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in ["/docs", "/redoc", "/openapi.json", "/api/v1/health"] or api_settings.env == "test":
            return await call_next(request)

        # Identify client (API key bearer or IP address)
        client_id = request.client.host if request.client else "unknown_ip"
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            client_id = auth_header.split(" ")[1]

        redis = await self.get_redis_client()
        current_minute = int(time.time() // 60)
        rate_key = f"ratelimit:{client_id}:{current_minute}"

        try:
            count = await redis.incr(rate_key)
            if count == 1:
                await redis.expire(rate_key, 60)
                
            if count > self.limit:
                logger.warning(
                    f"Rate limit breached for identifier: {client_id[-8:] if len(client_id) > 16 else client_id}",
                    extra={"endpoint": path}
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "TOO_MANY_REQUESTS",
                            "message": "Rate limit exceeded. Maximum 100 requests per minute.",
                            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                            "request_id": request.headers.get("X-Request-ID", "unknown")
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Rate limiter Redis failure: {e}. Bypassing limit checks.", extra={"endpoint": path})
        finally:
            await redis.close()

        return await call_next(request)
