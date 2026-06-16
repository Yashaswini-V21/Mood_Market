# c:\Mood_Market\celery\tasks\monitoring_tasks.py
import logging
import asyncio
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy import text

from dependencies import engine
from cache import cache_manager

logger = logging.getLogger("celery.tasks.monitoring")


def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(coro))
                return future.result()
        else:
            return loop.run_until_complete(coro)


@shared_task(
    bind=True,
    name="celery.tasks.monitoring_tasks.health_check_task",
    max_retries=3,
    time_limit=300
)
def health_check_task(self):
    """Pings database pools and Redis cache to verify system state."""
    logger.info("Executing periodic health check task...")
    try:
        db_ok = False
        redis_ok = False
        
        # Test Database
        async def test_db():
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return True
        try:
            db_ok = run_async(test_db())
        except Exception as e:
            logger.error(f"Health check database failure: {e}")
            db_ok = False
            
        # Test Redis
        if cache_manager.is_available and cache_manager._sync_client:
            try:
                cache_manager._sync_client.ping()
                redis_ok = True
            except Exception as e:
                logger.error(f"Health check Redis failure: {e}")
                redis_ok = False
        else:
            redis_ok = False
            
        status = "HEALTHY" if (db_ok and redis_ok) else "DEGRADED"
        logger.info(f"System health check: Status={status} | DB={db_ok} | Redis={redis_ok}")
        return {
            "status": status,
            "db_connected": db_ok,
            "redis_connected": redis_ok,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in health_check_task. Retrying: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(
    bind=True,
    name="celery.tasks.monitoring_tasks.alert_anomalies_task",
    max_retries=3,
    time_limit=300
)
def alert_anomalies_task(self):
    """Monitors active HIGH risk anomalies and dispatches alerts."""
    logger.info("Checking for unalerted high-risk anomaly records...")
    try:
        async def fetch_anomalies():
            cutoff = datetime.utcnow() - timedelta(minutes=15)
            async with engine.connect() as conn:
                query = text(
                    "SELECT ticker, alert_level, confidence FROM anomaly_records "
                    "WHERE timestamp >= :cutoff AND alert_level = 'HIGH' AND anomaly_detected = 1"
                )
                try:
                    res = await conn.execute(query, {"cutoff": cutoff})
                    return res.fetchall()
                except Exception:
                    return []
                    
        rows = run_async(fetch_anomalies())
        
        alerts_sent = 0
        for row in rows:
            ticker, level, conf = row
            # Mock sending alert (e.g. Email/Slack/Telegram)
            logger.warning(
                f"🚨 TELEMETRY ALERT: High-risk anomaly detected on ticker {ticker}! "
                f"Classification confidence: {conf:.2%}"
            )
            alerts_sent += 1
            
        return {"status": "success", "alerts_dispatched": alerts_sent}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in alert_anomalies_task. Retrying: {exc}")
        raise self.retry(exc=exc, countdown=countdown)

# clean architecture alignment
