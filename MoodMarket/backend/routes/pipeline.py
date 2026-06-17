from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
import json
import logging
from datetime import datetime
from typing import Dict, Any

from models import PipelineResponse
from dependencies import get_db, get_redis, get_inference_engine, verify_api_key
from routes.sentiment import get_latest_sentiment
from routes.forecast import get_price_forecast
from agents.risk_manager_agent import RiskManagerAgent
from decorators import validate_ticker

router = APIRouter()
logger = logging.getLogger("routes.pipeline")


@router.get("/pipeline/{ticker}", response_model=PipelineResponse)
@validate_ticker
async def get_pipeline_analysis(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    engine = Depends(get_inference_engine),
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Assembles a complete analysis of the stock, combining the latest sentiment metrics,
    the Informer price direction forecast, and the active risk manager guidelines.
    """
    ticker = ticker.upper().strip()
    
    # 1. Fetch Sentiment Summary
    sentiment_data = await get_latest_sentiment(ticker, lookback_hours=24, db=db, redis=redis, api_key=api_key)
    
    # 2. Fetch Price Forecast Summary
    forecast_data = await get_price_forecast(ticker, confidence_level=0.95, db=db, redis=redis, engine=engine, api_key=api_key)
    
    # 3. Calculate Risk Sizing via RiskManagerAgent logic
    price = 0.0
    try:
        # Extract the latest close price from price_records
        from sqlalchemy import text
        query = text("SELECT close FROM price_records WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1")
        result = await db.execute(query, {"ticker": ticker})
        row = result.fetchone()
        if row:
            price = float(row[0])
        else:
            logger.warning(f"No price data found for {ticker}; risk calculations may be inaccurate.")
    except Exception:
        logger.warning(f"Failed to fetch latest price for {ticker} from DB.")
        
    # Instantiate RiskManager logic
    risk_config = {"risk_tolerance": 0.02, "max_position_size": 0.05}
    risk_agent = RiskManagerAgent(config=risk_config)
    
    direction = forecast_data["direction"]
    prob = forecast_data["prediction"]
    
    # Run risk calculations
    decision_payload = {
        "ticker": ticker,
        "prices": [price] * 10,  # feed static array for bounds
        "sentiment": sentiment_data["sentiment"],
        "technical_signal": "BUY" if direction == "UP" else "SELL",
        "probability": prob
    }
    
    # Calculate bounds
    risk_metrics = await risk_agent.process(decision_payload)
    
    return {
        "sentiment": sentiment_data,
        "price_forecast": forecast_data,
        "risk": {
            "recommended_position_size": risk_metrics.get("recommended_position_size", "1%"),
            "stop_loss": float(risk_metrics.get("stop_loss", price * 0.98)),
            "take_profit": float(risk_metrics.get("take_profit", price * 1.05)),
            "max_loss": float(risk_metrics.get("max_loss", 20.0))
        },
        "timestamp": datetime.utcnow().isoformat()
    }
