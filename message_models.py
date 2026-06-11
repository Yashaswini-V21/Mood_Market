# c:\Mood_Market\message_models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class SentimentUpdateMessage(BaseModel):
    sentiment: float = Field(..., description="Averaged social sentiment score (-1.0 to 1.0)")
    confidence: float = Field(..., description="Confidence index (0.0 to 1.0)")
    updated_at: str = Field(..., description="ISO formatted timestamp of update")


class PriceUpdateMessage(BaseModel):
    price: float = Field(..., description="Current close price of the asset")
    change: float = Field(..., description="Absolute price change since last observation")
    change_pct: float = Field(..., description="Percentage price change since last observation")
    timestamp: str = Field(..., description="ISO formatted timestamp of update")


class AnomalyAlertMessage(BaseModel):
    ticker: str = Field(..., description="Asset ticker symbol")
    anomaly_type: str = Field(..., description="Type of anomaly detected (e.g. hype_storm, crash)")
    confidence: float = Field(..., description="Statistical confidence score (0.0 to 1.0)")
    explanation: Optional[str] = Field(None, description="Detailed explanation of triggered rules")


class PredictionUpdateMessage(BaseModel):
    prediction: float = Field(..., description="Directional prediction probability (0.0 to 1.0)")
    confidence: float = Field(..., description="Confidence interval margin")
    direction: str = Field(..., description="Predicted direction: 'UP' or 'DOWN'")


class PortfolioUpdateMessage(BaseModel):
    user_id: str = Field(..., description="Subscribed User Identifier")
    watchlist_id: str = Field(..., description="Watchlist identification ID")
    updates: Dict[str, Any] = Field(..., description="Aggregated updates for all watched tickers")
    timestamp: str = Field(..., description="ISO formatted timestamp")
