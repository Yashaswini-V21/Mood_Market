import logging
import redis
from typing import Set

logger = logging.getLogger("processors.deduplicator")


class Deduplicator:
    """Deduplicates items (posts/articles/candles) using a cache."""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._memory_set: Set[str] = set()

    def is_duplicate(self, item_id: str, expiry_seconds: int = 86400) -> bool:
        """
        Checks if an item is a duplicate.
        If not duplicate, registers it in the cache/set.
        """
        cache_key = f"dedup:{item_id}"
        
        # 1. Try Redis cache
        if self.redis is not None:
            try:
                # setnx returns 1 if key was set, 0 if it already existed
                # Since we are using redis.asyncio or redis, we check synchronous/asynchronous.
                # In processors, we might receive either sync or async redis client.
                # Let's support both sync and async redis check.
                # First check if the method is coroutine
                import inspect
                if inspect.iscoroutinefunction(self.redis.set):
                    # We will handle it outside or await it? 
                    # Usually, processors can be synchronous or asynchronous.
                    # Let's make this method check if redis client is async, but wait,
                    # Celery tasks are usually synchronous in Python.
                    # Let's support synchronous redis operations first, and fall back to local check if it fails.
                    pass
            except Exception as e:
                logger.warning(f"Redis deduplication error: {e}")

        # Let's implement robust sync and async checks.
        # To keep processors generic, let's support sync Redis and memory fallback.
        # If the redis client is async, we can detect it. But wait, in Celery, we can pass a sync Redis client.
        if self.redis is not None:
            try:
                # Let's do a simple check. If the redis client has a get/set method, try running it.
                # If the method is async, it returns a coroutine. We don't want to block Celery worker threads.
                # Pika/Celery workers run synchronous code. Let's write a sync check.
                import inspect
                is_async = False
                try:
                    if hasattr(self.redis, "connection_pool") and "asyncio" in str(type(self.redis)):
                        is_async = True
                except Exception:
                    pass
                
                if not is_async:
                    # Sync Redis client
                    is_new = self.redis.set(cache_key, "1", ex=expiry_seconds, nx=True)
                    return not is_new
                else:
                    # Async Redis - we can't easily await inside sync method, so log and use memory fallback
                    # Let's use memory fallback for simplicity when async redis is passed, 
                    # or write a separate async_is_duplicate if needed.
                    pass
            except Exception as e:
                logger.warning(f"Sync Redis call failed: {e}. Falling back to memory set.")
                
        # 2. In-memory fallback
        if item_id in self._memory_set:
            return True
        
        self._memory_set.add(item_id)
        # Limit memory set size to prevent memory leaks
        if len(self._memory_set) > 100000:
            self._memory_set.clear()
            
        return False
        
    async def is_duplicate_async(self, redis_async_client, item_id: str, expiry_seconds: int = 86400) -> bool:
        """Asynchronous version of duplicate check, suitable for FastAPI routes."""
        cache_key = f"dedup:{item_id}"
        try:
            is_new = await redis_async_client.set(cache_key, "1", ex=expiry_seconds, nx=True)
            return not is_new
        except Exception as e:
            logger.warning(f"Async Redis deduplication error: {e}. Falling back to memory.")
            
        if item_id in self._memory_set:
            return True
        self._memory_set.add(item_id)
        return False

# clean architecture alignment
