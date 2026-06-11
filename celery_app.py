# c:\Mood_Market\celery_app.py
import os
import logging
from celery import Celery
from config import api_settings

logger = logging.getLogger("celery.logger")

# Initialize Celery app
app = Celery(
    "moodmarket",
    broker=api_settings.redis_uri,
    backend=api_settings.redis_uri,
    include=[
        "celery.tasks.ingestion_tasks",
        "celery.tasks.analysis_tasks",
        "celery.tasks.prediction_tasks",
        "celery.tasks.maintenance_tasks",
        "celery.tasks.monitoring_tasks"
    ]
)

# Celery Configuration mapping to priority queues
app.conf.update(
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Priority Queue Routing Definitions
    task_routes={
        # Low Priority: Scrapers and cleanups
        "celery.tasks.ingestion_tasks.*": {"queue": "low"},
        "celery.tasks.maintenance_tasks.*": {"queue": "low"},
        
        # Default Priority: Intermediate analysis tasks
        "celery.tasks.analysis_tasks.run_sentiment_analysis": {"queue": "default"},
        "celery.tasks.analysis_tasks.calculate_technical_indicators_task": {"queue": "default"},
        
        # Priority Queue: Core forecasts and high-priority anomalies
        "celery.tasks.analysis_tasks.run_anomaly_detection_task": {"queue": "priority"},
        "celery.tasks.prediction_tasks.run_price_forecast_task": {"queue": "priority"},
        "celery.tasks.prediction_tasks.run_risk_assessment_task": {"queue": "priority"},
        
        # Critical Queue: Real-time health metrics and critical dispatcher alerts
        "celery.tasks.monitoring_tasks.health_check_task": {"queue": "critical"},
        "celery.tasks.monitoring_tasks.alert_anomalies_task": {"queue": "critical"},
    }
)

# Load periodic schedules dynamically to bypass package namespace cache collisions
import importlib.util
spec = importlib.util.spec_from_file_location(
    "local_schedules",
    os.path.join(os.path.dirname(__file__), "celery", "schedules.py")
)
local_schedules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_schedules)
setup_periodic_tasks = local_schedules.setup_periodic_tasks

setup_periodic_tasks(app)

# Import callbacks to activate signal listeners
import celery.callbacks

if __name__ == "__main__":
    app.start()
