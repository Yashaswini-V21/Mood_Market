# c:\Mood_Market\cache_stats.py
import logging
from typing import Dict, Any
from cache import cache_manager

logger = logging.getLogger("cache.logger")


class CacheStatsTracker:
    """
    Atomic stats counter for tracking hits and misses in Redis
    with fallback in-memory counters.
    """
    def __init__(self, stats_key: str = "cache_stats"):
        self.stats_key = stats_key
        self._local_hits = 0
        self._local_misses = 0

    def record_hit(self):
        """Atomically increments the hits count in Redis (or locally if offline)."""
        if cache_manager.is_available and cache_manager._sync_client is not None:
            try:
                cache_manager._sync_client.hincrby(self.stats_key, "hits", 1)
                self._check_hit_rate()
                return
            except Exception as e:
                logger.debug(f"Failed to increment Redis hits: {e}")
        self._local_hits += 1

    def record_miss(self):
        """Atomically increments the misses count in Redis (or locally if offline)."""
        if cache_manager.is_available and cache_manager._sync_client is not None:
            try:
                cache_manager._sync_client.hincrby(self.stats_key, "misses", 1)
                self._check_hit_rate()
                return
            except Exception as e:
                logger.debug(f"Failed to increment Redis misses: {e}")
        self._local_misses += 1

    def get_stats(self) -> Dict[str, Any]:
        """Calculates cache performance metrics and current Redis memory footprint."""
        hits = 0
        misses = 0
        if cache_manager.is_available and cache_manager._sync_client is not None:
            try:
                data = cache_manager._sync_client.hgetall(self.stats_key)
                hits = int(data.get("hits", 0))
                misses = int(data.get("misses", 0))
            except Exception as e:
                logger.debug(f"Failed to get Redis stats: {e}")
                hits = self._local_hits
                misses = self._local_misses
        else:
            hits = self._local_hits
            misses = self._local_misses

        total = hits + misses
        hit_rate = float(hits) / total if total > 0 else 1.0

        memory_used = 0
        if cache_manager.is_available and cache_manager._sync_client is not None:
            try:
                mem_info = cache_manager._sync_client.info(section="memory")
                memory_used = mem_info.get("used_memory", 0)
            except Exception:
                pass

        return {
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hit_rate, 4),
            "memory_used_bytes": memory_used,
            "is_available": cache_manager.is_available
        }

    def _check_hit_rate(self):
        """Emits an alert if the cache hit rate drops below 70% after 20 requests."""
        try:
            stats = self.get_stats()
            total = stats["hits"] + stats["misses"]
            if total >= 20 and stats["hit_rate"] < 0.70:
                logger.warning(
                    f"⚠️ Alert: Redis Cache Hit Rate is below threshold! "
                    f"Current hit rate: {stats['hit_rate']:.2%} "
                    f"(Hits: {stats['hits']}, Misses: {stats['misses']})"
                )
        except Exception as e:
            logger.debug(f"Failed to verify cache stats thresholds: {e}")


# Singleton tracker
cache_stats_tracker = CacheStatsTracker()

# clean architecture alignment
