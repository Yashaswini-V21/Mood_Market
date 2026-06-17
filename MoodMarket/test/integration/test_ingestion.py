import os
import sys
# Add project root to path to resolve main and dependencies
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import json
from datetime import datetime
from fastapi.testclient import TestClient

from main import app
from dependencies import get_db, get_redis, verify_api_key
from processors.data_validator import DataValidator
from processors.deduplicator import Deduplicator
from processors.enricher import TechnicalIndicatorEnricher
from sources.reddit_source import RedditSourceClient
from sources.news_source import NewsSourceClient
from sources.price_source import PriceSourceClient
from sources.trends_source import GoogleTrendsSourceClient


class TestDataValidation(unittest.TestCase):
    """Verifies that DataValidator catches invalid metrics and structures."""
    
    def test_price_candle_validation(self):
        # Valid candle
        valid_candle = {
            "id": "price_AAPL_12345",
            "ticker": "AAPL",
            "timestamp": datetime.utcnow().isoformat(),
            "open": 150.0,
            "high": 155.0,
            "low": 149.0,
            "close": 152.0,
            "volume": 1000000.0
        }
        self.assertIsNotNone(DataValidator.validate_price_candle(valid_candle))
        
        # Invalid candle (negative price)
        invalid_candle_neg = valid_candle.copy()
        invalid_candle_neg["close"] = -10.0
        self.assertIsNone(DataValidator.validate_price_candle(invalid_candle_neg))
        
        # Invalid candle (zero price)
        invalid_candle_zero = valid_candle.copy()
        invalid_candle_zero["open"] = 0.0
        self.assertIsNone(DataValidator.validate_price_candle(invalid_candle_zero))
        
    def test_google_trend_validation(self):
        # Valid trend
        valid_trend = {
            "id": "trend_AAPL_123",
            "ticker": "AAPL",
            "timestamp": datetime.utcnow().isoformat(),
            "interest": 45.5
        }
        self.assertIsNotNone(DataValidator.validate_google_trend(valid_trend))
        
        # Invalid trend (too high)
        invalid_trend_high = valid_trend.copy()
        invalid_trend_high["interest"] = 105.0
        self.assertIsNone(DataValidator.validate_google_trend(invalid_trend_high))
        
        # Invalid trend (negative interest)
        invalid_trend_neg = valid_trend.copy()
        invalid_trend_neg["interest"] = -2.0
        self.assertIsNone(DataValidator.validate_google_trend(invalid_trend_neg))

    def test_reddit_post_validation(self):
        valid_post = {
            "id": "reddit_post_1",
            "title": "Bullish on Apple earnings next week!",
            "text": "AAPL to the moon!",
            "subreddit": "wallstreetbets",
            "score": 450,
            "created_utc": 1625097600.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.assertIsNotNone(DataValidator.validate_reddit_post(valid_post))
        
        invalid_post_score = valid_post.copy()
        invalid_post_score["score"] = -10
        self.assertIsNone(DataValidator.validate_reddit_post(invalid_post_score))


class TestDeduplication(unittest.TestCase):
    """Verifies Deduplicator filters duplicate items."""
    
    def test_in_memory_deduplication(self):
        dedup = Deduplicator()
        
        # First time is not duplicate
        self.assertFalse(dedup.is_duplicate("post_123"))
        
        # Second time is duplicate
        self.assertTrue(dedup.is_duplicate("post_123"))
        
        # New key is not duplicate
        self.assertFalse(dedup.is_duplicate("post_456"))

    @patch("redis.Redis")
    def test_redis_sync_deduplication(self, mock_redis_class):
        mock_redis = MagicMock()
        # Mock set to return True (success = new key created) or False (duplicate)
        mock_redis.set.side_effect = lambda key, val, ex, nx: True if "new" in key else False
        
        dedup = Deduplicator(mock_redis)
        self.assertFalse(dedup.is_duplicate("new_post"))
        self.assertTrue(dedup.is_duplicate("dup_post"))


class TestIngestionClients(unittest.TestCase):
    """Verifies ingestion clients return expected structure and support mock mode."""

    def test_reddit_client_mock(self):
        client = RedditSourceClient()
        self.assertTrue(client.is_mock)
        posts = client.fetch_posts("wallstreetbets", limit=5)
        self.assertEqual(len(posts), 5)
        for post in posts:
            self.assertTrue(post["id"].startswith("mock_reddit_"))
            self.assertIn("score", post)

    def test_news_client_mock(self):
        client = NewsSourceClient()
        self.assertTrue(client.is_mock)
        articles = client.fetch_articles("AAPL", ["financial"], limit=3)
        self.assertEqual(len(articles), 3)
        for article in articles:
            self.assertTrue(article["id"].startswith("mock_news_"))
            self.assertEqual(article["ticker"], "AAPL")

    def test_price_client_simulated(self):
        client = PriceSourceClient()
        candles = client.fetch_price_history("AAPL", period="1d")
        self.assertTrue(len(candles) > 0)
        for c in candles:
            self.assertEqual(c["ticker"], "AAPL")
            self.assertIn("close", c)

    def test_trends_client_simulated(self):
        client = GoogleTrendsSourceClient()
        trends = client.fetch_trends("AAPL")
        self.assertTrue(len(trends) > 0)
        for t in trends:
            self.assertEqual(t["ticker"], "AAPL")
            self.assertIn("interest", t)


class TestRouteEndpoints(unittest.TestCase):
    """Verifies that FastAPI routes handle requests and dependencies correctly."""
    
    def setUp(self):
        # Override dependencies
        app.dependency_overrides[verify_api_key] = lambda: "mock_api_key"
        
        # Mock DB session
        self.mock_db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        
        # Mock Redis cache
        self.mock_redis = AsyncMock()
        self.mock_redis.get.return_value = None  # Cache miss by default
        app.dependency_overrides[get_redis] = lambda: self.mock_redis
        
        self.client = TestClient(app)
        
    def tearDown(self):
        app.dependency_overrides.clear()
        
    def test_health_endpoint(self):
        # Setup mocks for health check queries
        self.mock_redis.ping = AsyncMock(return_value=True)
        self.mock_db.execute = AsyncMock()
        
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["models_loaded"])
        self.assertTrue(data["db_connected"])

    def test_sentiment_get_endpoint(self):
        # Setup mock db query return values for sentiment query
        mock_row = [0.25, 0.82, datetime.utcnow()]
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        self.mock_db.execute.return_value = mock_result
        
        response = self.client.get("/api/v1/sentiment/AAPL")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["sentiment"], 0.25)
        self.assertEqual(data["confidence"], 0.82)
        
    def test_sentiment_predict_endpoint(self):
        payload = {"text": "Apple surges on blowout earnings report!", "ticker": "AAPL"}
        response = self.client.post("/api/v1/sentiment/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue("sentiment" in data)
        self.assertTrue("tokens_importance" in data)
        self.assertTrue("confidence" in data)

    def test_price_forecast_endpoint(self):
        mock_row = [0.65, 0.08, "UP"]
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        self.mock_db.execute.return_value = mock_result
        
        response = self.client.get("/api/v1/price/forecast/AAPL")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["prediction"], 0.65)
        self.assertEqual(data["direction"], "UP")

    def test_anomaly_endpoint(self):
        mock_row = [True, 0.96, "HIGH"]
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        self.mock_db.execute.return_value = mock_result
        
        response = self.client.get("/api/v1/anomaly/AAPL")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["anomaly_detected"])
        self.assertEqual(data["alert_level"], "HIGH")

    def test_watchlist_endpoint(self):
        # Mock check query
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None  # New user
        self.mock_db.execute.return_value = mock_result
        
        payload = {"user_id": "test_trader_123", "tickers": ["AAPL", "MSFT"]}
        response = self.client.post("/api/v1/watchlist", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["tickers"], ["AAPL", "MSFT"])
        self.assertTrue("watchlist_id" in data)


if __name__ == "__main__":
    unittest.main()
