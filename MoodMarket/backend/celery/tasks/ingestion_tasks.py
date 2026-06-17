# c:\Mood_Market\celery\tasks\ingestion_tasks.py
import os
import re
import yaml
import logging
import asyncio
import uuid
import time
from datetime import datetime
from celery import shared_task
from sqlalchemy import text

from config import api_settings
from dependencies import engine
from sources.reddit_source import RedditSourceClient
from sources.news_source import NewsSourceClient
from sources.price_source import PriceSourceClient
from sources.trends_source import GoogleTrendsSourceClient
from processors.data_validator import DataValidator
from processors.deduplicator import Deduplicator

logger = logging.getLogger("celery.tasks.ingestion")


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
                },
                "price": {
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


async def save_trend_record(trend: dict):
    """Saves google trends interest record to the database."""
    try:
        dt = datetime.fromisoformat(trend["timestamp"])
    except Exception:
        dt = datetime.utcnow()
        
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


def analyze_sentiment_fallback(text_content: str):
    """Rule-based fallback for sentiment scoring."""
    positive_words = {"surge", "gain", "profit", "bullish", "growth", "buy", "upbeat", "record"}
    negative_words = {"crash", "loss", "decline", "bearish", "drop", "sell", "regulatory", "disappoint"}
    words = text_content.lower().replace(",", " ").replace(".", " ").replace("!", " ").split()
    pos_count = sum(1 for w in words if w in positive_words)
    neg_count = sum(1 for w in words if w in negative_words)
    denom = pos_count + neg_count
    sentiment = (pos_count - neg_count) / denom if denom > 0 else 0.0
    confidence = min(0.5 + (denom / 10.0), 0.85)
    return sentiment, confidence


@shared_task(
    bind=True,
    name="celery.tasks.ingestion_tasks.fetch_reddit_posts_task",
    max_retries=3,
    time_limit=300
)
def fetch_reddit_posts_task(self):
    """Scrapes WallStreetBets and stock subreddits for sentiment indicators."""
    logger.info("Starting Reddit fetch periodic task...")
    try:
        cfg = load_sources_config()
        reddit_cfg = cfg["sources"]["reddit"]
        subreddits = reddit_cfg.get("subreddits", ["wallstreetbets", "stocks", "investing"])
        limit = reddit_cfg.get("limit_posts_per_interval", 100)
        tickers_to_track = cfg["sources"].get("news", {}).get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
        
        client = RedditSourceClient()
        
        import redis
        try:
            redis_sync = redis.Redis.from_url(api_settings.redis_uri, decode_responses=True)
        except Exception:
            redis_sync = None
        deduplicator = Deduplicator(redis_sync)
        
        total_new_posts = 0
        for sub in subreddits:
            try:
                posts = client.fetch_posts(sub, limit=limit)
            except Exception as e:
                logger.warning(f"Reddit fetch failed for r/{sub}: {e}")
                posts = []
            
            for post in posts:
                validated_post = DataValidator.validate_reddit_post(post)
                if not validated_post or deduplicator.is_duplicate(validated_post["id"]):
                    continue
                
                total_new_posts += 1
                text_to_analyze = f"{validated_post['title']}. {validated_post['text']}"
                mentioned_tickers = [t for t in tickers_to_track if re.search(r'\b' + re.escape(t) + r'\b', text_to_analyze, re.IGNORECASE)]
                
                if not mentioned_tickers:
                    matches = re.findall(r'\b[A-Z]{3,4}\b', text_to_analyze)
                    mentioned_tickers = [m for m in matches if m in tickers_to_track]
                
                if not mentioned_tickers:
                    mentioned_tickers = ["SPY"]
                
                try:
                    from sentiment_ensemble import SentimentEnsemble
                    ensemble = SentimentEnsemble(cache_enabled=False, device="cpu")
                    sentiment_res = ensemble.analyze_single(text_to_analyze)
                    sentiment = sentiment_res.sentiment_score
                    confidence = sentiment_res.confidence
                except Exception:
                    sentiment, confidence = analyze_sentiment_fallback(text_to_analyze)
                
                for ticker in set(mentioned_tickers):
                    try:
                        run_async(save_sentiment_record(ticker, sentiment, confidence, validated_post["timestamp"]))
                    except Exception as e:
                        logger.error(f"Failed to save Reddit sentiment: {e}")
                        
        return {"status": "success", "new_posts_processed": total_new_posts}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in fetch_reddit_posts_task. Retrying in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(
    bind=True,
    name="celery.tasks.ingestion_tasks.fetch_news_articles_task",
    max_retries=3,
    time_limit=300
)
def fetch_news_articles_task(self):
    """Scrapes financial newsletters for sentiment analysis."""
    logger.info("Starting News fetch periodic task...")
    try:
        cfg = load_sources_config()
        news_cfg = cfg["sources"]["news"]
        tickers = news_cfg.get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
        keywords = news_cfg.get("keywords", ["financial", "stock", "earnings", "merger", "regulatory"])
        limit = news_cfg.get("limit_articles_per_interval", 50)
        
        client = NewsSourceClient()
        
        import redis
        try:
            redis_sync = redis.Redis.from_url(api_settings.redis_uri, decode_responses=True)
        except Exception:
            redis_sync = None
        deduplicator = Deduplicator(redis_sync)
        
        total_new_articles = 0
        for ticker in tickers:
            try:
                articles = client.fetch_articles(ticker, keywords, limit=limit)
            except Exception as e:
                logger.warning(f"News fetch failed for {ticker}: {e}")
                articles = []
                
            for article in articles:
                validated_art = DataValidator.validate_news_article(article)
                if not validated_art or deduplicator.is_duplicate(validated_art["id"]):
                    continue
                
                total_new_articles += 1
                text_to_analyze = validated_art["text"]
                
                try:
                    from sentiment_ensemble import SentimentEnsemble
                    ensemble = SentimentEnsemble(cache_enabled=False, device="cpu")
                    sentiment_res = ensemble.analyze_single(text_to_analyze)
                    sentiment = sentiment_res.sentiment_score
                    confidence = sentiment_res.confidence
                except Exception:
                    sentiment, confidence = analyze_sentiment_fallback(text_to_analyze)
                    
                try:
                    run_async(save_sentiment_record(ticker, sentiment, confidence, validated_art["published_at"]))
                except Exception as e:
                    logger.error(f"Failed to save News sentiment: {e}")
                    
        return {"status": "success", "new_articles_processed": total_new_articles}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in fetch_news_articles_task. Retrying in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(
    bind=True,
    name="celery.tasks.ingestion_tasks.fetch_price_data_task",
    max_retries=3,
    time_limit=300
)
def fetch_price_data_task(self):
    """Fetches high-frequency 15-minute price bars for price feed."""
    logger.info("Starting Price fetch periodic task...")
    try:
        cfg = load_sources_config()
        price_cfg = cfg["sources"]["price"]
        tickers = price_cfg.get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
        
        client = PriceSourceClient()
        total_candles = 0
        
        for ticker in tickers:
            try:
                candles = client.fetch_price_history(ticker, period="1d")
            except Exception as e:
                logger.warning(f"Price history fetch failed for {ticker}: {e}")
                candles = []
                
            for candle in candles:
                validated = DataValidator.validate_price_candle(candle)
                if not validated:
                    continue
                
                # Fetch auxiliary indicators
                async def fetch_indicators():
                    sentiment = 0.15
                    reddit_hype = 0.3
                    google_trends = 50.0
                    async with engine.connect() as conn:
                        try:
                            sent_query = text(
                                "SELECT sentiment, confidence FROM sentiment_records "
                                "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"
                            )
                            res = await conn.execute(sent_query, {"ticker": ticker})
                            row = res.fetchone()
                            if row:
                                sentiment = float(row[0])
                                reddit_hype = float(row[1])
                        except Exception:
                            pass
                        try:
                            trend_query = text(
                                "SELECT interest FROM trends_records "
                                "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"
                            )
                            res = await conn.execute(trend_query, {"ticker": ticker})
                            row = res.fetchone()
                            if row:
                                google_trends = float(row[0])
                        except Exception:
                            pass
                    return sentiment, reddit_hype, google_trends
                
                s, r_h, gt = run_async(fetch_indicators())
                validated["sentiment_score"] = s
                validated["reddit_hype"] = r_h
                validated["google_trends"] = gt
                
                # Add basic technical indicators
                try:
                    from processors.enricher import TechnicalIndicatorEnricher
                    enriched = TechnicalIndicatorEnricher.enrich_candle(validated)
                except Exception:
                    enriched = validated
                    
                try:
                    run_async(save_price_candle(enriched))
                    total_candles += 1
                except Exception as e:
                    logger.error(f"Failed to save price record: {e}")
                    
        return {"status": "success", "price_candles_processed": total_candles}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in fetch_price_data_task. Retrying in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(
    bind=True,
    name="celery.tasks.ingestion_tasks.fetch_google_trends_task",
    max_retries=3,
    time_limit=300
)
def fetch_google_trends_task(self):
    """Pulls search trend metrics to determine user interest thresholds."""
    logger.info("Starting Google Trends fetch periodic task...")
    try:
        cfg = load_sources_config()
        tickers = cfg["sources"].get("news", {}).get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
        
        client = GoogleTrendsSourceClient()
        total_trends = 0
        
        for ticker in tickers:
            try:
                trends = client.fetch_trends(ticker)
            except Exception as e:
                logger.warning(f"Google Trends fetch failed for {ticker}: {e}")
                trends = []
                
            if not trends:
                continue
                
            for raw_trend in trends[-5:]:
                validated_trend = DataValidator.validate_google_trend(raw_trend)
                if not validated_trend:
                    continue
                    
                try:
                    run_async(save_trend_record(validated_trend))
                    total_trends += 1
                except Exception as e:
                    logger.error(f"Failed to save Google Trend: {e}")
                    
        return {"status": "success", "trends_processed": total_trends}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in fetch_google_trends_task. Retrying in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)
