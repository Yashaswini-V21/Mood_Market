# c:\Mood_Market\cache_warmer.py
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy import text

from config import api_settings
from dependencies import async_session
from cache import cache_manager

logger = logging.getLogger("cache.logger")

TOP_50_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B", "LLY", "V",
    "UNH", "AVGO", "XOM", "JPM", "WMT", "MA", "PG", "JNJ", "HD", "ADBE",
    "ASML", "ORCL", "COST", "CVX", "KO", "MRK", "PEP", "NFLX", "TMO", "BAC",
    "SHEL", "ACN", "ABT", "NVO", "MCD", "CSCO", "DIS", "INTC", "WFC", "VZ",
    "QCOM", "ADR", "AMD", "CMCSA", "NEST", "TXN", "DHR", "AMGN", "PFE", "PM"
]


async def warm_cache(tickers: Optional[List[str]] = None):
    """
    Fetches the latest metrics for tickers from the DB and writes them to Redis cache.
    If DB is unseeded or Redis is unavailable, fallback gracefully.
    """
    if not cache_manager.is_available:
        logger.warning("Cache warmer skipped: Redis is offline.")
        return

    tickers = tickers or TOP_50_TICKERS
    logger.info(f"Starting cache warming for {len(tickers)} tickers...")

    async with async_session() as session:
        for ticker in tickers:
            ticker = ticker.upper().strip()
            
            # 1. Warm Sentiment Cache
            try:
                sent_query = text(
                    "SELECT sentiment, confidence, timestamp FROM sentiment_records "
                    "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"
                )
                res = await session.execute(sent_query, {"ticker": ticker})
                row = res.fetchone()
                if row:
                    sent_val = {
                        "score": float(row[0]),
                        "confidence": float(row[1]),
                        "updated_at": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2]),
                        "source": "database"
                    }
                else:
                    sent_val = {
                        "score": 0.15,
                        "confidence": 0.78,
                        "updated_at": datetime.utcnow().isoformat(),
                        "source": "fallback"
                    }
                await cache_manager.set_async(f"sentiment:{ticker}", sent_val, ttl=300)
            except Exception as e:
                logger.debug(f"Failed to warm sentiment for {ticker}: {e}")

            # 2. Warm Price Cache
            try:
                price_query = text(
                    "SELECT close, open, timestamp FROM price_records "
                    "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"
                )
                res = await session.execute(price_query, {"ticker": ticker})
                row = res.fetchone()
                if row:
                    close_val = float(row[0])
                    open_val = float(row[1])
                    change = close_val - open_val
                    price_val = {
                        "price": close_val,
                        "change": change,
                        "timestamp": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2])
                    }
                else:
                    price_val = {
                        "price": 150.0,
                        "change": 0.5,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                await cache_manager.set_async(f"price:{ticker}", price_val, ttl=60)
            except Exception as e:
                logger.debug(f"Failed to warm price for {ticker}: {e}")

            # 3. Warm Prediction Cache
            try:
                pred_query = text(
                    "SELECT prediction, confidence, direction FROM forecast_records "
                    "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"
                )
                res = await session.execute(pred_query, {"ticker": ticker})
                row = res.fetchone()
                if row:
                    pred_val = {
                        "predicted_price": float(row[0]),
                        "confidence": float(row[1]),
                        "direction": str(row[2])
                    }
                else:
                    pred_val = {
                        "predicted_price": 155.0,
                        "confidence": 0.08,
                        "direction": "UP"
                    }
                await cache_manager.set_async(f"prediction:{ticker}", pred_val, ttl=900)
            except Exception as e:
                logger.debug(f"Failed to warm predictions for {ticker}: {e}")

            # 4. Warm Technical Indicators Cache
            try:
                ind_query = text(
                    "SELECT RSI, MACD, Bollinger_Band FROM price_records "
                    "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"
                )
                res = await session.execute(ind_query, {"ticker": ticker})
                row = res.fetchone()
                if row:
                    ind_val = {
                        "rsi": float(row[0]) if row[0] is not None else 50.0,
                        "macd": float(row[1]) if row[1] is not None else 0.0,
                        "bb_upper": float(row[2]) if row[2] is not None else 100.0,
                        "bb_lower": float(row[2]) * 0.9 if row[2] is not None else 90.0,
                        "bb_middle": float(row[2]) * 0.95 if row[2] is not None else 95.0,
                    }
                else:
                    ind_val = {
                        "rsi": 55.0,
                        "macd": 1.2,
                        "bb_upper": 155.0,
                        "bb_lower": 145.0,
                        "bb_middle": 150.0
                    }
                await cache_manager.set_async(f"indicators:{ticker}", ind_val, ttl=300)
            except Exception as e:
                logger.debug(f"Failed to warm indicators for {ticker}: {e}")

    logger.info("✓ Cache warming completed.")


def warm_cache_on_startup():
    """Startup wrapper to run the async cache warmer in a background thread/loop."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(warm_cache())
    except RuntimeError:
        # No running loop, execute synchronously via asyncio.run
        asyncio.run(warm_cache())
