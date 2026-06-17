# c:\Mood_Market\schema.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


class SentimentDataModel(BaseModel):
    time: datetime = Field(..., description="Timestamp of the sentiment observation")
    ticker: str = Field(..., min_length=1, max_length=16, description="Stock ticker symbol")
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score from -1.0 to 1.0")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence of the sentiment model")
    source: str = Field(..., min_length=1, max_length=32, description="Source of data (e.g., reddit, twitter, news)")
    text_sample: Optional[str] = Field(None, description="Optional snippet of the analyzed text")
    model_version: str = Field(..., min_length=1, max_length=32, description="Version of model used")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        return v.upper().strip()


class PriceDataModel(BaseModel):
    time: datetime = Field(..., description="Timestamp of the price candle")
    ticker: str = Field(..., min_length=1, max_length=16, description="Stock ticker symbol")
    open: float = Field(..., gt=0.0, description="Opening price")
    high: float = Field(..., gt=0.0, description="Highest price in candle")
    low: float = Field(..., gt=0.0, description="Lowest price in candle")
    close: float = Field(..., gt=0.0, description="Closing price")
    volume: float = Field(..., ge=0.0, description="Volume traded")
    vwap: float = Field(..., gt=0.0, description="Volume Weighted Average Price")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        return v.upper().strip()

    @field_validator("high")
    @classmethod
    def validate_high(cls, v, info):
        # High must be greater than or equal to open, close, low
        if "open" in info.data and v < info.data["open"]:
            raise ValueError("High cannot be less than open")
        if "close" in info.data and v < info.data["close"]:
            raise ValueError("High cannot be less than close")
        return v


class TechnicalIndicatorModel(BaseModel):
    time: datetime = Field(..., description="Timestamp of indicator calculation")
    ticker: str = Field(..., min_length=1, max_length=16, description="Stock ticker symbol")
    rsi: float = Field(..., ge=0.0, le=100.0, description="Relative Strength Index")
    macd: float = Field(..., description="Moving Average Convergence Divergence")
    bb_upper: float = Field(..., description="Bollinger Band Upper threshold")
    bb_lower: float = Field(..., description="Bollinger Band Lower threshold")
    bb_middle: float = Field(..., description="Bollinger Band Moving Average")
    volume_profile: Optional[Dict[str, Any]] = Field(None, description="Detailed volume distribution map")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        return v.upper().strip()


class PredictionModel(BaseModel):
    time: datetime = Field(..., description="Timestamp of prediction event")
    ticker: str = Field(..., min_length=1, max_length=16, description="Stock ticker symbol")
    predicted_direction: str = Field(..., description="Forecasted direction: 'UP' or 'DOWN'")
    predicted_price: float = Field(..., gt=0.0, description="Predicted target price")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Probability / confidence in prediction")
    actual_outcome: Optional[str] = Field(None, description="Actual outcome: 'UP' or 'DOWN'")
    model_used: str = Field(..., min_length=1, max_length=64, description="Name of model run")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional extra metadata JSON")

    @field_validator("predicted_direction", "actual_outcome")
    @classmethod
    def validate_direction(cls, v):
        if v is None:
            return v
        val = v.upper().strip()
        if val not in ["UP", "DOWN"]:
            raise ValueError("Direction must be 'UP' or 'DOWN'")
        return val


class AnomalyModel(BaseModel):
    time: datetime = Field(..., description="Timestamp of anomaly alert event")
    ticker: str = Field(..., min_length=1, max_length=16, description="Stock ticker symbol")
    anomaly_type: str = Field(..., min_length=1, max_length=32, description="Type of anomaly (e.g. hype_storm, crash)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Statistical confidence score")
    explanation: Optional[str] = Field(None, description="Reasoning / features triggered details")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        return v.upper().strip()
