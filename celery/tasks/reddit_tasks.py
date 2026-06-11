import os
import yaml
import logging
import asyncio
import uuid
import re
from datetime import datetime
from celery import shared_task
from sqlalchemy import text

from config import api_settings
from dependencies import engine, get_redis
from sources.reddit_source import RedditSourceClient
from processors.data_validator import DataValidator
from processors.deduplicator import Deduplicator

logger = logging.getLogger("celery.tasks.reddit")

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
                "reddit": {
                    "subreddits": ["wallstreetbets", "stocks", "investing"],
                    "limit_posts_per_interval": 100
                },
                "news": {
                    "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
                    "keywords": ["financial", "stock", "earnings", "merger", "regulatory"]
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


@shared_task(name="celery.tasks.reddit_tasks.fetch_reddit_posts_task")
def fetch_reddit_posts_task():
    logger.info("Starting Reddit fetch periodic task...")
    
    # 1. Load configuration
    cfg = load_sources_config()
    reddit_cfg = cfg["sources"]["reddit"]
    subreddits = reddit_cfg.get("subreddits", ["wallstreetbets", "stocks", "investing"])
    limit = reddit_cfg.get("limit_posts_per_interval", 100)
    
    tickers_to_track = cfg["sources"].get("news", {}).get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
    
    # 2. Initialize clients and processors
    client = RedditSourceClient()
    
    # Connect to Redis sync for deduplication
    try:
        import redis
        # Parse redis URI
        redis_sync = redis.Redis.from_url(api_settings.redis_uri, decode_responses=True)
    except Exception as e:
        logger.warning(f"Could not connect to Redis for deduplication: {e}. Using memory fallback.")
        redis_sync = None
        
    deduplicator = Deduplicator(redis_sync)
    
    total_new_posts = 0
    
    for sub in subreddits:
        logger.info(f"Fetching posts from r/{sub} (limit={limit})")
        import time
        from monitoring import ingestion_monitor
        
        t0 = time.time()
        try:
            posts = client.fetch_posts(sub, limit=limit)
            ingestion_monitor.record_fetch("reddit", True, (time.time() - t0) * 1000.0)
        except Exception as e:
            logger.warning(f"Reddit fetch failed: {e}")
            ingestion_monitor.record_fetch("reddit", False, (time.time() - t0) * 1000.0)
            posts = []
        
        for post in posts:
            # Validate
            validated_post = DataValidator.validate_reddit_post(post)
            if not validated_post:
                continue
                
            # Deduplicate
            if deduplicator.is_duplicate(validated_post["id"]):
                continue
                
            total_new_posts += 1
            text_to_analyze = f"{validated_post['title']}. {validated_post['text']}"
            
            # Check which tickers are mentioned in this post
            mentioned_tickers = []
            for ticker in tickers_to_track:
                # Match word boundary
                if re.search(r'\b' + re.escape(ticker) + r'\b', text_to_analyze, re.IGNORECASE):
                    mentioned_tickers.append(ticker)
            
            # If no specific configured tickers are found, look for general stock patterns (e.g. $AAPL)
            if not mentioned_tickers:
                matches = re.findall(r'\b[A-Z]{3,4}\b', text_to_analyze)
                for match in matches:
                    if match in tickers_to_track:
                        mentioned_tickers.append(match)
            
            # Default to broad market tracking if no specific ticker mentioned
            if not mentioned_tickers:
                # We can skip or record under a general SPY/market ticker
                mentioned_tickers = ["SPY"]
                
            # Run Sentiment Analysis
            try:
                from sentiment_ensemble import SentimentEnsemble
                # Try CPU-friendly mode
                ensemble = SentimentEnsemble(cache_enabled=False, device="cpu")
                sentiment_res = ensemble.analyze_single(text_to_analyze)
                sentiment = sentiment_res.sentiment_score
                confidence = sentiment_res.confidence
            except Exception as e:
                logger.debug(f"SentimentEnsemble unavailable: {e}. Using rule-based fallback.")
                sentiment, confidence = analyze_sentiment_fallback(text_to_analyze)
                
            # Write to database for all mentioned tickers
            for ticker in set(mentioned_tickers):
                t_write_start = time.time()
                try:
                    run_async(save_sentiment_record(ticker, sentiment, confidence, validated_post["timestamp"]))
                    ingestion_monitor.record_write("reddit", True, (time.time() - t_write_start) * 1000.0)
                except Exception as e:
                    logger.error(f"Failed to save reddit sentiment to db: {e}")
                    ingestion_monitor.record_write("reddit", False, (time.time() - t_write_start) * 1000.0)
                
    logger.info(f"Reddit fetch task completed. Processed {total_new_posts} new posts.")
    return {"status": "success", "new_posts_processed": total_new_posts}
