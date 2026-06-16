from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime


# Sentiment Schemas
class SentimentResponse(BaseModel):
    sentiment: float = Field(..., description="Average sentiment score between -1.0 and 1.0")
    confidence: float = Field(..., description="Confidence index of the sentiment assessment")
    updated_at: str = Field(..., description="ISO formatted timestamp of the latest update")


class PredictSentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Custom text input to analyze")
    ticker: Optional[str] = Field(None, description="Optional stock ticker associated with the text")


class TokenImportance(BaseModel):
    token: str
    importance: float


class PredictSentimentResponse(BaseModel):
    sentiment: float = Field(..., description="Analyzed sentiment score between -1.0 and 1.0")
    tokens_importance: List[Dict[str, Any]] = Field(..., description="Token-level SHAP importance weights")
    confidence: float = Field(..., description="Prediction confidence score")


# Price Forecasting Schemas
class PriceForecastResponse(BaseModel):
    prediction: float = Field(..., description="Probability of stock price going UP (0.0 to 1.0)")
    confidence: float = Field(..., description="Prediction confidence interval margin")
    direction: str = Field(..., description="Predicted direction: 'UP' or 'DOWN'")
    timeframe: str = Field(..., description="Target prediction horizon, e.g., '4h'")


# Anomaly Schemas
class AnomalyResponse(BaseModel):
    anomaly_detected: bool = Field(..., description="True if a social volume/hype anomaly is active")
    confidence: float = Field(..., description="Statistical confidence score of anomaly classification")
    alert_level: str = Field(..., description="Alert severity: 'LOW', 'MEDIUM', or 'HIGH'")


# Pipeline Aggregated Schemas
class PipelineRisk(BaseModel):
    recommended_position_size: str
    stop_loss: float
    take_profit: float
    max_loss: float


class PipelineResponse(BaseModel):
    sentiment: Dict[str, Any] = Field(..., description="Latest sentiment summary metrics")
    price_forecast: Dict[str, Any] = Field(..., description="Price direction forecast details")
    risk: Dict[str, Any] = Field(..., description="Risk management guidelines and sizing thresholds")
    timestamp: str = Field(..., description="ISO formatted execution time")


# Explainability Schemas
class ExplainResponse(BaseModel):
    shap_values: List[Dict[str, Any]] = Field(..., description="SHAP feature attribution scores")
    attention_weights: List[Dict[str, Any]] = Field(..., description="Aggregated multi-head self-attention weights")
    interpretation: str = Field(..., description="Human-readable breakdown of forecasting factors")


# Watchlist Schemas
class WatchlistRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Unique identification of user")
    tickers: List[str] = Field(..., description="List of stock tickers to track")
    
    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v):
        if not v:
            raise ValueError("Tickers list cannot be empty")
        return [ticker.upper().strip() for ticker in v]


class WatchlistResponse(BaseModel):
    watchlist_id: str = Field(..., description="Watchlist identification ID")
    tickers: List[str] = Field(..., description="List of tracked stock tickers")


# Health Check Schemas
class HealthResponse(BaseModel):
    status: str = Field(..., description="Server status, e.g., 'healthy'")
    models_loaded: bool = Field(..., description="True if local Informer model is loaded successfully")
    db_connected: bool = Field(..., description="True if database pool is online")

# clean architecture alignment
