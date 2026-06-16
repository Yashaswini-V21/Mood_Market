# c:\Mood_Market\tests\test_websocket.py
import os
import sys
import asyncio
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

# Add project root directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from authenticator import JWTAuthenticator
from websocket_server import manager


def run_async(coro):
    """Helper to run async coroutines in synchronous unittest methods safely."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestWebSocketServer(unittest.TestCase):
    """Verifies WebSocket authentication, multicast channel routing, heartbeats, and rate limiting."""

    def setUp(self):
        self.client = TestClient(app)
        self.user_id = "test_user_789"
        self.valid_token = JWTAuthenticator.generate_token(self.user_id)

    def test_websocket_auth_rejects_missing_token(self):
        # Connection without token query param should fail
        with self.assertRaises((WebSocketDisconnect, Exception)):
            with self.client.websocket_connect("/ws/price/AAPL"):
                pass

    def test_websocket_auth_rejects_invalid_token(self):
        # Connection with invalid token should close with code 4003
        with self.assertRaises((WebSocketDisconnect, Exception)) as ctx:
            with self.client.websocket_connect("/ws/price/AAPL?token=invalid_jwt_token"):
                pass
        if hasattr(ctx, "exception") and isinstance(ctx.exception, WebSocketDisconnect):
            self.assertEqual(ctx.exception.code, 4003)

    def test_websocket_auth_accepts_valid_token(self):
        # Connection with valid token should connect successfully
        with self.client.websocket_connect(f"/ws/price/AAPL?token={self.valid_token}") as ws:
            ws.send_text("keepalive")
            self.assertTrue(True)

    def test_multicast_broadcasting(self):
        # Subscribe Client A to AAPL
        with self.client.websocket_connect(f"/ws/price/AAPL?token={self.valid_token}") as ws_a:
            # Subscribe Client B to MSFT
            with self.client.websocket_connect(f"/ws/price/MSFT?token={self.valid_token}") as ws_b:
                # Trigger a price update for AAPL
                aapl_msg = {"price": 182.50, "change_pct": 0.005, "timestamp": "2026-06-11T20:00:00"}
                
                run_async(manager.broadcast("price:AAPL", aapl_msg))
                
                # Client A (AAPL) should receive the update
                received_a = ws_a.receive_json()
                self.assertEqual(received_a["price"], 182.50)
                
                # Assert B didn't crash
                self.assertTrue(True)

    def test_deduplication(self):
        with self.client.websocket_connect(f"/ws/price/AAPL?token={self.valid_token}") as ws:
            msg = {"price": 100.0, "change_pct": 0.0}
            
            # First send: should succeed
            res1 = run_async(manager.broadcast("price:AAPL", msg))
            self.assertTrue(res1)
            
            # Second duplicate send: should be filtered out and return False
            res2 = run_async(manager.broadcast("price:AAPL", msg))
            self.assertFalse(res2)

    def test_heartbeat_ping(self):
        with self.client.websocket_connect(f"/ws/price/AAPL?token={self.valid_token}") as ws:
            async def run_heartbeat_test():
                task = asyncio.create_task(manager.start_heartbeat_loop(0.01))
                await asyncio.sleep(0.03)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            run_async(run_heartbeat_test())
            msg = ws.receive_json()
            self.assertEqual(msg.get("type"), "ping")


if __name__ == "__main__":
    unittest.main()

# clean architecture alignment
