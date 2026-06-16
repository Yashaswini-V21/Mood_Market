"""
Anomaly Detection Route.

Retrieves the current social volume anomaly and hype storm monitoring
alert status for a given stock ticker.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
import json
import logging
from typing import Dict, Any

from models import AnomalyResponse
from dependencies import get_db, get_redis, verify_api_key
from exceptions import DatabaseException
from cache import cache_manager
from decorators import validate_ticker

router = APIRouter()
logger = logging.getLogger("routes.anomaly")


@router.get("/anomaly/{ticker}", response_model=AnomalyResponse)
@validate_ticker
async def get_anomaly_status(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    api_key: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    Retrieves the current social volume anomaly and hype storm monitoring alert status.
    Uses CacheManager for consistent caching across all routes.
    """
    ticker = ticker.upper().strip()
    cache_key = f"anomaly:{ticker}"

    # 1. Check Cache via CacheManager (consistent with sentiment/forecast routes)
    cached = await cache_manager.get_async(cache_key)
    if cached:
        return cached

    # 2. Query TimescaleDB
    try:
        query = text(
            "SELECT anomaly_detected, confidence, alert_level FROM anomaly_records "
            "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"
        )
        result = await db.execute(query, {"ticker": ticker})
        row = result.fetchone()

        if row:
            response_data = {
                "anomaly_detected": bool(row[0]),
                "confidence": float(row[1]),
                "alert_level": str(row[2]),
            }
        else:
            # Simulated baseline default (neutral state)
            response_data = {
                "anomaly_detected": False,
                "confidence": 0.95,
                "alert_level": "LOW",
            }

        # 3. Cache response for 5 minutes via CacheManager
        await cache_manager.set_async(cache_key, response_data, ttl=300)

        return response_data
    except Exception as e:
        logger.error(f"Failed to query anomaly status for {ticker}: {e}")
        raise DatabaseException(f"Failed to query anomaly status: {str(e)}")
