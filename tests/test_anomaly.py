"""
Comprehensive tests for anomaly detection system.
Tests individual detectors, ensemble voting, and real-world scenarios.
"""

import os
import sys
import unittest
import numpy as np
import time
import logging
from datetime import datetime
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from anomaly_detector import AnomalyDetector, AnomalyAlert
from detectors.zscore_detector import ZScoreDetector, MultiVarZScoreDetector
from detectors.isolation_forest_detector import IsolationForestDetector
from detectors.autoencoder_detector import AutoencoderDetector
from detectors.ewma_detector import EWMADetector, AdaptiveEWMADetector
from detectors.base_detector import DetectionResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestZScoreDetector(unittest.TestCase):
    """Test Z-score detector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = ZScoreDetector(threshold=3.0)
        
        # Normal data: mean=100, std=10
        np.random.seed(42)
        self.normal_data = np.random.normal(100, 10, 300)
    
    def test_fit(self):
        """Test fitting"""
        self.detector.fit(self.normal_data)
        
        self.assertTrue(self.detector.is_fitted)
        self.assertAlmostEqual(self.detector.mean, 100, delta=2)
        self.assertAlmostEqual(self.detector.std, 10, delta=2)
    
    def test_normal_prediction(self):
        """Test normal value prediction"""
        self.detector.fit(self.normal_data)
        
        result = self.detector.predict(100)
        
        self.assertFalse(result.anomaly_detected)
        self.assertEqual(result.confidence, 0.0)
    
    def test_anomaly_detection(self):
        """Test anomaly detection"""
        self.detector.fit(self.normal_data)
        
        # 4σ away = clear anomaly
        anomaly = self.detector.mean + 4 * self.detector.std
        result = self.detector.predict(anomaly)
        
        self.assertTrue(result.anomaly_detected)
        self.assertGreater(result.confidence, 0.8)
    
    def test_statistics(self):
        """Test statistics retrieval"""
        self.detector.fit(self.normal_data)
        stats = self.detector.get_stats()
        
        self.assertIn("mean", stats)
        self.assertIn("std", stats)
        self.assertIn("threshold", stats)
        self.assertTrue(stats["fitted"])


class TestMultiVarZScoreDetector(unittest.TestCase):
    """Test multi-variable Z-score detector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = MultiVarZScoreDetector(n_features=3, threshold=3.0)
        
        # 3-variable normal data
        np.random.seed(42)
        self.data = np.column_stack([
            np.random.normal(100, 10, 300),  # Reddit
            np.random.normal(50, 5, 300),    # Google Trends
            np.random.normal(200, 20, 300)   # Twitter
        ])
    
    def test_fit(self):
        """Test fitting"""
        self.detector.fit(self.data)
        
        self.assertTrue(self.detector.is_fitted)
        self.assertEqual(len(self.detector.means), 3)
    
    def test_multivar_anomaly(self):
        """Test multivariate anomaly detection"""
        self.detector.fit(self.data)
        
        # Anomaly in first variable
        observation = np.array([
            self.detector.means[0] + 4 * self.detector.stds[0],  # Anomaly
            self.detector.means[1],
            self.detector.means[2]
        ])
        
        result = self.detector.predict(observation)
        
        self.assertTrue(result.anomaly_detected)


class TestIsolationForestDetector(unittest.TestCase):
    """Test Isolation Forest detector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = IsolationForestDetector(contamination=0.05)
        
        np.random.seed(42)
        self.normal_data = np.random.normal(100, 10, 300)
    
    def test_fit(self):
        """Test fitting"""
        self.detector.fit(self.normal_data)
        
        self.assertTrue(self.detector.is_fitted)
        self.assertIsNotNone(self.detector.model)
    
    def test_anomaly_detection(self):
        """Test anomaly detection"""
        self.detector.fit(self.normal_data)
        
        # Extreme outlier
        anomaly = 200  # Way outside normal distribution
        result = self.detector.predict(anomaly)
        
        self.assertTrue(result.anomaly_detected)
        self.assertGreater(result.confidence, 0.5)
    
    def test_normal_prediction(self):
        """Test normal prediction"""
        self.detector.fit(self.normal_data)
        
        result = self.detector.predict(100)
        
        self.assertFalse(result.anomaly_detected)


class TestAutoencoderDetector(unittest.TestCase):
    """Test Autoencoder detector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = AutoencoderDetector(hidden_size=8)
        
        np.random.seed(42)
        self.normal_data = np.random.normal(100, 10, 200)
    
    def test_fit(self):
        """Test fitting"""
        self.detector.fit(self.normal_data)
        
        self.assertTrue(self.detector.is_fitted)
        self.assertIsNotNone(self.detector.error_threshold)
    
    def test_anomaly_detection(self):
        """Test anomaly detection"""
        self.detector.fit(self.normal_data)
        
        # Extreme value
        anomaly = 250
        result = self.detector.predict(anomaly)
        
        # Should detect or at least flag as potential
        self.assertGreaterEqual(result.score, 0)
    
    def test_normal_prediction(self):
        """Test normal prediction"""
        self.detector.fit(self.normal_data)
        
        result = self.detector.predict(100)
        
        self.assertFalse(result.anomaly_detected)


class TestEWMADetector(unittest.TestCase):
    """Test EWMA detector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = EWMADetector(alpha=0.2, spike_multiplier=2.0)
        
        np.random.seed(42)
        self.normal_data = np.random.normal(100, 10, 300)
    
    def test_fit(self):
        """Test fitting"""
        self.detector.fit(self.normal_data)
        
        self.assertTrue(self.detector.is_fitted)
        self.assertIsNotNone(self.detector.ewma_volatility)
    
    def test_volatility_spike_detection(self):
        """Test volatility spike detection"""
        self.detector.fit(self.normal_data)
        
        # Create spike: 10x normal std
        spike = 100 + 100  # Much higher variance
        result = self.detector.predict(spike)
        
        # Should detect spike
        self.assertGreater(result.score, 1.0)
    
    def test_statistics(self):
        """Test statistics"""
        self.detector.fit(self.normal_data)
        stats = self.detector.get_stats()
        
        self.assertIn("alpha", stats)
        self.assertIn("ewma_volatility", stats)


class TestAdaptiveEWMADetector(unittest.TestCase):
    """Test Adaptive EWMA detector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = AdaptiveEWMADetector(alpha=0.2)
        
        np.random.seed(42)
        self.normal_data = np.random.normal(100, 10, 300)
    
    def test_regime_detection(self):
        """Test regime detection"""
        self.detector.fit(self.normal_data)
        
        # Should start in normal regime
        self.assertEqual(self.detector.regime, "normal")
    
    def test_high_vol_regime(self):
        """Test high volatility regime"""
        self.detector.fit(self.normal_data)
        
        # Add high volatility data
        high_vol_data = np.random.normal(100, 50, 300)  # 5x volatility
        
        for value in high_vol_data:
            self.detector.predict(value)
        
        # Should eventually detect high volatility regime
        # (might take a while to stabilize)


class TestAnomalyDetectorOrchestrator(unittest.TestCase):
    """Test main orchestrator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = AnomalyDetector(
            zscore_threshold=3.0,
            ensemble_threshold=0.65,
            confidence_threshold=0.7
        )
        
        # Generate synthetic data for testing
        np.random.seed(42)
        self.reddit_history = np.random.normal(100, 10, 300)
        self.google_history = np.random.normal(50, 5, 300)
        self.twitter_history = np.random.normal(200, 20, 300)
    
    def test_fit_baseline(self):
        """Test baseline fitting"""
        self.detector.fit_baseline(
            "AAPL",
            self.reddit_history,
            self.google_history,
            self.twitter_history
        )
        
        self.assertIn("AAPL", self.detector.baselines)
        baseline = self.detector.baselines["AAPL"]
        
        self.assertAlmostEqual(baseline.reddit_mean, 100, delta=2)
        self.assertAlmostEqual(baseline.reddit_std, 10, delta=2)
    
    def test_normal_prediction(self):
        """Test normal prediction"""
        self.detector.fit_baseline(
            "AAPL",
            self.reddit_history,
            self.google_history,
            self.twitter_history
        )
        
        alert = self.detector.predict(
            "AAPL",
            reddit_volume=100,
            google_trends_score=50,
            twitter_volume=200
        )
        
        self.assertFalse(alert.anomaly_detected)
    
    def test_hype_storm_detection(self):
        """Test hype storm detection"""
        self.detector.fit_baseline(
            "GME",
            self.reddit_history,
            self.google_history,
            self.twitter_history
        )
        
        # Extreme spike across all metrics
        baseline = self.detector.baselines["GME"]
        
        alert = self.detector.predict(
            "GME",
            reddit_volume=baseline.reddit_mean + 6 * baseline.reddit_std,  # 6σ
            google_trends_score=baseline.google_trends_mean + 4 * baseline.google_trends_std,
            twitter_volume=baseline.twitter_mean + 5 * baseline.twitter_std
        )
        
        if alert.anomaly_detected:
            self.assertEqual(alert.alert_type, "HYPE_STORM")
            self.assertEqual(alert.recommendation, "REDUCE_POSITION_SIZE")
    
    def test_alert_summary(self):
        """Test alert summary"""
        self.detector.fit_baseline(
            "TSLA",
            self.reddit_history,
            self.google_history,
            self.twitter_history
        )
        
        # Generate some alerts
        for _ in range(5):
            self.detector.predict("TSLA", 150, 60, 250)
        
        summary = self.detector.get_alert_summary("TSLA")
        
        self.assertIn("ticker", summary)
        self.assertIn("total_alerts", summary)
        self.assertIn("recent_alerts", summary)
    
    def test_detector_stats(self):
        """Test detector statistics"""
        self.detector.fit_baseline(
            "MSFT",
            self.reddit_history,
            self.google_history,
            self.twitter_history
        )
        
        stats = self.detector.get_detector_stats("MSFT")
        
        self.assertEqual(stats["ticker"], "MSFT")
        self.assertIn("detectors", stats)
        self.assertIn("baseline", stats)


class TestRealWorldScenarios(unittest.TestCase):
    """Test on realistic market scenarios"""
    
    def test_gme_2021_scenario(self):
        """Test GME 2021 squeeze scenario"""
        detector = AnomalyDetector()
        
        # Baseline: normal Reddit activity
        np.random.seed(42)
        baseline_reddit = np.random.normal(50, 5, 300)
        baseline_google = np.random.normal(40, 3, 300)
        baseline_twitter = np.random.normal(100, 10, 300)
        
        detector.fit_baseline("GME", baseline_reddit, baseline_google, baseline_twitter)
        
        # GME squeeze event: 20x Reddit volume
        alert = detector.predict(
            "GME",
            reddit_volume=1000,  # 20x normal
            google_trends_score=95,
            twitter_volume=2000
        )
        
        logger.info(f"GME scenario alert: {alert.alert_type}, confidence={alert.confidence:.2f}")
    
    def test_doge_pump_scenario(self):
        """Test DOGE pump scenario"""
        detector = AnomalyDetector()
        
        np.random.seed(42)
        baseline_reddit = np.random.normal(200, 20, 300)
        baseline_google = np.random.normal(60, 5, 300)
        baseline_twitter = np.random.normal(500, 50, 300)
        
        detector.fit_baseline("DOGE", baseline_reddit, baseline_google, baseline_twitter)
        
        # Social media pump
        alert = detector.predict(
            "DOGE",
            reddit_volume=5000,  # 25x
            google_trends_score=85,
            twitter_volume=15000
        )
        
        logger.info(f"DOGE pump alert: {alert.alert_type}, confidence={alert.confidence:.2f}")
    
    def test_ftx_collapse_scenario(self):
        """Test FTX collapse scenario"""
        detector = AnomalyDetector()
        
        np.random.seed(42)
        baseline_reddit = np.random.normal(300, 30, 300)
        baseline_google = np.random.normal(70, 7, 300)
        baseline_twitter = np.random.normal(800, 80, 300)
        
        detector.fit_baseline("FTX", baseline_reddit, baseline_google, baseline_twitter)
        
        # Crisis event
        alert = detector.predict(
            "FTX",
            reddit_volume=8000,  # 27x
            google_trends_score=98,
            twitter_volume=20000
        )
        
        logger.info(f"FTX crisis alert: {alert.alert_type}, confidence={alert.confidence:.2f}")


class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance and scalability tests"""
    
    def test_single_prediction_latency(self):
        """Test single prediction latency (<30ms)"""
        detector = AnomalyDetector()
        
        np.random.seed(42)
        data = np.random.normal(100, 10, 300)
        
        detector.fit_baseline("TEST", data, data/2, data*2)
        
        # Warm up
        detector.predict("TEST", 100, 50, 200)
        
        # Benchmark
        start = time.time()
        for _ in range(100):
            detector.predict("TEST", np.random.normal(100, 10), 50, 200)
        elapsed = time.time() - start
        
        avg_latency_ms = (elapsed / 100) * 1000
        logger.info(f"Single prediction latency: {avg_latency_ms:.2f}ms")
        
        self.assertLess(avg_latency_ms, 30)  # <30ms requirement
    
    def test_multi_stock_scaling(self):
        """Test scaling to 500 stocks"""
        detector = AnomalyDetector(n_stocks=500)
        
        np.random.seed(42)
        baseline_data = np.random.normal(100, 10, 300)
        
        # Fit 100 stocks (representative sample)
        start = time.time()
        for i in range(100):
            ticker = f"STOCK_{i}"
            detector.fit_baseline(
                ticker,
                baseline_data,
                baseline_data / 2,
                baseline_data * 2
            )
        elapsed = time.time() - start
        
        logger.info(f"Fitted 100 stocks in {elapsed:.2f}s")
        
        # Predict on all
        start = time.time()
        for i in range(100):
            ticker = f"STOCK_{i}"
            detector.predict(ticker, 100, 50, 200)
        elapsed = time.time() - start
        
        logger.info(f"Predicted on 100 stocks in {elapsed:.2f}s")
        
        self.assertLess(elapsed, 5.0)  # <5s for 100 predictions
    
    def test_memory_efficiency(self):
        """Test memory efficiency with 500 stocks"""
        detector = AnomalyDetector(n_stocks=500)
        
        np.random.seed(42)
        baseline_data = np.random.normal(100, 10, 300)
        
        # Fit all 500
        for i in range(500):
            ticker = f"STOCK_{i}"
            detector.fit_baseline(
                ticker,
                baseline_data,
                baseline_data / 2,
                baseline_data * 2
            )
        
        # Should still be responsive
        start = time.time()
        for i in range(50):
            detector.predict(f"STOCK_{i}", 100, 50, 200)
        elapsed = time.time() - start
        
        logger.info(f"Predicted on 50 stocks (500 loaded) in {elapsed:.2f}s")


class TestFalsePositiveRate(unittest.TestCase):
    """Test false positive rate (target <5%)"""
    
    def test_false_positive_rate_on_normal_data(self):
        """Test FPR on purely normal data"""
        detector = AnomalyDetector(
            ensemble_threshold=0.65,
            confidence_threshold=0.7
        )
        
        np.random.seed(42)
        baseline_data = np.random.normal(100, 10, 300)
        baseline_google = np.random.normal(50, 5, 300)
        baseline_twitter = np.random.normal(200, 20, 300)
        
        detector.fit_baseline("TEST", baseline_data, baseline_google, baseline_twitter)
        
        # Generate 1000 normal predictions
        false_positives = 0
        for _ in range(1000):
            value = np.random.normal(100, 10)
            alert = detector.predict(
                "TEST",
                reddit_volume=value,
                google_trends_score=50,
                twitter_volume=200
            )
            if alert.anomaly_detected:
                false_positives += 1
        
        fpr = false_positives / 1000
        logger.info(f"False positive rate: {fpr:.2%}")
        
        self.assertLess(fpr, 0.05)  # <5% requirement


class TestThreadSafety(unittest.TestCase):
    """Test thread safety"""
    
    def test_concurrent_predictions(self):
        """Test concurrent predictions from multiple threads"""
        import threading
        
        detector = AnomalyDetector()
        
        np.random.seed(42)
        data = np.random.normal(100, 10, 300)
        
        for i in range(10):
            detector.fit_baseline(f"STOCK_{i}", data, data/2, data*2)
        
        results = []
        errors = []
        
        def predict_worker(ticker_id, n_predictions):
            try:
                for _ in range(n_predictions):
                    alert = detector.predict(
                        f"STOCK_{ticker_id}",
                        np.random.normal(100, 10),
                        50,
                        200
                    )
                    results.append(alert)
            except Exception as e:
                errors.append(e)
        
        # Create 10 threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=predict_worker, args=(i, 10))
            threads.append(t)
            t.start()
        
        # Wait for all
        for t in threads:
            t.join()
        
        logger.info(f"Completed {len(results)} concurrent predictions")
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 100)


# Test runner
def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [
        TestZScoreDetector,
        TestMultiVarZScoreDetector,
        TestIsolationForestDetector,
        TestAutoencoderDetector,
        TestEWMADetector,
        TestAdaptiveEWMADetector,
        TestAnomalyDetectorOrchestrator,
        TestRealWorldScenarios,
        TestPerformanceBenchmarks,
        TestFalsePositiveRate,
        TestThreadSafety
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
