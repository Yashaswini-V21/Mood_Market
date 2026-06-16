# c:\Mood_Market\queries.py
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from schema import (
    SentimentDataModel,
    PriceDataModel,
    TechnicalIndicatorModel,
    AnomalyModel,
    PredictionModel
)

logger = logging.getLogger("queries")


# 1. Insert Operations (Write-optimized)

async def insert_sentiment(session: AsyncSession, model: SentimentDataModel):
    query = text(
        "INSERT INTO sentiment_data (time, ticker, sentiment_score, confidence, source, text_sample, model_version) "
        "VALUES (:time, :ticker, :sentiment_score, :confidence, :source, :text_sample, :model_version)"
    )
    await session.execute(query, model.model_dump())


async def insert_price(session: AsyncSession, model: PriceDataModel):
    query = text(
        "INSERT INTO price_data (time, ticker, open, high, low, close, volume, vwap) "
        "VALUES (:time, :ticker, :open, :high, :low, :close, :volume, :vwap)"
    )
    await session.execute(query, model.model_dump())


async def insert_indicator(session: AsyncSession, model: TechnicalIndicatorModel):
    # If volume_profile is dict, serialize as JSON or check SQLite fallback
    import json
    data = model.model_dump()
    if data.get("volume_profile") is not None:
        data["volume_profile"] = json.dumps(data["volume_profile"])
        
    query = text(
        "INSERT INTO technical_indicators (time, ticker, rsi, macd, bb_upper, bb_lower, bb_middle, volume_profile) "
        "VALUES (:time, :ticker, :rsi, :macd, :bb_upper, :bb_lower, :bb_middle, :volume_profile)"
    )
    await session.execute(query, data)


async def insert_prediction(session: AsyncSession, model: PredictionModel):
    import json
    data = model.model_dump()
    if data.get("metadata") is not None:
        data["metadata"] = json.dumps(data["metadata"])
        
    query = text(
        "INSERT INTO predictions (time, ticker, predicted_direction, predicted_price, confidence, actual_outcome, model_used, metadata) "
        "VALUES (:time, :ticker, :predicted_direction, :predicted_price, :confidence, :actual_outcome, :model_used, :metadata)"
    )
    await session.execute(query, data)


async def insert_anomaly(session: AsyncSession, model: AnomalyModel):
    query = text(
        "INSERT INTO anomalies (time, ticker, anomaly_type, confidence, explanation) "
        "VALUES (:time, :ticker, :anomaly_type, :confidence, :explanation)"
    )
    await session.execute(query, model.model_dump())


async def insert_api_log(
    session: AsyncSession,
    time: datetime,
    endpoint: str,
    status_code: int,
    latency_ms: float,
    user_id: Optional[str]
):
    query = text(
        "INSERT INTO api_logs (time, endpoint, status_code, latency_ms, user_id) "
        "VALUES (:time, :endpoint, :status_code, :latency_ms, :user_id)"
    )
    await session.execute(query, {
        "time": time,
        "endpoint": endpoint,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "user_id": user_id
    })


# 2. Retrieval & Analytical Range Queries

async def get_historical_prices(
    session: AsyncSession,
    ticker: str,
    start_time: datetime,
    end_time: datetime
) -> List[Dict[str, Any]]:
    """Fetches high-frequency price data within a time range, ordered chronologically."""
    query = text(
        "SELECT time, ticker, open, high, low, close, volume, vwap FROM price_data "
        "WHERE ticker = :ticker AND time >= :start AND time <= :end "
        "ORDER BY time ASC"
    )
    result = await session.execute(query, {
        "ticker": ticker.upper().strip(),
        "start": start_time,
        "end": end_time
    })
    rows = result.fetchall()
    return [
        {
            "time": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
            "ticker": r[1],
            "open": float(r[2]),
            "high": float(r[3]),
            "low": float(r[4]),
            "close": float(r[5]),
            "volume": float(r[6]),
            "vwap": float(r[7])
        }
        for r in rows
    ]


async def get_daily_sentiment_averages(
    session: AsyncSession,
    ticker: str,
    start_time: datetime,
    end_time: datetime
) -> List[Dict[str, Any]]:
    """Retrieves aggregated daily averages from the continuous aggregate materialized view."""
    # Under SQLite fallback, sentiment_daily_avg is a standard view, but queries run identical SQL.
    # Postgres returns 'bucket' column, SQLite will return 'bucket' column.
    query = text(
        "SELECT bucket, ticker, avg_sentiment, avg_confidence, total_samples FROM sentiment_daily_avg "
        "WHERE ticker = :ticker AND bucket >= :start AND bucket <= :end "
        "ORDER BY bucket ASC"
    )
    result = await session.execute(query, {
        "ticker": ticker.upper().strip(),
        "start": start_time,
        "end": end_time
    })
    rows = result.fetchall()
    return [
        {
            "bucket": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
            "ticker": r[1],
            "avg_sentiment": float(r[2]) if r[2] is not None else 0.0,
            "avg_confidence": float(r[3]) if r[3] is not None else 0.0,
            "total_samples": int(r[4])
        }
        for r in rows
    ]


async def get_hourly_price_ranges(
    session: AsyncSession,
    ticker: str,
    start_time: datetime,
    end_time: datetime
) -> List[Dict[str, Any]]:
    """Retrieves aggregated hourly ranges from continuous aggregate price_hourly_range view."""
    query = text(
        "SELECT bucket, ticker, open, high, low, close, volume FROM price_hourly_range "
        "WHERE ticker = :ticker AND bucket >= :start AND bucket <= :end "
        "ORDER BY bucket ASC"
    )
    result = await session.execute(query, {
        "ticker": ticker.upper().strip(),
        "start": start_time,
        "end": end_time
    })
    rows = result.fetchall()
    return [
        {
            "bucket": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
            "ticker": r[1],
            "open": float(r[2]) if r[2] is not None else 0.0,
            "high": float(r[3]) if r[3] is not None else 0.0,
            "low": float(r[4]) if r[4] is not None else 0.0,
            "close": float(r[5]) if r[5] is not None else 0.0,
            "volume": float(r[6]) if r[6] is not None else 0.0
        }
        for r in rows
    ]


async def get_weekly_returns(
    session: AsyncSession,
    ticker: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Fetches recently completed weekly return percentages for a specific ticker."""
    query = text(
        "SELECT bucket, ticker, weekly_return_pct FROM weekly_returns "
        "WHERE ticker = :ticker ORDER BY bucket DESC LIMIT :limit"
    )
    result = await session.execute(query, {
        "ticker": ticker.upper().strip(),
        "limit": limit
    })
    rows = result.fetchall()
    return [
        {
            "bucket": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
            "ticker": r[1],
            "weekly_return_pct": float(r[2]) if r[2] is not None else 0.0
        }
        for r in rows
    ]


async def query_anomalies_by_type(
    session: AsyncSession,
    ticker: str,
    anomaly_type: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Retrieves high confidence anomaly events matching a type using partial indexing filter."""
    query = text(
        "SELECT time, ticker, anomaly_type, confidence, explanation FROM anomalies "
        "WHERE ticker = :ticker AND anomaly_type = :type AND confidence >= 0.90 "
        "ORDER BY time DESC LIMIT :limit"
    )
    result = await session.execute(query, {
        "ticker": ticker.upper().strip(),
        "type": anomaly_type,
        "limit": limit
    })
    rows = result.fetchall()
    return [
        {
            "time": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
            "ticker": r[1],
            "anomaly_type": r[2],
            "confidence": float(r[3]),
            "explanation": r[4]
        }
        for r in rows
    ]

# clean architecture alignment
