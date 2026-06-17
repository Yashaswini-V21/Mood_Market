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


def validate_ticker(func: Callable[..., Any]):
    """
    Decorator to validate that the 'ticker' parameter is a valid format.
    Must be a string of 1 to 5 alphabetical characters.
    """
    import re
    from fastapi import HTTPException
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        ticker = kwargs.get("ticker")
        if ticker is not None:
            if not isinstance(ticker, str) or not re.match(r"^[A-Za-z]{1,5}$", ticker):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid ticker symbol: '{ticker}'. Must be 1 to 5 alphabetical characters."
                )
        return await func(*args, **kwargs)
    return wrapper
