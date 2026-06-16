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
from sources.news_source import NewsSourceClient
from processors.data_validator import DataValidator
from processors.deduplicator import Deduplicator

logger = logging.getLogger("celery.tasks.news")

# Rule-based fallback words
POSITIVE_WORDS = {
    "surge", "gain", "profit", "bullish", "growth", "buy", "upbeat", "record", 
    "beats", "innovation", "outperform", "success", "green", "climb", "high", "positive"
}
NEGATIVE_WORDS = {
    "crash", "loss", "decline", "bearish", "drop", "sell", "regulatory", "disappoint", 
    "down", "investigate", "lawsuit", "fines", "red", "sink", "low", "fail", "negative"
}


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
                    "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
                    "keywords": ["financial", "stock", "earnings", "merger", "regulatory"],
                    "limit_articles_per_interval": 50
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


async def save_sentiment_record(ticker: str, sentiment: float, confidence: float, timestamp_str: str):
    """Saves sentiment record to database."""
    try:
        dt = datetime.fromisoformat(timestamp_str)
    except Exception:
        dt = datetime.utcnow()
        
    query = text(
        "INSERT INTO sentiment_records (id, ticker, sentiment, confidence, timestamp) "
        "VALUES (:id, :ticker, :sentiment, :confidence, :timestamp)"
    )
    
    async with engine.begin() as conn:
        await conn.execute(query, {
            "id": str(uuid.uuid4()),
            "ticker": ticker.upper(),
            "sentiment": sentiment,
            "confidence": confidence,
            "timestamp": dt
        })


def analyze_sentiment_fallback(text_content: str):
    """Rule-based fallback for sentiment scoring."""
    words = text_content.lower().replace(",", " ").replace(".", " ").replace("!", " ").split()
    pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    
    denom = pos_count + neg_count
    sentiment = (pos_count - neg_count) / denom if denom > 0 else 0.0
    confidence = min(0.5 + (denom / 10.0), 0.85)
    return sentiment, confidence


@shared_task(name="celery.tasks.news_tasks.fetch_news_articles_task")
def fetch_news_articles_task():
    logger.info("Starting News fetch periodic task...")
    
    # 1. Load configuration
    cfg = load_sources_config()
    news_cfg = cfg["sources"]["news"]
    tickers = news_cfg.get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
    keywords = news_cfg.get("keywords", ["financial", "stock", "earnings", "merger", "regulatory"])
    limit = news_cfg.get("limit_articles_per_interval", 50)
    
    # 2. Initialize clients and processors
    client = NewsSourceClient()
    
    try:
        import redis
        redis_sync = redis.Redis.from_url(api_settings.redis_uri, decode_responses=True)
    except Exception as e:
        logger.warning(f"Could not connect to Redis for deduplication: {e}. Using memory fallback.")
        redis_sync = None
        
    deduplicator = Deduplicator(redis_sync)
    total_new_articles = 0
    
    for ticker in tickers:
        logger.info(f"Fetching news for ticker '{ticker}'")
        import time
        from monitoring import ingestion_monitor
        
        t0 = time.time()
        try:
            articles = client.fetch_articles(ticker, keywords, limit=limit)
            ingestion_monitor.record_fetch("news", True, (time.time() - t0) * 1000.0)
        except Exception as e:
            logger.warning(f"News fetch failed for {ticker}: {e}")
            ingestion_monitor.record_fetch("news", False, (time.time() - t0) * 1000.0)
            articles = []
        
        for article in articles:
            # Validate
            validated_art = DataValidator.validate_news_article(article)
            if not validated_art:
                continue
                
            # Deduplicate
            if deduplicator.is_duplicate(validated_art["id"]):
                continue
                
            total_new_articles += 1
            text_to_analyze = validated_art["text"]
            
            # Run Sentiment Analysis
            try:
                from sentiment_ensemble import SentimentEnsemble
                ensemble = SentimentEnsemble(cache_enabled=False, device="cpu")
                sentiment_res = ensemble.analyze_single(text_to_analyze)
                sentiment = sentiment_res.sentiment_score
                confidence = sentiment_res.confidence
            except Exception as e:
                logger.debug(f"SentimentEnsemble unavailable: {e}. Using rule-based fallback.")
                sentiment, confidence = analyze_sentiment_fallback(text_to_analyze)
                
            # Save record
            t_write_start = time.time()
            try:
                run_async(save_sentiment_record(ticker, sentiment, confidence, validated_art["published_at"]))
                ingestion_monitor.record_write("news", True, (time.time() - t_write_start) * 1000.0)
            except Exception as e:
                logger.error(f"Failed to save news sentiment to db: {e}")
                ingestion_monitor.record_write("news", False, (time.time() - t_write_start) * 1000.0)
            
    logger.info(f"News fetch task completed. Processed {total_new_articles} new articles.")
    return {"status": "success", "new_articles_processed": total_new_articles}

# clean architecture alignment
