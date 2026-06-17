# c:\Mood_Market\tests\test_cache.py
import os
import sys
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import redis
import redis.asyncio as aioredis

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cache import CacheManager
from cache_stats import CacheStatsTracker
from decorators import cached


class TestCacheSystem(unittest.IsolatedAsyncioTestCase):
    """Validates Redis cache manager operations, fallbacks, decorators, and statistics."""

    async def asyncSetUp(self):
        # Create a CacheManager instance with a mock Redis client for isolated testing
        self.mock_redis_uri = "redis://mockhost:6379/0"
        
        with patch("redis.Redis.from_url") as mock_sync_class:
            self.mock_sync_client = MagicMock()
            mock_sync_class.return_value = self.mock_sync_client
            self.mock_sync_client.ping.return_value = True
            
            self.manager = CacheManager(redis_uri=self.mock_redis_uri)

    def test_sync_set_and_get(self):
        # Set mock return value for GET
        self.mock_sync_client.get.return_value = '"value1"'
        
        # Test SET
        set_res = self.manager.set("test_key", "value1", ttl=60)
        self.assertTrue(set_res)
        self.mock_sync_client.setex.assert_called_with("test_key", 60, '"value1"')
        
        # Test GET
        get_res = self.manager.get("test_key")
        self.assertEqual(get_res, "value1")
        self.mock_sync_client.get.assert_called_with("test_key")

    def test_sync_delete(self):
        self.manager.delete("test_key")
        self.mock_sync_client.delete.assert_called_with("test_key")

    def test_sync_clear_all(self):
        self.manager.clear_all()
        self.mock_sync_client.flushdb.assert_called_once()

    async def test_async_set_and_get(self):
        with patch("redis.asyncio.Redis.from_url") as mock_async_class:
            mock_async_client = AsyncMock()
            mock_async_class.return_value = mock_async_client
            mock_async_client.ping = AsyncMock(return_value=True)
            mock_async_client.get = AsyncMock(return_value='"async_val"')
            
            # Populate async client in manager
            await self.manager.get_async_client()
            
            # Set
            set_res = await self.manager.set_async("async_key", "async_val", ttl=10)
            self.assertTrue(set_res)
            mock_async_client.setex.assert_called_with("async_key", 10, '"async_val"')
            
            # Get
            get_res = await self.manager.get_async("async_key")
            self.assertEqual(get_res, "async_val")
            mock_async_client.get.assert_called_with("async_key")

    def test_graceful_degradation_sync(self):
        # Set standard client to raise connection issues
        self.mock_sync_client.get.side_effect = redis.exceptions.ConnectionError("Connection refused")
        self.mock_sync_client.set.side_effect = redis.exceptions.ConnectionError("Connection refused")
        
        # Should return None instead of raising exceptions
        get_res = self.manager.get("some_key")
        self.assertIsNone(get_res)
        self.assertFalse(self.manager.is_available)
        
        # Should fail-open return False silently instead of raising
        set_res = self.manager.set("some_key", "val")
        self.assertFalse(set_res)

    async def test_graceful_degradation_async(self):
        with patch("redis.asyncio.Redis.from_url") as mock_async_class:
            mock_async_client = AsyncMock()
            mock_async_class.return_value = mock_async_client
            mock_async_client.ping = AsyncMock(return_value=True)
            mock_async_client.get.side_effect = redis.exceptions.ConnectionError("Connection lost")
            
            await self.manager.get_async_client()
            
            # Should degrade and return None
            get_res = await self.manager.get_async("some_key")
            self.assertIsNone(get_res)
            self.assertFalse(self.manager.is_available)

    def test_cache_stats_tracker_offline(self):
        # Verify stats tracking fallbacks locally when Redis is unavailable
        stats_tracker = CacheStatsTracker(stats_key="test_stats")
        
        stats_tracker.record_hit()
        stats_tracker.record_miss()
        stats_tracker.record_hit()
        
        stats = stats_tracker.get_stats()
        self.assertEqual(stats["hits"], 2)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_rate"], 0.6667)

    async def test_cached_decorator(self):
        call_count = 0
        
        @cached(ttl=10, prefix="test_decorator")
        async def sample_func(ticker):
            nonlocal call_count
            call_count += 1
            return {"ticker": ticker, "count": call_count}
            
        with patch("cache.cache_manager.get_async") as mock_get, \
             patch("cache.cache_manager.set_async") as mock_set, \
             patch("cache.cache_manager.is_available", True):
            
            # 1. First invocation (miss)
            mock_get.return_value = None
            res1 = await sample_func("AAPL")
            self.assertEqual(res1["count"], 1)
            self.assertEqual(call_count, 1)
            mock_set.assert_called_once()
            
            # 2. Second invocation (hit)
            mock_get.return_value = {"ticker": "AAPL", "count": 1}
            res2 = await sample_func("AAPL")
            self.assertEqual(res2["count"], 1)
            self.assertEqual(call_count, 1)  # Internal count hasn't changed, cached hit triggered


if __name__ == "__main__":
    unittest.main()
