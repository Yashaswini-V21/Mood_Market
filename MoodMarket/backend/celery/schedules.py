# c:\Mood_Market\celery\schedules.py
from celery.schedules import crontab


def setup_periodic_tasks(app):
    """Binds task triggers to periodic intervals inside Celery Beat scheduler."""
    app.conf.beat_schedule = {
        # Ingestion Tasks
        "fetch-price-data-every-1m": {
            "task": "celery.tasks.ingestion_tasks.fetch_price_data_task",
            "schedule": crontab(minute="*"),  # every 1 minute
        },
        "fetch-news-articles-every-5m": {
            "task": "celery.tasks.ingestion_tasks.fetch_news_articles_task",
            "schedule": crontab(minute="*/5"),  # every 5 minutes
        },
        "fetch-reddit-posts-every-15m": {
            "task": "celery.tasks.ingestion_tasks.fetch_reddit_posts_task",
            "schedule": crontab(minute="*/15"),  # every 15 minutes
        },
        "fetch-google-trends-every-60m": {
            "task": "celery.tasks.ingestion_tasks.fetch_google_trends_task",
            "schedule": crontab(minute="0", hour="*"),  # every 60 minutes
        },
        
        # Analysis Tasks
        "run-anomaly-detection-every-15m": {
            "task": "celery.tasks.analysis_tasks.run_anomaly_detection_task",
            "schedule": crontab(minute="*/15"),
        },
        "calculate-technical-indicators-every-15m": {
            "task": "celery.tasks.analysis_tasks.calculate_technical_indicators_task",
            "schedule": crontab(minute="*/15"),
        },
        
        # Prediction Tasks
        "run-price-forecast-every-15m": {
            "task": "celery.tasks.prediction_tasks.run_price_forecast_task",
            "schedule": crontab(minute="*/15"),
        },
        "run-risk-assessment-every-15m": {
            "task": "celery.tasks.prediction_tasks.run_risk_assessment_task",
            "schedule": crontab(minute="*/15"),
        },
        
        # Maintenance Tasks
        "cleanup-old-data-daily-at-2am": {
            "task": "celery.tasks.maintenance_tasks.cleanup_old_data_task",
            "schedule": crontab(hour="2", minute="0"),  # Daily at 2 AM
        },
        "generate-reports-daily-at-3am": {
            "task": "celery.tasks.maintenance_tasks.generate_reports_task",
            "schedule": crontab(hour="3", minute="0"),  # Daily at 3 AM
        },
        "update-model-weights-weekly": {
            "task": "celery.tasks.maintenance_tasks.update_model_weights_task",
            "schedule": crontab(day_of_week="0", hour="0", minute="0"),  # Weekly (Sunday 12 AM)
        },
        
        # Monitoring Tasks
        "health-check-every-5m": {
            "task": "celery.tasks.monitoring_tasks.health_check_task",
            "schedule": crontab(minute="*/5"),  # every 5 minutes
        }
    }

# clean architecture alignment
