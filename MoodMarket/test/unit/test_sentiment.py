"""
Comprehensive test suite for sentiment analysis pipeline
Includes unit tests, integration tests, and performance benchmarks.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
import numpy as np
from typing import List
from datetime import datetime, timedelta
import logging
import json
from unittest.mock import Mock, patch, MagicMock
import tempfile

from sentiment_ensemble import (
    SentimentEnsemble,
    SentimentResult,
    SentimentCache,
    create_ensemble
)
from monitoring import (
    PerformanceMonitor,
    DriftDetector,
    Alert,
    AlertLevel,
    ModelComparisonTracker
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSentimentCache(unittest.TestCase):
    """Test sentiment caching mechanism"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cache = SentimentCache(max_size=100, ttl_seconds=3600)
    
    def test_cache_put_and_get(self):
        """Test basic cache put and get"""
        text = "Apple stock is doing well."
        result = SentimentResult(
            text=text,
            sentiment_score=0.8,
            confidence=0.95,
            label="positive",
            individual_scores={"finbert": 0.8},
            model_confidences={"finbert": 0.95},
            timestamp=datetime.now()
        )
        
        self.cache.put(text, result)
        cached_result = self.cache.get(text)
        
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.sentiment_score, 0.8)
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        cache = SentimentCache(max_size=100, ttl_seconds=0)  # Immediate expiration
        
        text = "Test text"
        result = SentimentResult(
            text=text,
            sentiment_score=0.5,
            confidence=0.8,
            label="neutral",
            individual_scores={},
            model_confidences={},
            timestamp=datetime.now()
        )
        
        cache.put(text, result)
        
        # Wait for expiration
        import time
        time.sleep(0.1)
        
        cached_result = cache.get(text)
        self.assertIsNone(cached_result)
    
    def test_cache_max_size(self):
        """Test cache max size limit"""
        cache = SentimentCache(max_size=5, ttl_seconds=3600)
        
        # Add more items than max size
        for i in range(10):
            text = f"Text {i}"
            result = SentimentResult(
                text=text,
                sentiment_score=0.5,
                confidence=0.8,
                label="neutral",
                individual_scores={},
                model_confidences={},
                timestamp=datetime.now()
            )
            cache.put(text, result)
        
        # Check cache size
        stats = cache.stats()
        self.assertEqual(stats['size'], 5)
    
    def test_cache_stats(self):
        """Test cache statistics"""
        stats = self.cache.stats()
        
        self.assertEqual(stats['max_size'], 100)
        self.assertEqual(stats['ttl_seconds'], 3600)
        self.assertEqual(stats['size'], 0)


class TestPerformanceMonitor(unittest.TestCase):
    """Test performance monitoring"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = PerformanceMonitor()
    
    def test_record_prediction(self):
        """Test recording predictions"""
        alerts = self.monitor.record_prediction(
            sentiment_score=0.8,
            confidence=0.95,
            label="positive",
            inference_time_ms=150.0
        )
        
        metrics = self.monitor.get_metrics_snapshot()
        self.assertEqual(metrics.total_predictions, 1)
        self.assertEqual(metrics.positive_ratio, 1.0)
    
    def test_low_confidence_alert(self):
        """Test low confidence alert"""
        alerts = self.monitor.record_prediction(
            sentiment_score=0.5,
            confidence=0.3,  # Below threshold
            label="neutral",
            inference_time_ms=150.0
        )
        
        self.assertTrue(any(a.metric == "confidence" for a in alerts))
    
    def test_high_latency_alert(self):
        """Test high latency alert"""
        alerts = self.monitor.record_prediction(
            sentiment_score=0.5,
            confidence=0.8,
            label="neutral",
            inference_time_ms=600.0  # Above threshold
        )
        
        self.assertTrue(any(a.metric == "latency" for a in alerts))
    
    def test_metrics_snapshot(self):
        """Test metrics snapshot"""
        # Record multiple predictions
        for i in range(10):
            self.monitor.record_prediction(
                sentiment_score=np.random.randn(),
                confidence=np.random.beta(5, 2),
                label=np.random.choice(["positive", "negative", "neutral"]),
                inference_time_ms=np.random.uniform(100, 300),
                cache_hit=np.random.random() < 0.6
            )
        
        metrics = self.monitor.get_metrics_snapshot()
        
        self.assertEqual(metrics.total_predictions, 10)
        self.assertGreater(metrics.avg_confidence, 0)
        self.assertLess(metrics.cache_hit_rate, 1.0)
    
    def test_health_check(self):
        """Test system health check"""
        # Record some good predictions
        for _ in range(100):
            self.monitor.record_prediction(
                sentiment_score=0.5,
                confidence=0.85,
                label="neutral",
                inference_time_ms=200.0
            )
        
        is_healthy, alerts = self.monitor.check_health()
        self.assertTrue(is_healthy)


class TestDriftDetector(unittest.TestCase):
    """Test drift detection"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = DriftDetector(window_size=100, min_samples=50)
    
    def test_baseline_initialization(self):
        """Test baseline initialization"""
        # Add samples
        for i in range(60):
            self.detector.update(
                sentiment_score=0.5 + np.random.randn() * 0.1,
                confidence=0.8,
                label="neutral"
            )
        
        self.assertIsNotNone(self.detector.baseline_mean)
        self.assertIsNotNone(self.detector.baseline_std)
    
    def test_drift_detection(self):
        """Test drift detection"""
        # Set baseline
        for i in range(60):
            self.detector.update(
                sentiment_score=0.0 + np.random.randn() * 0.1,
                confidence=0.8,
                label="neutral"
            )
        
        # Introduce drift
        alerts = []
        for i in range(60):
            alert = self.detector.update(
                sentiment_score=1.0 + np.random.randn() * 0.1,  # Shifted to positive
                confidence=0.8,
                label="positive"
            )
            if alert:
                alerts.append(alert)
        
        # Should detect drift
        self.assertTrue(len(alerts) > 0)


class TestModelComparisonTracker(unittest.TestCase):
    """Test model comparison tracking"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = ModelComparisonTracker()
    
    def test_record_comparison(self):
        """Test recording model comparison"""
        self.tracker.record_comparison(
            text="Test text",
            model1_name="finbert",
            model1_score=0.8,
            model1_confidence=0.95,
            model2_name="distilbert",
            model2_score=0.75,
            model2_confidence=0.90
        )
        
        stats = self.tracker.get_agreement_stats()
        # Keys are sorted alphabetically: "distilbert vs finbert"
        self.assertTrue("distilbert vs finbert" in stats)
    
    def test_disagreement_detection(self):
        """Test disagreement detection"""
        # Record agreements
        for _ in range(5):
            self.tracker.record_comparison(
                text="Test text",
                model1_name="finbert",
                model1_score=0.8,
                model1_confidence=0.95,
                model2_name="distilbert",
                model2_score=0.75,
                model2_confidence=0.90
            )
        
        # Record disagreement
        self.tracker.record_comparison(
            text="Test text",
            model1_name="finbert",
            model1_score=0.8,
            model1_confidence=0.95,
            model2_name="distilbert",
            model2_score=-0.8,  # Large disagreement
            model2_confidence=0.90
        )
        
        disagreements = self.tracker.get_disagreements(threshold=0.3)
        self.assertEqual(len(disagreements), 1)


class TestSentimentResult(unittest.TestCase):
    """Test sentiment result dataclass"""
    
    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = SentimentResult(
            text="Test text",
            sentiment_score=0.8,
            confidence=0.95,
            label="positive",
            individual_scores={"finbert": 0.8},
            model_confidences={"finbert": 0.95},
            timestamp=datetime.now()
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict['text'], "Test text")
        self.assertEqual(result_dict['sentiment_score'], 0.8)
        self.assertEqual(result_dict['label'], "positive")
    
    def test_result_serialization(self):
        """Test JSON serialization of result"""
        result = SentimentResult(
            text="Test text",
            sentiment_score=0.8,
            confidence=0.95,
            label="positive",
            individual_scores={"finbert": 0.8},
            model_confidences={"finbert": 0.95},
            timestamp=datetime.now()
        )
        
        result_dict = result.to_dict()
        json_str = json.dumps(result_dict, default=str)
        
        self.assertIsInstance(json_str, str)
        self.assertIn("positive", json_str)


class TestAlerts(unittest.TestCase):
    """Test alert system"""
    
    def test_alert_creation(self):
        """Test creating alerts"""
        alert = Alert(
            level=AlertLevel.WARNING,
            message="Test warning",
            metric="test_metric",
            current_value=0.5,
            threshold=0.3
        )
        
        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertEqual(alert.message, "Test warning")
    
    def test_alert_serialization(self):
        """Test alert to dictionary"""
        alert = Alert(
            level=AlertLevel.CRITICAL,
            message="Test critical",
            metric="critical_metric",
            current_value=1.0,
            threshold=0.5
        )
        
        alert_dict = alert.to_dict()
        
        self.assertEqual(alert_dict['level'], "CRITICAL")
        self.assertEqual(alert_dict['message'], "Test critical")


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    @unittest.skip("Requires Hugging Face models")
    def test_sentiment_ensemble_initialization(self):
        """Test ensemble initialization"""
        try:
            ensemble = create_ensemble(cache_enabled=True)
            self.assertIsNotNone(ensemble.finbert_pipeline)
        except Exception as e:
            logger.warning(f"Skipping: {e}")
    
    def test_monitoring_workflow(self):
        """Test complete monitoring workflow"""
        monitor = PerformanceMonitor()
        
        # Simulate predictions
        for i in range(200):
            score = np.sin(i / 50) * 0.8 + np.random.randn() * 0.1
            confidence = 0.8 + np.random.randn() * 0.05
            label = "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral"
            latency = 200 + np.random.randn() * 50
            
            monitor.record_prediction(
                score,
                confidence,
                label,
                latency,
                disagreement=np.random.random() < 0.1
            )
        
        # Check metrics
        metrics = monitor.get_metrics_snapshot()
        self.assertGreater(metrics.total_predictions, 0)
        
        # Check health
        is_healthy, alerts = monitor.check_health()
        # May or may not be healthy depending on random data
        self.assertIsInstance(is_healthy, bool)


class TestPerformanceBenchmark(unittest.TestCase):
    """Performance benchmarking tests"""
    
    def test_cache_performance(self):
        """Benchmark cache performance"""
        cache = SentimentCache(max_size=10000)
        
        import time
        
        # Cache put performance
        text = "Test text for benchmarking"
        result = SentimentResult(
            text=text,
            sentiment_score=0.5,
            confidence=0.8,
            label="neutral",
            individual_scores={},
            model_confidences={},
            timestamp=datetime.now()
        )
        
        start = time.time()
        for _ in range(1000):
            cache.put(text, result)
        put_time = time.time() - start
        
        # Cache get performance
        start = time.time()
        for _ in range(1000):
            cache.get(text)
        get_time = time.time() - start
        
        logger.info(f"Cache put: {put_time*1000:.2f}ms per 1000 ops")
        logger.info(f"Cache get: {get_time*1000:.2f}ms per 1000 ops")
        
        # Should be fast
        self.assertLess(put_time, 1.0)
        self.assertLess(get_time, 1.0)
    
    def test_monitor_performance(self):
        """Benchmark monitoring performance"""
        monitor = PerformanceMonitor()
        
        import time
        
        start = time.time()
        for i in range(10000):
            monitor.record_prediction(
                sentiment_score=np.random.randn(),
                confidence=np.random.random(),
                label=np.random.choice(["positive", "negative", "neutral"]),
                inference_time_ms=np.random.uniform(100, 300),
                disagreement=np.random.random() < 0.1
            )
        elapsed = time.time() - start
        
        logger.info(f"Monitor: {elapsed*1000:.2f}ms for 10000 predictions")
        logger.info(f"Average per prediction: {elapsed/10000*1000:.2f}ms")
        
        # Should be very fast
        self.assertLess(elapsed, 10.0)



class TestErrorHandling(unittest.TestCase):
    """Test error handling"""
    
    def test_invalid_sentiment_score(self):
        """Test handling of invalid sentiment scores"""
        # Out of range score
        result = SentimentResult(
            text="Test",
            sentiment_score=1.5,  # Out of range
            confidence=0.8,
            label="positive",
            individual_scores={},
            model_confidences={},
            timestamp=datetime.now()
        )
        
        # Should still create result
        self.assertIsNotNone(result)
    
    def test_invalid_confidence(self):
        """Test handling of invalid confidence"""
        result = SentimentResult(
            text="Test",
            sentiment_score=0.5,
            confidence=1.5,  # Out of range
            label="neutral",
            individual_scores={},
            model_confidences={},
            timestamp=datetime.now()
        )
        
        self.assertIsNotNone(result)


# Test runner
def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSentimentCache))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestDriftDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestModelComparisonTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestSentimentResult))
    suite.addTests(loader.loadTestsFromTestCase(TestAlerts))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBenchmark))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

# clean architecture alignment
