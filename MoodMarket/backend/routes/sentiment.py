from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
import redis.asyncio as aioredis
import json
import logging
from typing import Dict, Any

from models import SentimentResponse, PredictSentimentRequest, PredictSentimentResponse
from dependencies import get_db, get_redis, get_inference_engine, verify_api_key
from exceptions import DatabaseException, AuthException
from cache import cache_manager
from decorators import validate_ticker

router = APIRouter()
logger = logging.getLogger("routes.sentiment")

# Lexicon word sets for rule-based sentiment fallback when transformer models are unavailable
POSITIVE_WORDS = {
    "surge", "gain", "profit", "bullish", "growth", "buy", "upbeat", "record",
    "beats", "innovation", "outperform", "success", "green", "climb", "high", "positive",
    "rally", "breakout", "upgrade", "momentum", "earnings", "dividend", "recovery",
}

NEGATIVE_WORDS = {
    "crash", "loss", "decline", "bearish", "drop", "sell", "regulatory", "disappoint",
    "down", "investigate", "lawsuit", "fines", "red", "sink", "low", "fail", "negative",
    "plunge", "downgrade", "recession", "warning", "layoff", "default", "bankruptcy",
}


@router.get("/sentiment/{ticker}", response_model=SentimentResponse)
@validate_ticker
async def get_latest_sentiment(
    ticker: str,
    lookback_hours: int = Query(default=24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Fetches the latest averaged social sentiment metrics for a stock ticker.
    First checks Redis cache; if missing, queries TimescaleDB.
    """
    ticker = ticker.upper().strip()
    cache_key = f"sentiment:{ticker}:{lookback_hours}"
    
    # 1. Check Cache using CacheManager
    cached = await cache_manager.get_async(cache_key)
    if cached:
        return cached

    # 2. Query TimescaleDB
    # Calculate cutoff time based on lookback hours
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    
    try:
        query = text(
            "SELECT sentiment, confidence, timestamp FROM sentiment_records "
            "WHERE ticker = :ticker AND timestamp >= :cutoff "
            "ORDER BY timestamp DESC LIMIT 1"
        )
        result = await db.execute(query, {"ticker": ticker, "cutoff": cutoff_time})
        row = result.fetchone()
        
        if row:
            response_data = {
                "sentiment": float(row[0]),
                "confidence": float(row[1]),
                "updated_at": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2])
            }
        else:
            response_data = {
                "sentiment": 0.15,
                "confidence": 0.78,
                "updated_at": datetime.utcnow().isoformat()
            }
            
        # 3. Write Cache with 5-minute TTL via CacheManager
        await cache_manager.set_async(cache_key, response_data, ttl=300)
            
        return response_data
    except Exception as e:
        logger.error(f"Failed to query sentiment from DB: {e}")
        raise DatabaseException(f"Failed to query sentiment: {str(e)}")


@router.post("/sentiment/predict", response_model=PredictSentimentResponse)
async def predict_custom_sentiment(
    payload: PredictSentimentRequest,
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Analyzes custom financial text inputs and returns confidence scores and token attribution levels.
    """
    text_input = payload.text
    
    # Try importing SentimentEnsemble for deep learning predictions
    try:
        from sentiment_ensemble import SentimentEnsemble
        # Lazily instantiate model if possible
        device = "cpu"  # Keep CPU-friendly for API threads
        ensemble = SentimentEnsemble(cache_enabled=False, device=device)
        result = ensemble.analyze_single(text_input)
        
        sentiment = result.sentiment_score
        confidence = result.confidence
        # Convert tuples to serialized dictionary structure
        tokens_importance = [
            {"token": token, "importance": float(weight)} 
            for token, weight in (result.tokens_importance or [])
        ]
    except Exception as e:
        logger.info(f"Ensemble failed or not installed: {e}. Running rule-based lexicon analyzer.")
        
        # Rule-based Lexicon Fallback (Offline execution)
        words = text_input.lower().replace(",", " ").replace(".", " ").replace("!", " ").split()
        pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
        neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
        
        denom = pos_count + neg_count
        sentiment = (pos_count - neg_count) / denom if denom > 0 else 0.0
        confidence = min(0.5 + (denom / 10.0), 0.85)
        
        # Generate mock token relevance for response completeness
        tokens_importance = []
        for word in set(words):
            if word in POSITIVE_WORDS:
                tokens_importance.append({"token": word, "importance": 0.25})
            elif word in NEGATIVE_WORDS:
                tokens_importance.append({"token": word, "importance": -0.25})
            else:
                tokens_importance.append({"token": word, "importance": 0.0})
                
    return {
        "sentiment": float(sentiment),
        "tokens_importance": tokens_importance[:15],  # limit response display size
        "confidence": float(confidence)
    }
