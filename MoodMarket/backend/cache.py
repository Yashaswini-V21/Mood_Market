# c:\Mood_Market\cache.py
import json
import logging
import time
from typing import Any, Optional
import redis
import redis.asyncio as aioredis
from config import api_settings

logger = logging.getLogger("cache.logger")


class CacheManager:
    """
    Thread-safe connection wrapper for Redis with auto-reconnection
    and graceful fail-open degradation when Redis is offline.
    """
    def __init__(self, redis_uri: str = None):
        self.redis_uri = redis_uri or api_settings.redis_uri
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[aioredis.Redis] = None
        self.is_available = False
        self._last_reconnect_attempt = 0.0
        
        # Initial attempt
        self._init_clients()

    def _init_clients(self) -> bool:
        """Attempts to initialize standard and async Redis clients."""
        try:
            self._sync_client = redis.Redis.from_url(
                self.redis_uri,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            self._sync_client.ping()
            self.is_available = True
            logger.info("✓ Redis cache manager successfully connected.")
            return True
        except Exception as e:
            logger.warning(
                f"Redis cache connection failed: {e}. "
                "Operating in fallback (fail-open) mode."
            )
            self.is_available = False
            self._sync_client = None
            return False

    def _check_reconnect(self):
        """Attempts to reconnect if the client is currently marked offline (rate-limited to every 10 seconds).
        Skipped entirely in test mode to avoid blocking reconnect timeouts.
        """
        if not self.is_available:
            # Never retry in test mode — avoids 2-second blocking socket timeouts
            if api_settings.env == "test":
                return
            now = time.time()
            if now - self._last_reconnect_attempt > 10.0:
                self._last_reconnect_attempt = now
                logger.info("Attempting Redis reconnection...")
                self._init_clients()

    async def get_async_client(self) -> Optional[aioredis.Redis]:
        """Lazy loader for async Redis client."""
        self._check_reconnect()
        if not self.is_available:
            return None
            
        if self._async_client is None:
            try:
                self._async_client = aioredis.Redis.from_url(
                    self.redis_uri,
                    decode_responses=True,
                    socket_timeout=1.0,
                    socket_connect_timeout=1.0
                )
                await self._async_client.ping()
                self.is_available = True
            except Exception as e:
                logger.warning(f"Async Redis setup failed: {e}")
                self.is_available = False
                self._async_client = None
                
        return self._async_client

    def get(self, key: str) -> Optional[Any]:
        """Retrieves and deserializes JSON value from cache. Returns None on miss/error."""
        self._check_reconnect()
        if not self.is_available or self._sync_client is None:
            return None
        try:
            val = self._sync_client.get(key)
            if val is not None:
                return json.loads(val)
        except Exception as e:
            logger.error(f"Redis GET failed for key '{key}': {e}")
            self.is_available = False
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Serializes and saves value to cache with optional TTL."""
        self._check_reconnect()
        if not self.is_available or self._sync_client is None:
            return False
        try:
            serialized = json.dumps(value)
            if ttl:
                self._sync_client.setex(key, ttl, serialized)
            else:
                self._sync_client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis SET failed for key '{key}': {e}")
            self.is_available = False
            return False

    def delete(self, key: str) -> bool:
        """Removes key from cache."""
        self._check_reconnect()
        if not self.is_available or self._sync_client is None:
            return False
        try:
            self._sync_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE failed for key '{key}': {e}")
            self.is_available = False
            return False

    def clear_all(self) -> bool:
        """Wipes the active database."""
        self._check_reconnect()
        if not self.is_available or self._sync_client is None:
            return False
        try:
            self._sync_client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis FLUSHDB failed: {e}")
            self.is_available = False
            return False

    # Async Implementations
    async def get_async(self, key: str) -> Optional[Any]:
        """Async version of GET."""
        client = await self.get_async_client()
        if client is None:
            return None
        try:
            val = await client.get(key)
            if val is not None:
                return json.loads(val)
        except Exception as e:
            logger.error(f"Redis async GET failed for key '{key}': {e}")
            self.is_available = False
        return None

    async def set_async(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Async version of SET."""
        client = await self.get_async_client()
        if client is None:
            return False
        try:
            serialized = json.dumps(value)
            if ttl:
                await client.setex(key, ttl, serialized)
            else:
                await client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis async SET failed for key '{key}': {e}")
            self.is_available = False
            return False

    async def delete_async(self, key: str) -> bool:
        """Async version of DELETE."""
        client = await self.get_async_client()
        if client is None:
            return False
        try:
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis async DELETE failed for key '{key}': {e}")
            self.is_available = False
            return False

    async def clear_all_async(self) -> bool:
        """Async version of FLUSHDB."""
        client = await self.get_async_client()
        if client is None:
            return False
        try:
            await client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis async FLUSHDB failed: {e}")
            self.is_available = False
            return False


# Global singleton instance
cache_manager = CacheManager()
