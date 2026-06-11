# c:\Mood_Market\decorators.py
from functools import wraps
from typing import Callable, Any
from cache import cache_manager


def cached(ttl: int, prefix: str):
    """
    Decorator to cache the result of an async function.
    Constructs a cache key combining the prefix and primitive argument values.
    """
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Fallback directly to underlying function if cache is down
            if not cache_manager.is_available:
                return await func(*args, **kwargs)

            # Build a deterministic cache key
            key_parts = [prefix]
            for arg in args:
                # Avoid caching self/cls or complex objects directly
                if type(arg) in (str, int, float, bool):
                    key_parts.append(str(arg))

            for k, v in sorted(kwargs.items()):
                if type(v) in (str, int, float, bool):
                    key_parts.append(f"{k}_{v}")

            cache_key = ":".join(key_parts)

            # Check cache
            cached_val = await cache_manager.get_async(cache_key)
            if cached_val is not None:
                # Record hit atomically in cache stats
                from cache_stats import cache_stats_tracker
                cache_stats_tracker.record_hit()
                return cached_val

            # Record miss
            from cache_stats import cache_stats_tracker
            cache_stats_tracker.record_miss()

            # Execute actual function
            result = await func(*args, **kwargs)

            # Save result to cache
            if result is not None:
                await cache_manager.set_async(cache_key, result, ttl=ttl)

            return result
        return wrapper
    return decorator
