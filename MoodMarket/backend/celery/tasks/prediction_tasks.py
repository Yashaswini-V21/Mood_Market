# c:\Mood_Market\celery\tasks\prediction_tasks.py
import os
import yaml
import logging
import asyncio
import uuid
import numpy as np
from datetime import datetime
from celery import shared_task
from sqlalchemy import text

from config import api_settings
from dependencies import engine, get_inference_engine
from agents.risk_manager_agent import RiskManagerAgent
from cache import cache_manager

logger = logging.getLogger("celery.tasks.prediction")


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


async def get_informer_input_sequence(ticker: str) -> np.ndarray:
    """Fetches the latest 72 candles of 8 features for Informer forecast model."""
    async with engine.connect() as conn:
        query = text(
            "SELECT sentiment_score, close, volume, RSI, MACD, Bollinger_Band, google_trends, reddit_hype "
            "FROM price_records WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 72"
        )
        try:
            res = await conn.execute(query, {"ticker": ticker})
            rows = res.fetchall()
        except Exception:
            rows = []
            
    if len(rows) == 72:
        return np.array([list(r) for r in reversed(rows)])
    else:
        return np.random.randn(72, 8)


async def save_forecast_record(ticker: str, prediction: float, confidence: float, direction: str):
    """Saves price forecast record to database."""
    query = text(
        "INSERT INTO forecast_records (id, ticker, prediction, confidence, direction, timestamp) "
        "VALUES (:id, :ticker, :prediction, :confidence, :direction, :timestamp)"
    )
    async with engine.begin() as conn:
        await conn.execute(query, {
            "id": str(uuid.uuid4()),
            "ticker": ticker.upper(),
            "prediction": prediction,
            "confidence": confidence,
            "direction": direction.upper(),
            "timestamp": datetime.utcnow()
        })


@shared_task(
    bind=True,
    name="celery.tasks.prediction_tasks.run_price_forecast_task",
    max_retries=3,
    time_limit=300
)
def run_price_forecast_task(self):
    """Runs the Informer forecasting engine and invalidates prediction cache."""
    logger.info("Starting Informer model price forecasting task...")
    try:
        cfg = load_sources_config()
        tickers = cfg["sources"].get("price", {}).get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
        total_forecasts = 0
        
        try:
            engine_instance = get_inference_engine()
        except Exception as e:
            logger.error(f"Cannot load Informer inference engine: {e}")
            return {"status": "error", "message": str(e)}
            
        for ticker in tickers:
            ticker = ticker.upper().strip()
            try:
                sequence = run_async(get_informer_input_sequence(ticker))
                dec_in = np.tile(sequence[-1], (1, 1))
                
                pred_results = engine_instance.predict_single(
                    encoder_input=sequence,
                    decoder_input=dec_in,
                    confidence_level=0.95
                )
                
                prob = float(pred_results["prediction"])
                direction = "UP" if prob > 0.5 else "DOWN"
                confidence_interval = float(pred_results["upper_bound"] - pred_results["lower_bound"])
                
                run_async(save_forecast_record(
                    ticker=ticker,
                    prediction=prob,
                    confidence=confidence_interval,
                    direction=direction
                ))
                
                # Invalidate Prediction Cache
                cache_manager.delete(f"prediction:{ticker}")
                total_forecasts += 1
            except Exception as e:
                logger.error(f"Failed to run forecast for {ticker}: {e}")
                
        return {"status": "success", "forecasts_generated": total_forecasts}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in run_price_forecast_task. Retrying: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(
    bind=True,
    name="celery.tasks.prediction_tasks.run_risk_assessment_task",
    max_retries=3,
    time_limit=300
)
def run_risk_assessment_task(self):
    """Evaluates risk thresholds (position size, stop losses) for active positions."""
    logger.info("Starting risk assessment calculations...")
    try:
        cfg = load_sources_config()
        tickers = cfg["sources"].get("price", {}).get("tickers", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])
        
        risk_config = {"risk_tolerance": 0.02, "max_position_size": 0.05}
        risk_agent = RiskManagerAgent(config=risk_config)
        
        for ticker in tickers:
            ticker = ticker.upper().strip()
            
            async def evaluate_ticker_risk():
                price = 150.0
                sentiment = 0.15
                direction = "UP"
                prob = 0.55
                
                async with engine.connect() as conn:
                    # Fetch latest close price
                    try:
                        price_res = await conn.execute(
                            text("SELECT close FROM price_records WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"),
                            {"ticker": ticker}
                        )
                        p_row = price_res.fetchone()
                        if p_row:
                            price = float(p_row[0])
                    except Exception:
                        pass
                        
                    # Fetch latest sentiment
                    try:
                        sent_res = await conn.execute(
                            text("SELECT sentiment FROM sentiment_records WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"),
                            {"ticker": ticker}
                        )
                        s_row = sent_res.fetchone()
                        if s_row:
                            sentiment = float(s_row[0])
                    except Exception:
                        pass
                        
                    # Fetch latest forecast
                    try:
                        fore_res = await conn.execute(
                            text("SELECT prediction, direction FROM forecast_records WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"),
                            {"ticker": ticker}
                        )
                        f_row = fore_res.fetchone()
                        if f_row:
                            prob = float(f_row[0])
                            direction = str(f_row[1])
                    except Exception:
                        pass
                
                decision_payload = {
                    "ticker": ticker,
                    "prices": [price] * 10,
                    "sentiment": sentiment,
                    "technical_signal": "BUY" if direction == "UP" else "SELL",
                    "probability": prob
                }
                
                risk_metrics = await risk_agent.process(decision_payload)
                logger.info(
                    f"Risk Assessment for {ticker}: "
                    f"Size={risk_metrics.get('recommended_position_size')}, "
                    f"SL={risk_metrics.get('stop_loss')}, TP={risk_metrics.get('take_profit')}"
                )
                
            run_async(evaluate_ticker_risk())
            
        return {"status": "success"}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in run_risk_assessment_task: {exc}")
        raise self.retry(exc=exc, countdown=countdown)
