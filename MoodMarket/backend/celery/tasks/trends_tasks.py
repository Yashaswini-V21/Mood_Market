import os
import yaml
import logging
import asyncio
import uuid
from datetime import datetime
from celery import shared_task
from sqlalchemy import text

from config import api_settings
from dependencies import engine
from sources.trends_source import GoogleTrendsSourceClient
from processors.data_validator import DataValidator

logger = logging.getLogger("celery.tasks.trends")


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
                "news": {
                    "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
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


async def save_trend_record(trend: dict):
    """Saves google trends interest record to the database."""
    try:
        dt = datetime.fromisoformat(trend["timestamp"])
    except Exception:
        dt = datetime.utcnow()
        
    # Table creation check inline
    create_query = text(
        "CREATE TABLE IF NOT EXISTS trends_records ("
        "id VARCHAR(64) PRIMARY KEY, "
        "ticker VARCHAR(16), "
        "interest FLOAT, "
        "timestamp TIMESTAMP"
        ")"
    )
    
    insert_query = text(
        "INSERT INTO trends_records (id, ticker, interest, timestamp) "
        "VALUES (:id, :ticker, :interest, :timestamp) "
        "ON CONFLICT(id) DO UPDATE SET "
        "interest = EXCLUDED.interest"
    )
    
    async with engine.begin() as conn:
        await conn.execute(create_query)
        await conn.execute(insert_query, {
            "id": trend["id"],
            "ticker": trend["ticker"].upper(),
            "interest": trend["interest"],
            "timestamp": dt
        })


@shared_task(name="celery.tasks.trends_tasks.fetch_google_trends_task")
def fetch_google_trends_task():
    logger.info("Starting Google Trends fetch periodic task...")
    
    # 1. Load configuration
    cfg = load_sources_config()
    tickers = cfg["sources"].get("news", {}).get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
    
    # 2. Fetch google trends interest
    client = GoogleTrendsSourceClient()
    total_trends = 0
    
    for ticker in tickers:
        logger.info(f"Fetching Google Trends for ticker '{ticker}'")
        import time
        from monitoring import ingestion_monitor
        
        t0 = time.time()
        try:
            trends = client.fetch_trends(ticker)
            ingestion_monitor.record_fetch("trends", True, (time.time() - t0) * 1000.0)
        except Exception as e:
            logger.warning(f"Google Trends fetch failed for {ticker}: {e}")
            ingestion_monitor.record_fetch("trends", False, (time.time() - t0) * 1000.0)
            trends = []
        
        if not trends:
            continue
            
        # Run through latest 5 trends to record updates
        recent_trends = trends[-5:]
        
        for raw_trend in recent_trends:
            # Validate
            validated_trend = DataValidator.validate_google_trend(raw_trend)
            if not validated_trend:
                continue
                
            # Save to database
            t_write_start = time.time()
            try:
                run_async(save_trend_record(validated_trend))
                ingestion_monitor.record_write("trends", True, (time.time() - t_write_start) * 1000.0)
                total_trends += 1
            except Exception as e:
                logger.error(f"Failed to save Google Trend for {ticker}: {e}")
                ingestion_monitor.record_write("trends", False, (time.time() - t_write_start) * 1000.0)
                
    logger.info(f"Google Trends fetch task completed. Processed {total_trends} interest points.")
    return {"status": "success", "trends_processed": total_trends}
