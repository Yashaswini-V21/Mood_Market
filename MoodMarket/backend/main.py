import logging
import time
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from config import api_settings
from exceptions import register_exception_handlers
from middleware import RequestLoggerMiddleware, RedisRateLimiterMiddleware
from dependencies import get_inference_engine, redis_pool, engine as db_engine

from logging_config import setup_logging
setup_logging()
logger = logging.getLogger("main")

_startup_time: float = 0.0

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events managing connections on application startup and shutdown."""
    global _startup_time
    _startup_time = time.time()
    logger.info("Initializing MoodMarket API server...")
    
    # 1. Warm-up: preload ML Informer model
    try:
        get_inference_engine()
        logger.info("✓ Informer prediction engine initialized and model loaded.")
    except Exception as e:
        logger.error(f"Failed to preload model: {e}")
        
    # 2. Warm-up: preload Redis cache with top 50 tickers
    try:
        from cache_warmer import warm_cache_on_startup
        warm_cache_on_startup()
    except Exception as e:
        logger.error(f"Failed to warm cache: {e}")
        
    # 3. Database table creation
    try:
        from sqlalchemy import text
        async with db_engine.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS sentiment_records ("
                "id VARCHAR(64) PRIMARY KEY, "
                "ticker VARCHAR(16), "
                "sentiment FLOAT, "
                "confidence FLOAT, "
                "timestamp TIMESTAMP"
                ")"
            ))
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS forecast_records ("
                "id VARCHAR(64) PRIMARY KEY, "
                "ticker VARCHAR(16), "
                "prediction FLOAT, "
                "confidence FLOAT, "
                "direction VARCHAR(8), "
                "timestamp TIMESTAMP"
                ")"
            ))
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS price_records ("
                "id VARCHAR(64) PRIMARY KEY, "
                "ticker VARCHAR(16), "
                "timestamp TIMESTAMP, "
                "open FLOAT, "
                "high FLOAT, "
                "low FLOAT, "
                "close FLOAT, "
                "volume FLOAT, "
                "RSI FLOAT, "
                "MACD FLOAT, "
                "Bollinger_Band FLOAT, "
                "google_trends FLOAT, "
                "reddit_hype FLOAT, "
                "sentiment_score FLOAT"
                ")"
            ))
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS anomaly_records ("
                "id VARCHAR(64) PRIMARY KEY, "
                "ticker VARCHAR(16), "
                "anomaly_detected BOOLEAN, "
                "confidence FLOAT, "
                "alert_level VARCHAR(16), "
                "timestamp TIMESTAMP"
                ")"
            ))
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS watchlist_records ("
                "id VARCHAR(64) PRIMARY KEY, "
                "user_id VARCHAR(64) UNIQUE, "
                "tickers TEXT"
                ")"
            ))
        logger.info("✓ Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")

    yield
    
    # 2. Cleanup: close database and Redis pools on shutdown
    logger.info("Shutting down MoodMarket API server...")
    try:
        await redis_pool.disconnect()
        logger.info("✓ Redis cache connection pools closed successfully.")
    except Exception as e:
        logger.error(f"Redis cache cleanup failure: {e}")
        
    try:
        await db_engine.dispose()
        logger.info("✓ Database connection pools disposed successfully.")
    except Exception as e:
        logger.error(f"Database cleanup failure: {e}")


# ── App version / build metadata ────────────────────────────────────────────
APP_VERSION = "1.0.0"
APP_DESCRIPTION = """
## MoodMarket Forecasting API

High-frequency, multi-agent AI platform that fuses real-time social sentiment
with an **Informer Transformer** (ProbSparse O(L log L) attention) to forecast
stock price direction and detect coordinated hype events.

### Key capabilities
- `/api/v1/sentiment/{ticker}` — FinBERT + DistilBERT ensemble score
- `/api/v1/price/forecast/{ticker}` — 4-hour direction + uncertainty
- `/api/v1/anomaly/{ticker}` — 7-method HypeStorm Radar™
- `/api/v1/pipeline/{ticker}` — Full 5-agent trading desk bundle
- `/api/v1/explain/{id}` — SHAP + Attention Rollout attribution
- `WS /ws/*` — JWT-authenticated live streams

> **Note:** All endpoints require a valid JWT. Obtain one via `POST /auth/token`.
"""

# Initialize FastAPI with rich Swagger UI metadata
app = FastAPI(
    title="MoodMarket API",
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Health", "description": "System health and status checks"},
        {"name": "Sentiment", "description": "FinBERT + DistilBERT sentiment analysis"},
        {"name": "Forecasting", "description": "Informer Transformer 4-hour price direction"},
        {"name": "Anomaly", "description": "7-method HypeStorm Radar anomaly detection"},
        {"name": "Pipeline", "description": "Full 5-agent trading desk end-to-end"},
        {"name": "Explainability", "description": "SHAP values and attention rollout weights"},
        {"name": "Watchlist", "description": "User ticker watchlist management"},
        {"name": "WebSockets", "description": "JWT-authenticated real-time data streams"},
    ],
)

# 1. Setup CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=api_settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Setup Logging and Rate Limiting Middlewares
app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(
    RedisRateLimiterMiddleware,
    redis_uri=api_settings.redis_uri,
    limit=api_settings.rate_limit_per_min
)

# 3. Setup Custom Exception Handlers
register_exception_handlers(app)


# 4. Import and Register Route Sub-Routers
from routes import (
    health,
    sentiment,
    forecast,
    anomaly,
    pipeline,
    explain,
    watchlist
)

# Bind endpoints under api/v1 prefix
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(sentiment.router, prefix="/api/v1", tags=["Sentiment"])
app.include_router(forecast.router, prefix="/api/v1", tags=["Forecasting"])
app.include_router(anomaly.router, prefix="/api/v1", tags=["Anomaly"])
app.include_router(pipeline.router, prefix="/api/v1", tags=["Pipeline"])
app.include_router(explain.router, prefix="/api/v1", tags=["Explainability"])
app.include_router(watchlist.router, prefix="/api/v1", tags=["Watchlist"])

# Bind WebSocket and HTTP Fallback endpoints
import websocket_server
app.include_router(websocket_server.router, tags=["WebSockets"])


# 5. Setup Prometheus Metrics Instrumentator
# Must be set up AFTER all routers are registered to avoid
# '_IncludedRouter' attribute errors in newer Starlette versions.
import os as _os
if _os.environ.get("ENVIRONMENT") != "test" and _os.environ.get("ENV") != "test":
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
        logger.info("✓ Prometheus metrics instrumentator initialized at /metrics")
    except Exception as e:
        logger.warning(f"Failed to initialize Prometheus metrics instrumentator: {e}")


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint — returns API version, uptime, and navigation links."""
    import sys
    uptime_s = round(time.time() - _startup_time, 1) if _startup_time else 0
    return {
        "name": "MoodMarket API",
        "version": APP_VERSION,
        "status": "running",
        "environment": api_settings.env,
        "python": sys.version.split()[0],
        "uptime_seconds": uptime_s,
        "links": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/api/v1/health",
            "metrics": "/metrics",
            "auth": "/auth/token",
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=(api_settings.env == "development")
    )
