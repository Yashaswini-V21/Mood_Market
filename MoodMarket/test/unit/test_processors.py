import unittest
from unittest.mock import MagicMock, AsyncMock
import pandas as pd
import numpy as np
import sys
import os

# Adjust path to import from parent folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processors.data_validator import DataValidator
from processors.deduplicator import Deduplicator
from processors.enricher import TechnicalIndicatorEnricher


class TestProcessors(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for ingestion middleware stages: Validator, Deduplicator, and Technical Enricher.
    """

    def test_data_validator_schemas(self):
        """Test DataValidator logic against clean and corrupt inputs"""
        # 1. Reddit Post validation
        reddit_ok = {
            "id": "post_1",
            "title": "NVDA stock outlook",
            "text": "Bullish setup on daily charts",
            "subreddit": "stocks",
            "score": 150,
            "created_utc": 1625097600.0,
            "timestamp": "2026-06-15T12:00:00"
        }
        self.assertIsNotNone(DataValidator.validate_reddit_post(reddit_ok))
        
        # Corrupt Reddit post (negative score)
        reddit_bad = reddit_ok.copy()
        reddit_bad["score"] = -10
        self.assertIsNone(DataValidator.validate_reddit_post(reddit_bad))

        # 2. News Article validation
        news_ok = {
            "id": "news_1",
            "title": "Microsoft partnership",
            "description": "Microsoft forms partnership",
            "text": "Full article body here...",
            "url": "http://news.com/msft",
            "source": "Reuters",
            "published_at": "2026-06-15T12:00:00",
            "ticker": "MSFT"
        }
        self.assertIsNotNone(DataValidator.validate_news_article(news_ok))

        # 3. Price Candle validation
        price_ok = {
            "id": "candle_1",
            "ticker": "TSLA",
            "timestamp": "2026-06-15T12:00:00",
            "open": 200.0,
            "high": 205.0,
            "low": 198.5,
            "close": 201.2,
            "volume": 2500000.0
        }
        self.assertIsNotNone(DataValidator.validate_price_candle(price_ok))
        
        # Corrupt Price candle (negative open price)
        price_bad = price_ok.copy()
        price_bad["open"] = -200.0
        self.assertIsNone(DataValidator.validate_price_candle(price_bad))

        # 4. Google Trend validation
        trend_ok = {
            "id": "trend_1",
            "ticker": "AAPL",
            "timestamp": "2026-06-15T12:00:00",
            "interest": 72.0
        }
        self.assertIsNotNone(DataValidator.validate_google_trend(trend_ok))

    def test_deduplicator_memory_fallback(self):
        """Test in-memory deduplication fallback behavior"""
        dedup = Deduplicator()
        self.assertFalse(dedup.is_duplicate("post_unique_1"))
        self.assertTrue(dedup.is_duplicate("post_unique_1"))  # Now duplicate
        self.assertFalse(dedup.is_duplicate("post_unique_2"))

    def test_deduplicator_sync_redis(self):
        """Test Deduplicator with synchronous Redis set operations"""
        mock_redis = MagicMock()
        # set NX returns True if key was set (new item)
        mock_redis.set.return_value = True
        
        dedup = Deduplicator(redis_client=mock_redis)
        self.assertFalse(dedup.is_duplicate("post_redis_1"))
        
        # set NX returns False if key already exists (duplicate)
        mock_redis.set.return_value = False
        self.assertTrue(dedup.is_duplicate("post_redis_1"))

    async def test_deduplicator_async_redis(self):
        """Test Deduplicator with asynchronous Redis operations"""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        
        dedup = Deduplicator()
        self.assertFalse(await dedup.is_duplicate_async(mock_redis, "post_async_1"))
        
        mock_redis.set.return_value = False
        self.assertTrue(await dedup.is_duplicate_async(mock_redis, "post_async_1"))

    def test_technical_indicator_enricher(self):
        """Test calculation of RSI, MACD, and Bollinger Bands on candles series"""
        enricher = TechnicalIndicatorEnricher()
        
        # Construct 35 sequential candles to exceed lookback period requirements
        candles = []
        start_time = pd.Timestamp("2026-06-15 09:30:00")
        for i in range(35):
            candles.append({
                "id": f"c_{i}",
                "ticker": "AAPL",
                "timestamp": (start_time + pd.Timedelta(minutes=15 * i)).isoformat(),
                "open": 150.0 + i * 0.5,
                "high": 151.0 + i * 0.5,
                "low": 149.0 + i * 0.5,
                "close": 150.5 + i * 0.5,
                "volume": 1000.0 * (i + 1)
            })
            
        enriched_candles = enricher.enrich_candles(candles)
        self.assertEqual(len(enriched_candles), 35)
        
        # Verify that indicator keys have been injected
        for candle in enriched_candles:
            self.assertIn("RSI", candle)
            self.assertIn("MACD", candle)
            self.assertIn("Bollinger_Band", candle)
            
        # Verify specific calculation values (RSI in uptrend should be high)
        last_candle = enriched_candles[-1]
        self.assertGreater(last_candle["RSI"], 50.0)


if __name__ == "__main__":
    unittest.main()
