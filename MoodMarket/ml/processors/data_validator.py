import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("processors.validator")


class RedditPostSchema(BaseModel):
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    text: str = Field("")
    subreddit: str = Field(..., min_length=1)
    score: int = Field(0, ge=0)
    created_utc: float = Field(..., gt=0)
    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("timestamp must be an ISO format string")


class NewsArticleSchema(BaseModel):
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = Field("")
    text: str = Field("")
    url: str = Field("")
    source: str = Field("Unknown")
    published_at: str
    ticker: str = Field(..., min_length=1)

    @field_validator("published_at")
    @classmethod
    def validate_published_at(cls, v):
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("published_at must be an ISO format string")


class PriceCandleSchema(BaseModel):
    id: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    timestamp: str
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(0.0, ge=0)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("timestamp must be an ISO format string")


class GoogleTrendSchema(BaseModel):
    id: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    timestamp: str
    interest: float = Field(..., ge=0.0, le=100.0)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("timestamp must be an ISO format string")


class DataValidator:
    """Validates records fetched from social and market APIs."""
    
    @staticmethod
    def validate_reddit_post(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            schema = RedditPostSchema(**data)
            return schema.model_dump()
        except Exception as e:
            logger.warning(f"Reddit post validation failed for data {data}: {e}")
            return None

    @staticmethod
    def validate_news_article(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            schema = NewsArticleSchema(**data)
            return schema.model_dump()
        except Exception as e:
            logger.warning(f"News article validation failed for data {data}: {e}")
            return None

    @staticmethod
    def validate_price_candle(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            schema = PriceCandleSchema(**data)
            return schema.model_dump()
        except Exception as e:
            logger.warning(f"Price candle validation failed for data {data}: {e}")
            return None

    @staticmethod
    def validate_google_trend(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            schema = GoogleTrendSchema(**data)
            return schema.model_dump()
        except Exception as e:
            logger.warning(f"Google Trends validation failed for data {data}: {e}")
            return None
