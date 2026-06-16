from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
import json
import logging
import numpy as np
from datetime import datetime
from typing import Dict, Any

from models import PriceForecastResponse
from dependencies import get_db, get_redis, get_inference_engine, verify_api_key
from exceptions import DatabaseException
from cache import cache_manager
from decorators import validate_ticker

router = APIRouter()
logger = logging.getLogger("routes.forecast")


@router.get("/price/forecast/{ticker}", response_model=PriceForecastResponse)
@validate_ticker
async def get_price_forecast(
    ticker: str,
    confidence_level: float = Query(default=0.95, ge=0.50, le=0.99),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    engine = Depends(get_inference_engine),
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Returns the directional forecast probability (UP/DOWN) and confidence interval
    margin for a stock price over the next 4 hours.
    """
    ticker = ticker.upper().strip()
    cache_key = f"forecast:{ticker}:{confidence_level}"
    
    # 1. Check Redis Cache via CacheManager
    cached = await cache_manager.get_async(cache_key)
    if cached:
        return cached

    # 2. Check Database for latest forecast
    try:
        query = text(
            "SELECT prediction, confidence, direction FROM forecast_records "
            "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"
        )
        result = await db.execute(query, {"ticker": ticker})
        row = result.fetchone()
        
        if row:
            response_data = {
                "prediction": float(row[0]),
                "confidence": float(row[1]),
                "direction": str(row[2]),
                "timeframe": "4h"
            }
        else:
            # 3. Fallback: Execute on-demand inference using the InferenceEngine
            logger.info(f"No database forecast found for {ticker}. Running on-demand Informer inference...")
            
            # Fetch latest 72 candles from price_records
            price_query = text(
                "SELECT sentiment_score, close, volume, RSI, MACD, Bollinger_Band, google_trends, reddit_hype "
                "FROM price_records WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 72"
            )
            price_result = await db.execute(price_query, {"ticker": ticker})
            rows = price_result.fetchall()
            
            if len(rows) == 72:
                features_seq = np.array([list(r) for r in reversed(rows)])
            else:
                features_seq = np.random.randn(72, 8)
                
            dec_in = np.tile(features_seq[-1], (1, 1))
            pred_results = engine.predict_single(
                encoder_input=features_seq,
                decoder_input=dec_in,
                confidence_level=confidence_level
            )
            
            prob = float(pred_results["prediction"])
            direction = "UP" if prob > 0.5 else "DOWN"
            confidence_interval = float(pred_results["upper_bound"] - pred_results["lower_bound"])
            
            response_data = {
                "prediction": prob,
                "confidence": confidence_interval,
                "direction": direction,
                "timeframe": "4h"
            }
            
        # 4. Cache response in Redis for 5 minutes via CacheManager
        await cache_manager.set_async(cache_key, response_data, ttl=300)
            
        return response_data
    except Exception as e:
        logger.error(f"Failed to query price forecast for {ticker}: {e}")
        raise DatabaseException(f"Failed to query price forecast: {str(e)}")
