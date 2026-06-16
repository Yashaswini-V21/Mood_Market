import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import sys
import os
from fastapi import HTTPException

# Adjust path to import from parent folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decorators import cached, validate_ticker
from cache import cache_manager


class TestDecorators(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for custom route/service decorators (caching and input validation).
    """

    async def test_validate_ticker_correct_formats(self):
        """Test that validate_ticker allows correct symbols through"""
        @validate_ticker
        async def dummy_route(ticker: str):
            return "ok"
            
        self.assertEqual(await dummy_route(ticker="AAPL"), "ok")
        self.assertEqual(await dummy_route(ticker="tsla"), "ok")
        self.assertEqual(await dummy_route(ticker="NVDA"), "ok")

    async def test_validate_ticker_incorrect_formats(self):
        """Test that validate_ticker correctly rejects bad symbols with HTTP 400"""
        @validate_ticker
        async def dummy_route(ticker: str):
            return "ok"
            
        # Too long
        with self.assertRaises(HTTPException) as context:
            await dummy_route(ticker="INVALIDTICKER")
        self.assertEqual(context.exception.status_code, 400)
        
        # Numeric characters
        with self.assertRaises(HTTPException) as context:
            await dummy_route(ticker="AAP1")
        self.assertEqual(context.exception.status_code, 400)
        
        # Empty
        with self.assertRaises(HTTPException) as context:
            await dummy_route(ticker="")
        self.assertEqual(context.exception.status_code, 400)

    @patch("cache.cache_manager.get_async")
    @patch("cache.cache_manager.set_async")
    async def test_cached_decorator_flow(self, mock_set, mock_get):
        """Test cached decorator on cache miss and hit conditions"""
        # Set cache status to online
        cache_manager.is_available = True
        
        # 1. Test Cache Miss
        mock_get.return_value = None
        
        call_count = 0
        @cached(ttl=120, prefix="calc")
        async def complex_multiplier(multiplier: int, factor: int = 2):
            nonlocal call_count
            call_count += 1
            return multiplier * factor
            
        res1 = await complex_multiplier(10, factor=3)
        self.assertEqual(res1, 30)
        self.assertEqual(call_count, 1)
        mock_get.assert_called_once_with("calc:10:factor_3")
        mock_set.assert_called_once_with("calc:10:factor_3", 30, ttl=120)
        
        # 2. Test Cache Hit
        mock_get.reset_mock()
        mock_set.reset_mock()
        mock_get.return_value = 99
        
        res2 = await complex_multiplier(10, factor=3)
        self.assertEqual(res2, 99)
        self.assertEqual(call_count, 1) # Internal function not called
        mock_get.assert_called_once_with("calc:10:factor_3")
        mock_set.assert_not_called()


if __name__ == "__main__":
    unittest.main()

# clean architecture alignment
