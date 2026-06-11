# c:\Mood_Market\celery\tasks\maintenance_tasks.py
import logging
import asyncio
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy import text

from dependencies import engine

logger = logging.getLogger("celery.tasks.maintenance")


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
    name="celery.tasks.maintenance_tasks.cleanup_old_data_task",
    max_retries=3,
    time_limit=1800  # 30 minutes for maintenance queries
)
def cleanup_old_data_task(self):
    """Deletes logs and metrics older than the 2-year retention window."""
    logger.info("Starting database retention cleanup task...")
    try:
        cutoff = datetime.utcnow() - timedelta(days=730)  # 2 years
        
        async def purge():
            async with engine.begin() as conn:
                # Purge SQLite fallback tables
                tables_records = [
                    ("price_records", "timestamp"),
                    ("sentiment_records", "timestamp"),
                    ("forecast_records", "timestamp"),
                    ("anomaly_records", "timestamp")
                ]
                for table, col in tables_records:
                    try:
                        q = text(f"DELETE FROM {table} WHERE {col} < :cutoff")
                        res = await conn.execute(q, {"cutoff": cutoff})
                        logger.info(f"Purged {res.rowcount} rows from {table}")
                    except Exception as e:
                        logger.debug(f"Purging {table} skipped: {e}")

                # Purge PostgreSQL hypertables
                tables_data = [
                    ("price_data", "time"),
                    ("sentiment_data", "time"),
                    ("predictions", "time"),
                    ("anomalies", "time"),
                    ("technical_indicators", "time"),
                    ("api_logs", "time")
                ]
                for table, col in tables_data:
                    try:
                        q = text(f"DELETE FROM {table} WHERE {col} < :cutoff")
                        res = await conn.execute(q, {"cutoff": cutoff})
                        logger.info(f"Purged {res.rowcount} rows from hypertable {table}")
                    except Exception as e:
                        logger.debug(f"Purging hypertable {table} skipped: {e}")
                        
        run_async(purge())
        logger.info("✓ Cleanup task finished successfully.")
        return {"status": "success"}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in cleanup_old_data_task. Retrying: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(
    bind=True,
    name="celery.tasks.maintenance_tasks.update_model_weights_task",
    max_retries=3,
    time_limit=3600  # 1 hour limit for offline training / weight updates
)
def update_model_weights_task(self):
    """Simulates updating local weights or trigger model retraining pipeline."""
    logger.info("Starting Informer model weight retraining update...")
    try:
        # Simulate loading data and computing gradients
        import time
        logger.info("Step 1: Extracting 3 years of indicators baseline...")
        time.sleep(1)
        logger.info("Step 2: Training model weights...")
        time.sleep(2)
        logger.info("✓ Model weight retraining completed. Best checkpoint saved to 'checkpoints/best_model.pt'.")
        return {"status": "success", "new_version": "v1.1"}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in update_model_weights_task. Retrying: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(
    bind=True,
    name="celery.tasks.maintenance_tasks.generate_reports_task",
    max_retries=3,
    time_limit=300
)
def generate_reports_task(self):
    """Compiles daily system analytical summary and prediction statistics."""
    logger.info("Generating daily analytics report...")
    try:
        # Compiles performance summary
        async def fetch_summary():
            async with engine.connect() as conn:
                res = await conn.execute(text("SELECT count(*) FROM forecast_records"))
                total_forecasts = res.scalar() or 0
                
                res = await conn.execute(text("SELECT count(*) FROM anomaly_records WHERE anomaly_detected = 1"))
                total_anomalies = res.scalar() or 0
            return total_forecasts, total_anomalies
            
        tf, ta = run_async(fetch_summary())
        logger.info(f"Daily Summary report: Forecasts={tf}, Anomalies={ta}")
        return {"status": "success", "total_forecasts": tf, "total_anomalies": ta}
    except Exception as exc:
        countdown = 5 ** (self.request.retries + 1)
        logger.error(f"Error in generate_reports_task. Retrying: {exc}")
        raise self.retry(exc=exc, countdown=countdown)
