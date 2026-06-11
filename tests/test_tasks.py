# c:\Mood_Market\tests\test_tasks.py
import os
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# Add project root directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import Celery app and tasks
from celery_app import app
from celery.tasks.ingestion_tasks import (
    fetch_price_data_task,
    fetch_reddit_posts_task,
    fetch_news_articles_task,
    fetch_google_trends_task
)
from celery.tasks.analysis_tasks import (
    run_sentiment_analysis,
    run_anomaly_detection_task,
    calculate_technical_indicators_task
)
from celery.tasks.prediction_tasks import (
    run_price_forecast_task,
    run_risk_assessment_task
)
from celery.tasks.maintenance_tasks import (
    cleanup_old_data_task,
    generate_reports_task
)
from celery.tasks.monitoring_tasks import (
    health_check_task,
    alert_anomalies_task
)


class TestCeleryTasks(unittest.TestCase):
    """Verifies task executions, API mock mappings, retry policies, and callbacks."""

    @patch("celery.tasks.ingestion_tasks.PriceSourceClient")
    @patch("celery.tasks.ingestion_tasks.engine")
    @patch("celery.tasks.ingestion_tasks.run_async")
    def test_fetch_price_data_task(self, mock_run_async, mock_engine, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_price_history.return_value = [
            {
                "id": "price_AAPL_123",
                "ticker": "AAPL",
                "timestamp": datetime.utcnow().isoformat(),
                "open": 170.0,
                "high": 175.0,
                "low": 169.0,
                "close": 174.0,
                "volume": 1000.0
            }
        ]
        mock_run_async.return_value = (0.15, 0.3, 50.0)  # sentiment, reddit_hype, google_trends
        
        # Execute task synchronously
        res = fetch_price_data_task.apply()
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.result["status"], "success")
        self.assertTrue(res.result["price_candles_processed"] >= 1)

    @patch("celery.tasks.ingestion_tasks.RedditSourceClient")
    @patch("celery.tasks.ingestion_tasks.run_async")
    def test_fetch_reddit_posts_task(self, mock_run_async, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_posts.return_value = [
            {
                "id": "reddit_post_1",
                "title": "Bullish news on AAPL",
                "text": "Apple is doing amazing things",
                "subreddit": "stocks",
                "score": 100,
                "created_utc": datetime.utcnow().timestamp(),
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        res = fetch_reddit_posts_task.apply()
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.result["status"], "success")
        self.assertTrue(res.result["new_posts_processed"] >= 1)

    @patch("celery.tasks.analysis_tasks.AnomalyDetector")
    @patch("celery.tasks.analysis_tasks.run_async")
    def test_run_anomaly_detection_task(self, mock_run_async, mock_detector_class):
        mock_run_async.return_value = (
            [10.0]*30, [10.0]*30, [10.0]*30, 10.0, 10.0, 10.0
        )
        mock_detector = MagicMock()
        mock_detector_class.return_value = mock_detector
        
        mock_alert = MagicMock()
        mock_alert.anomaly_detected = True
        mock_alert.confidence = 0.95
        mock_alert.alert_type = "HYPE_STORM"
        mock_detector.predict.return_value = mock_alert
        
        res = run_anomaly_detection_task.apply()
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.result["status"], "success")
        self.assertTrue(res.result["anomalies_detected"] >= 1)

    @patch("celery.tasks.prediction_tasks.get_inference_engine")
    @patch("celery.tasks.prediction_tasks.run_async")
    @patch("cache.cache_manager.delete")
    def test_run_price_forecast_task(self, mock_cache_delete, mock_run_async, mock_get_engine):
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_engine.predict_single.return_value = {
            "prediction": 0.75,
            "upper_bound": 0.80,
            "lower_bound": 0.70
        }
        
        res = run_price_forecast_task.apply()
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.result["status"], "success")
        self.assertTrue(res.result["forecasts_generated"] >= 1)
        mock_cache_delete.assert_called()

    @patch("celery.tasks.monitoring_tasks.run_async")
    @patch("cache.cache_manager.is_available", True)
    def test_health_check_task(self, mock_run_async):
        mock_run_async.return_value = True  # DB is OK
        
        with patch("cache.cache_manager._sync_client") as mock_redis_sync:
            mock_redis_sync.ping.return_value = True
            
            res = health_check_task.apply()
            self.assertEqual(res.status, "SUCCESS")
            self.assertEqual(res.result["status"], "HEALTHY")
            self.assertTrue(res.result["db_connected"])
            self.assertTrue(res.result["redis_connected"])

    @patch("celery.tasks.ingestion_tasks.PriceSourceClient")
    def test_task_retry_logic(self, mock_client_class):
        mock_client_class.side_effect = Exception("API rate limit error")
        
        # Test task retries and logs exception backoff
        # Using self.retry mechanism in Celery requires binding, so we check if retry raises retry exception
        # We can call the task directly and mock the task's retry method
        task = fetch_price_data_task
        task.retry = MagicMock(side_effect=Exception("Retrying task"))
        
        with self.assertRaises(Exception) as context:
            task()
            
        self.assertIn("Retrying task", str(context.exception))
        task.retry.assert_called()


if __name__ == "__main__":
    unittest.main()
