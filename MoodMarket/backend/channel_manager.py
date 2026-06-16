# c:\Mood_Market\channel_manager.py
import asyncio
import logging
import json
import hashlib
import time
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger("channel_manager")


class TokenBucket:
    """Token bucket rate limiter to throttle high-frequency client message broadcasts."""
    def __init__(self, capacity: float = 10.0, refill_rate: float = 5.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class ChannelManager:
    """Manages active WebSocket connections grouped by topics and handles deduplication/heartbeats."""

    def __init__(self):
        # Mapping: channel_name (e.g. price:AAPL) -> Set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Mapping: channel_name -> MD5 hash of last broadcasted message
        self.last_message_hashes: Dict[str, str] = {}
        # Mapping: WebSocket -> client-specific rate limit bucket
        self.client_limiters: Dict[WebSocket, TokenBucket] = {}
        # Lock to ensure connection updates are thread-safe / async-safe
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str):
        """Accepts connection and adds it to the active subscriptions registry."""
        await websocket.accept()
        async with self.lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)
            self.client_limiters[websocket] = TokenBucket(capacity=10.0, refill_rate=5.0)
            logger.info(f"WebSocket client subscribed to channel: {channel}. Current active subscribers: {len(self.active_connections[channel])}")

    async def disconnect(self, websocket: WebSocket, channel: str):
        """Removes the connection from the active subscriptions registry."""
        async with self.lock:
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)
                if not self.active_connections[channel]:
                    self.active_connections.pop(channel, None)
                    self.last_message_hashes.pop(channel, None)
            self.client_limiters.pop(websocket, None)
            logger.info(f"WebSocket client unsubscribed from channel: {channel}")

    async def broadcast(self, channel: str, message: Dict[str, Any]) -> bool:
        """
        Broadcasts a serialized message to all clients subscribed to a channel.
        Applies deduplication and token-bucket rate-limiting.
        """
        async with self.lock:
            connections = self.active_connections.get(channel, set())
            if not connections:
                return False

            # Convert message to sorted-key JSON string for stable hashing
            msg_str = json.dumps(message, sort_keys=True)
            msg_hash = hashlib.md5(msg_str.encode("utf-8")).hexdigest()

            # Deduplication check
            if self.last_message_hashes.get(channel) == msg_hash:
                logger.debug(f"Broadcast deduplicated for channel '{channel}'. Message skipped.")
                return False

            self.last_message_hashes[channel] = msg_hash

            dead_sockets = set()
            for ws in list(connections):
                # Apply rate limiting per subscriber socket
                limiter = self.client_limiters.get(ws)
                if limiter and not limiter.consume():
                    logger.warning(f"Rate limit exceeded for client on channel '{channel}'. Dropping message.")
                    continue
                    
                try:
                    await ws.send_text(msg_str)
                except Exception as e:
                    logger.warning(f"Failed to transmit data to client on '{channel}': {e}. Staging disconnection.")
                    dead_sockets.add(ws)

            # Cleanup failed connections
            for ws in dead_sockets:
                connections.discard(ws)
                self.client_limiters.pop(ws, None)

            if not connections:
                self.active_connections.pop(channel, None)
                self.last_message_hashes.pop(channel, None)

            return True

    async def start_heartbeat_loop(self, ping_interval_seconds: float = 30.0):
        """Continuously sends ping frames to keep connections alive and prune stale sockets."""
        logger.info("Starting WebSocket heartbeat loop...")
        while True:
            await asyncio.sleep(ping_interval_seconds)
            async with self.lock:
                # Clean up rate limiters for disconnected sockets
                all_active = set()
                for conns in self.active_connections.values():
                    all_active.update(conns)
                for ws in list(self.client_limiters.keys()):
                    if ws not in all_active:
                        self.client_limiters.pop(ws, None)
                        
                for channel in list(self.active_connections.keys()):
                    connections = self.active_connections[channel]
                    dead_sockets = set()
                    for ws in list(connections):
                        try:
                            await ws.send_json({"type": "ping"})
                        except Exception:
                            dead_sockets.add(ws)
                            
                    for ws in dead_sockets:
                        connections.discard(ws)
                        self.client_limiters.pop(ws, None)
                        
                    if not connections:
                        self.active_connections.pop(channel, None)
                        self.last_message_hashes.pop(channel, None)

# clean architecture alignment
