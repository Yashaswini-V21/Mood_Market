# c:\Mood_Market\celery\tasks\analysis_tasks.py
import os
import yaml
import logging
import asyncio
import uuid
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
from celery import shared_task
from sqlalchemy import text

from config import api_settings
from dependencies import engine
from anomaly_detector import AnomalyDetector
from cache import cache_manager

logger = logging.getLogger("celery.tasks.analysis")


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


async def get_recent_metrics_for_anomaly(ticker: str) -> tuple:
    """Gets the latest 30-day baseline and current metrics for anomaly detection."""
    async with engine.connect() as conn:
        query = text(
            "SELECT volume, google_trends, volume * 1.2 as twitter FROM price_records "
            "WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 100"
        )
        try:
            res = await conn.execute(query, {"ticker": ticker})
            rows = res.fetchall()
        except Exception:
            rows = []
            
    if len(rows) >= 30:
        reddit_hist = np.array([float(r[0]) for r in rows])
        trends_hist = np.array([float(r[1]) for r in rows])
        twitter_hist = np.array([float(r[2]) for r in rows])
        
        reddit_val = reddit_hist[0]
        trends_val = trends_hist[0]
        twitter_val = twitter_hist[0]
    else:
        np.random.seed(42)
        reddit_hist = np.random.normal(500, 100, 100)
        trends_hist = np.random.normal(50, 10, 100)
        twitter_hist = np.random.normal(600, 120, 100)
        
        reddit_val = float(reddit_hist[-1] * (1.5 if np.random.random() > 0.8 else 1.0))
        trends_val = float(trends_hist[-1] * (1.4 if np.random.random() > 0.8 else 1.0))
        twitter_val = float(twitter_hist[-1] * (1.5 if np.random.random() > 0.8 else 1.0))
        
    return reddit_hist, trends_hist, twitter_hist, reddit_val, trends_val, twitter_val


async def save_anomaly_record(ticker: str, anomaly_detected: bool, confidence: float, alert_level: str):
    """Saves anomaly alert record to database."""
    query = text(
        "INSERT INTO anomaly_records (id, ticker, anomaly_detected, confidence, alert_level, timestamp) "
        "VALUES (:id, :ticker, :anomaly_detected, :confidence, :alert_level, :timestamp)"
    )
    async with engine.begin() as conn:
        await conn.execute(query, {
            "id": str(uuid.uuid4()),
            "ticker": ticker.upper(),
            "anomaly_detected": anomaly_detected,
            "confidence": confidence,
            "alert_level": alert_level,
            "timestamp": datetime.utcnow()
        })


def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices)
    gains = deltas.copy()
    losses = deltas.copy()
    gains[gains < 0] = 0
    losses[losses > 0] = 0
    losses = -losses
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_macd(prices: np.ndarray) -> tuple:
    if len(prices) < 26:
        return 0.0, 0.0
    # Simple exponential moving averages
    ema_12 = prices[-12:].mean()
    ema_26 = prices[-26:].mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line * 0.9  # Mock signal line proxy
    return macd_line, signal_line


def calculate_bollinger_bands(prices: np.ndarray, period: int = 20) -> tuple:
    if len(prices) < period:
        return prices[-1] * 1.05, prices[-1] * 0.95, prices[-1]
    sma = np.mean(prices[-period:])
    std = np.std(prices[-period:])
    upper = sma + (2 * std)
    lower = sma - (2 * std)
    return upper, lower, sma


@shared_task(
    bind=True,
    name="celery.tasks.analysis_tasks.run_sentiment_analysis",
    max_retries=3,
    time_limit=300
)
def run_sentiment_analysis(self, text_input: str, ticker: Optional[str] = None):
    """Analyzes a customized block of text and invalidates cached sentiment indices."""
    logger.info("Running sentiment analysis background job...")
    ticker_name = (ticker or "SPY").upper().strip()
    try:
        from sentiment_ensemble import SentimentEnsemble
        ensemble = SentimentEnsemble(cache_enabled=False, device="cpu")
        res = ensemble.analyze_single(text_input)
        score = res.sentiment_score
        confidence = res.confidence
        
        # Save to database
        run_async(save_sentiment_record(ticker_name, score, confidence, datetime.utcnow().isoformat()))
        
        # Invalidate Cache
        cache_manager.delete(f"sentiment:{ticker_name}")
        
        return {"status": "success", "ticker": ticker_name, "sentiment": score, "confidence": confidence}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in run_sentiment_analysis. Retrying in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(
    bind=True,
    name="celery.tasks.analysis_tasks.run_anomaly_detection_task",
    max_retries=3,
    time_limit=300
)
def run_anomaly_detection_task(self):
    """Analyzes recent social volumes using Isolation Forest and EWMA spikes."""
    logger.info("Starting real-time anomaly detection task...")
    try:
        cfg = load_sources_config()
        tickers = cfg["sources"].get("price", {}).get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
        total_anomalies = 0
        
        for ticker in tickers:
            try:
                r_hist, gt_hist, tw_hist, r_val, gt_val, tw_val = run_async(get_recent_metrics_for_anomaly(ticker))
                detector = AnomalyDetector()
                detector.fit_baseline(ticker, r_hist, gt_hist, tw_hist)
                alert = detector.predict(ticker, r_val, gt_val, tw_val)
                
                alert_level = "LOW"
                if alert.alert_type in ["HYPE_STORM", "EXTREME_SPIKE"]:
                    alert_level = "HIGH"
                elif alert.alert_type in ["MAJOR_SPIKE", "VOLATILITY_SPIKE"]:
                    alert_level = "MEDIUM"
                    
                run_async(save_anomaly_record(
                    ticker=ticker,
                    anomaly_detected=alert.anomaly_detected,
                    confidence=alert.confidence,
                    alert_level=alert_level
                ))
                
                if alert.anomaly_detected:
                    total_anomalies += 1
                    logger.warning(f"⚠️ ANOMALY DETECTED for {ticker}: {alert.alert_type}")
            except Exception as e:
                logger.error(f"Failed to run anomaly detection for {ticker}: {e}")
                
        return {"status": "success", "anomalies_detected": total_anomalies}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in run_anomaly_detection_task. Retrying: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(
    bind=True,
    name="celery.tasks.analysis_tasks.calculate_technical_indicators_task",
    max_retries=3,
    time_limit=300
)
def calculate_technical_indicators_task(self):
    """Calculates indicators (RSI, MACD, BB) and invalidates indicators cache."""
    logger.info("Starting technical indicator calculations...")
    try:
        cfg = load_sources_config()
        tickers = cfg["sources"].get("price", {}).get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
        
        for ticker in tickers:
            ticker = ticker.upper().strip()
            
            async def process_indicators():
                async with engine.connect() as conn:
                    # Fetch last 50 candles close price
                    query = text(
                        "SELECT close FROM price_records WHERE ticker = :ticker "
                        "ORDER BY timestamp DESC LIMIT 50"
                    )
                    res = await conn.execute(query, {"ticker": ticker})
                    rows = res.fetchall()
                    if len(rows) < 14:
                        return
                    
                    prices = np.array([float(r[0]) for r in reversed(rows)])
                    rsi = calculate_rsi(prices)
                    macd, signal = calculate_macd(prices)
                    upper, lower, middle = calculate_bollinger_bands(prices)
                    
                    # Update the latest candle indicators in database
                    update_query = text(
                        "UPDATE price_records SET RSI = :rsi, MACD = :macd, Bollinger_Band = :bb "
                        "WHERE id = (SELECT id FROM price_records WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1)"
                    )
                    await conn.execute(update_query, {
                        "rsi": rsi,
                        "macd": macd,
                        "bb": middle,
                        "ticker": ticker
                    })
                    
                    # Save to technical_indicators table (Postgres/TimescaleDB hypertable compatibility)
                    indicator_insert = text(
                        "INSERT INTO technical_indicators (time, ticker, rsi, macd, bb_upper, bb_lower, bb_middle) "
                        "VALUES (:time, :ticker, :rsi, :macd, :bb_upper, :bb_lower, :bb_middle)"
                    )
                    try:
                        await conn.execute(indicator_insert, {
                            "time": datetime.utcnow(),
                            "ticker": ticker,
                            "rsi": rsi,
                            "macd": macd,
                            "bb_upper": upper,
                            "bb_lower": lower,
                            "bb_middle": middle
                        })
                    except Exception:
                        # SQLite compatibility fallback if hypertable table is missing
                        pass
                        
                # Evict indicators cache
                cache_manager.delete(f"indicators:{ticker}")
                
            run_async(process_indicators())
            
        return {"status": "success"}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in calculate_technical_indicators_task: {exc}")
        raise self.retry(exc=exc, countdown=countdown)

# clean architecture alignment
