import os
import yaml
import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy import text

from config import api_settings
from dependencies import engine
from sources.price_source import PriceSourceClient
from processors.data_validator import DataValidator
from processors.enricher import TechnicalIndicatorEnricher

logger = logging.getLogger("celery.tasks.price")


def load_sources_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "sources.yaml")
    if not os.path.exists(config_path):
        config_path = "config/sources.yaml"
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load sources.yaml: {e}. Using static defaults.")
        return {
            "sources": {
                "price": {
                    "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
                    "fetch_interval_minutes": 15
                }
            }
        }


def run_async(coro):
    """Helper to run async code inside Celery sync workers."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(coro))
                return future.result()
        else:
            return loop.run_until_complete(coro)


async def fetch_history_and_enrich(ticker: str, new_candle: dict) -> dict:
    """
    Fetches the last 50 price candles from the database to compute indicators
    accurately, combines them with the new candle, runs the enricher,
    and returns the updated new candle.
    """
    async with engine.connect() as conn:
        # Fetch past 50 candles
        query = text(
            "SELECT id, ticker, timestamp, open, high, low, close, volume FROM price_records "
            "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 50"
        )
        result = await conn.execute(query, {"ticker": ticker})
        rows = result.fetchall()
        
    past_candles = []
    for r in reversed(rows):
        past_candles.append({
            "id": r[0],
            "ticker": r[1],
            "timestamp": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2]),
            "open": float(r[3]),
            "high": float(r[4]),
            "low": float(r[5]),
            "close": float(r[6]),
            "volume": float(r[7])
        })
        
    # Append the new candle
    combined = past_candles + [new_candle]
    
    # Calculate indicators
    enricher = TechnicalIndicatorEnricher()
    enriched = enricher.enrich_candles(combined)
    
    # Return only the newly enriched candle
    return enriched[-1]


async def get_latest_sentiment_and_trends(ticker: str) -> tuple:
    """Queries latest sentiment and google trends for ticker."""
    sentiment = 0.15  # Default neutral positive
    reddit_hype = 0.3  # Default baseline volume
    google_trends = 50.0  # Default neutral score
    
    async with engine.connect() as conn:
        try:
            # Latest sentiment
            sent_query = text(
                "SELECT sentiment, confidence FROM sentiment_records "
                "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"
            )
            res = await conn.execute(sent_query, {"ticker": ticker})
            row = res.fetchone()
            if row:
                sentiment = float(row[0])
                reddit_hype = float(row[1])  # Use confidence as proxy for hype / strength
        except Exception as e:
            logger.warning(f"Could not fetch sentiment for {ticker}: {e}")
            
        try:
            # Latest google trend
            trend_query = text(
                "SELECT interest FROM trends_records "
                "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"
            )
            res = await conn.execute(trend_query, {"ticker": ticker})
            row = res.fetchone()
            if row:
                google_trends = float(row[0])
        except Exception as e:
            # Table may not exist yet, ignore
            pass
            
    return sentiment, reddit_hype, google_trends


async def save_price_candle(candle: dict):
    """Inserts or updates a price candle record in the database."""
    query = text(
        "INSERT INTO price_records (id, ticker, timestamp, open, high, low, close, volume, "
        "RSI, MACD, Bollinger_Band, google_trends, reddit_hype, sentiment_score) "
        "VALUES (:id, :ticker, :timestamp, :open, :high, :low, :close, :volume, "
        ":RSI, :MACD, :Bollinger_Band, :google_trends, :reddit_hype, :sentiment_score) "
        "ON CONFLICT(id) DO UPDATE SET "
        "open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, close = EXCLUDED.close, "
        "volume = EXCLUDED.volume, RSI = EXCLUDED.RSI, MACD = EXCLUDED.MACD, "
        "Bollinger_Band = EXCLUDED.Bollinger_Band, google_trends = EXCLUDED.google_trends, "
        "reddit_hype = EXCLUDED.reddit_hype, sentiment_score = EXCLUDED.sentiment_score"
    )
    
    try:
        dt = datetime.fromisoformat(candle["timestamp"])
    except Exception:
        dt = datetime.utcnow()
        
    async with engine.begin() as conn:
        await conn.execute(query, {
            "id": candle["id"],
            "ticker": candle["ticker"].upper(),
            "timestamp": dt,
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": candle["close"],
            "volume": candle["volume"],
            "RSI": candle.get("RSI", 50.0),
            "MACD": candle.get("MACD", 0.0),
            "Bollinger_Band": candle.get("Bollinger_Band", 0.0),
            "google_trends": candle.get("google_trends", 50.0),
            "reddit_hype": candle.get("reddit_hype", 0.3),
            "sentiment_score": candle.get("sentiment_score", 0.15)
        })


@shared_task(name="celery.tasks.price_tasks.fetch_price_data_task")
def fetch_price_data_task():
    logger.info("Starting Price fetch periodic task...")
    
    # 1. Load configuration
    cfg = load_sources_config()
    price_cfg = cfg["sources"]["price"]
    tickers = price_cfg.get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
    
    # 2. Fetch price data
    client = PriceSourceClient()
    total_candles = 0
    
    for ticker in tickers:
        logger.info(f"Fetching price history for ticker '{ticker}'")
        import time
        from monitoring import ingestion_monitor
        
        t0 = time.time()
        try:
            candles = client.fetch_price_history(ticker, interval="15m", period="5d")
            ingestion_monitor.record_fetch("price", True, (time.time() - t0) * 1000.0)
        except Exception as e:
            logger.warning(f"Price fetch failed for {ticker}: {e}")
            ingestion_monitor.record_fetch("price", False, (time.time() - t0) * 1000.0)
            candles = []
        
        if not candles:
            continue
            
        # Get only the latest candle to ingest (or insert multiple missing candles)
        # For a periodic task, we can just process the last 5 candles to ensure continuity
        recent_candles = candles[-5:]
        
        for raw_candle in recent_candles:
            # Validate
            validated_candle = DataValidator.validate_price_candle(raw_candle)
            if not validated_candle:
                continue
                
            # Enrich indicators
            try:
                enriched_candle = run_async(fetch_history_and_enrich(ticker, validated_candle))
            except Exception as e:
                logger.warning(f"Indicator calculation failed for {ticker}: {e}. Saving standard candle.")
                enriched_candle = validated_candle
                enriched_candle["RSI"] = 50.0
                enriched_candle["MACD"] = 0.0
                enriched_candle["Bollinger_Band"] = 0.0
                
            # Merge latest social sentiment & google trends values
            try:
                sentiment, reddit_hype, google_trends = run_async(get_latest_sentiment_and_trends(ticker))
                enriched_candle["sentiment_score"] = sentiment
                enriched_candle["reddit_hype"] = reddit_hype
                enriched_candle["google_trends"] = google_trends
            except Exception as e:
                logger.warning(f"Failed to merge sentiment/trends for {ticker}: {e}")
                
            # Save to database
            t_write_start = time.time()
            try:
                run_async(save_price_candle(enriched_candle))
                ingestion_monitor.record_write("price", True, (time.time() - t_write_start) * 1000.0)
                total_candles += 1
            except Exception as e:
                logger.error(f"Failed to save price candle for {ticker}: {e}")
                ingestion_monitor.record_write("price", False, (time.time() - t_write_start) * 1000.0)
                
    logger.info(f"Price fetch task completed. Processed {total_candles} price candles.")
    return {"status": "success", "candles_processed": total_candles}

# clean architecture alignment
