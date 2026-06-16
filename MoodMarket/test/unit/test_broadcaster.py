import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import time
import sys
import os

# Adjust path to import from parent folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from channel_manager import ChannelManager, TokenBucket
from broadcaster import RealTimeBroadcaster


class MockWebSocket:
    def __init__(self):
        self.accept = AsyncMock()
        self.send_text = AsyncMock()
        self.send_json = AsyncMock()


class TestChannelManagerAndBroadcaster(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for ChannelManager, TokenBucket rate limiter, and RealTimeBroadcaster.
    """

    async def test_token_bucket_rate_limiter(self):
        """Test TokenBucket consume logic and capacity limits"""
        bucket = TokenBucket(capacity=2.0, refill_rate=1.0)
        self.assertTrue(bucket.consume())
        self.assertTrue(bucket.consume())
        # Third consumption should fail as tokens are exhausted
        self.assertFalse(bucket.consume())

    async def test_channel_manager_connect_disconnect(self):
        """Test client connection registration and teardown"""
        manager = ChannelManager()
        ws = MockWebSocket()
        
        await manager.connect(ws, "price:AAPL")
        self.assertIn("price:AAPL", manager.active_connections)
        self.assertIn(ws, manager.active_connections["price:AAPL"])
        self.assertIn(ws, manager.client_limiters)
        
        await manager.disconnect(ws, "price:AAPL")
        self.assertNotIn("price:AAPL", manager.active_connections)
        self.assertNotIn(ws, manager.client_limiters)

    async def test_channel_manager_broadcast_deduplication(self):
        """Test connection broadcast and strict message hashing deduplication"""
        manager = ChannelManager()
        ws = MockWebSocket()
        await manager.connect(ws, "price:AAPL")
        
        # Initial broadcast
        payload = {"price": 100.0, "ticker": "AAPL"}
        success = await manager.broadcast("price:AAPL", payload)
        self.assertTrue(success)
        ws.send_text.assert_called_once()
        
        # Re-broadcast identical payload (should trigger deduplication and return False)
        ws.send_text.reset_mock()
        success = await manager.broadcast("price:AAPL", payload)
        self.assertFalse(success)
        ws.send_text.assert_not_called()
        
        # Broadcast modified payload (should go through)
        payload_new = {"price": 101.5, "ticker": "AAPL"}
        success = await manager.broadcast("price:AAPL", payload_new)
        self.assertTrue(success)
        self.assertEqual(ws.send_text.call_count, 1)

    async def test_broadcaster_anomaly_alert(self):
        """Test trigger_anomaly_alert publishes correctly formatted payloads"""
        manager = ChannelManager()
        ws = MockWebSocket()
        await manager.connect(ws, "anomaly")
        
        broadcaster = RealTimeBroadcaster(manager, ["AAPL"])
        await broadcaster.trigger_anomaly_alert("AAPL", "HYPE_STORM", 0.92, "High social mentions")
        
        self.assertEqual(ws.send_text.call_count, 1)
        args, _ = ws.send_text.call_args
        import json
        sent_data = json.loads(args[0])
        self.assertEqual(sent_data["ticker"], "AAPL")
        self.assertEqual(sent_data["anomaly_type"], "HYPE_STORM")
        self.assertEqual(sent_data["confidence"], 0.92)

    async def test_broadcaster_start_stop(self):
        """Test starting and stopping broadcaster background loop handles tasks gracefully"""
        manager = ChannelManager()
        broadcaster = RealTimeBroadcaster(manager, ["AAPL"])
        
        with patch.object(broadcaster, '_price_loop', new_callable=AsyncMock) as mock_price, \
             patch.object(broadcaster, '_sentiment_loop', new_callable=AsyncMock) as mock_sentiment, \
             patch.object(broadcaster, '_prediction_loop', new_callable=AsyncMock) as mock_prediction:
             
            broadcaster.start()
            self.assertEqual(len(broadcaster.tasks), 3)
            broadcaster.stop()
            self.assertEqual(len(broadcaster.tasks), 0)


if __name__ == "__main__":
    unittest.main()

# clean architecture alignment
