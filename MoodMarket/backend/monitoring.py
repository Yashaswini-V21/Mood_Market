"""
Monitoring and Drift Detection for Sentiment Analysis Models
Tracks model performance, detects distribution shifts, and alerts on issues.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import logging
import json
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: datetime
    total_predictions: int
    positive_ratio: float  # Ratio of positive predictions
    negative_ratio: float
    neutral_ratio: float
    avg_confidence: float
    min_confidence: float
    max_confidence: float
    model_disagreement_rate: float  # % of disagreements between models
    inference_latency_ms: float
    cache_hit_rate: float


@dataclass
class Alert:
    """System alert"""
    level: AlertLevel
    message: str
    metric: str
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "level": self.level.value,
            "message": self.message,
            "metric": self.metric,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat()
        }


class DriftDetector:
    """Detect distribution shifts in model predictions"""
    
    def __init__(
        self,
        window_size: int = 1000,
        drift_threshold: float = 0.05,
        min_samples: int = 100
    ):
        """
        Initialize drift detector
        
        Args:
            window_size: Number of samples for moving window
            drift_threshold: Threshold for detecting drift
            min_samples: Minimum samples needed for detection
        """
        self.window_size = window_size
        self.drift_threshold = drift_threshold
        self.min_samples = min_samples
        
        # Store recent predictions
        self.recent_scores = deque(maxlen=window_size)
        self.recent_confidences = deque(maxlen=window_size)
        self.recent_labels = deque(maxlen=window_size)
        
        # Baseline statistics
        self.baseline_mean = None
        self.baseline_std = None
        self.baseline_positive_ratio = None
        
        self.drift_detected = False
        self.drift_start_time = None
    
    def update(
        self,
        sentiment_score: float,
        confidence: float,
        label: str
    ) -> Optional[Alert]:
        """
        Update detector with new prediction
        
        Args:
            sentiment_score: Sentiment score (-1 to 1)
            confidence: Prediction confidence (0 to 1)
            label: Sentiment label
        
        Returns:
            Alert if drift detected, None otherwise
        """
        self.recent_scores.append(sentiment_score)
        self.recent_confidences.append(confidence)
        self.recent_labels.append(label)
        
        # Initialize baseline if needed
        if self.baseline_mean is None and len(self.recent_scores) >= self.min_samples:
            self._set_baseline()
            return None
        
        # Check for drift
        if len(self.recent_scores) >= self.min_samples:
            return self._check_drift()
        
        return None
    
    def _set_baseline(self) -> None:
        """Set baseline statistics"""
        scores = np.array(list(self.recent_scores))
        
        self.baseline_mean = np.mean(scores)
        self.baseline_std = np.std(scores)
        
        # Positive ratio
        positive_count = sum(1 for label in self.recent_labels if label == "positive")
        self.baseline_positive_ratio = positive_count / len(self.recent_labels)
        
        logger.info(
            f"Baseline set - Mean: {self.baseline_mean:.3f}, "
            f"Std: {self.baseline_std:.3f}, "
            f"Positive Ratio: {self.baseline_positive_ratio:.3f}"
        )
    
    def _check_drift(self) -> Optional[Alert]:
        """Check for distribution drift"""
        scores = np.array(list(self.recent_scores))
        
        current_mean = np.mean(scores)
        current_positive_ratio = sum(1 for label in self.recent_labels if label == "positive") / len(self.recent_labels)
        
        # Kolmogorov-Smirnov test approximation
        mean_shift = abs(current_mean - self.baseline_mean) / (self.baseline_std + 1e-6)
        ratio_shift = abs(current_positive_ratio - self.baseline_positive_ratio)
        
        # Detect drift
        if mean_shift > 2.0 or ratio_shift > self.drift_threshold:
            if not self.drift_detected:
                self.drift_detected = True
                self.drift_start_time = datetime.now()
                
                return Alert(
                    level=AlertLevel.CRITICAL,
                    message=f"Distribution drift detected! Mean shift: {mean_shift:.2f}σ, Ratio shift: {ratio_shift:.3f}",
                    metric="distribution_drift",
                    current_value=max(mean_shift, ratio_shift * 10),
                    threshold=2.0
                )
        else:
            if self.drift_detected:
                self.drift_detected = False
                logger.info("Drift resolved")
        
        return None


class PerformanceMonitor:
    """Monitor sentiment analysis performance over time"""
    
    def __init__(
        self,
        accuracy_threshold: float = 0.85,
        confidence_threshold_min: float = 0.5,
        latency_threshold_ms: float = 500.0,
        history_size: int = 10000
    ):
        """
        Initialize performance monitor
        
        Args:
            accuracy_threshold: Minimum acceptable accuracy
            confidence_threshold_min: Minimum acceptable confidence
            latency_threshold_ms: Maximum acceptable latency
            history_size: Size of metrics history
        """
        self.accuracy_threshold = accuracy_threshold
        self.confidence_threshold_min = confidence_threshold_min
        self.latency_threshold_ms = latency_threshold_ms
        
        # Metrics history
        self.metrics_history: deque = deque(maxlen=history_size)
        
        # Prediction tracking
        self.predictions = deque(maxlen=history_size)
        self.confidences = deque(maxlen=history_size)
        self.labels = deque(maxlen=history_size)
        
        # Model disagreements
        self.disagreements = deque(maxlen=history_size)
        
        # Inference times
        self.inference_times = deque(maxlen=history_size)
        
        # Cache stats
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Drift detector
        self.drift_detector = DriftDetector()
        
        # Alerts
        self.alerts: List[Alert] = []
    
    def record_prediction(
        self,
        sentiment_score: float,
        confidence: float,
        label: str,
        inference_time_ms: float,
        disagreement: bool = False,
        cache_hit: bool = False
    ) -> List[Alert]:
        """
        Record a prediction
        
        Args:
            sentiment_score: Sentiment score
            confidence: Prediction confidence
            label: Sentiment label
            inference_time_ms: Inference latency
            disagreement: Whether models disagreed
            cache_hit: Whether cache was hit
        
        Returns:
            List of alerts if any
        """
        self.predictions.append(sentiment_score)
        self.confidences.append(confidence)
        self.labels.append(label)
        self.inference_times.append(inference_time_ms)
        self.disagreements.append(disagreement)
        
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        # Check for alerts
        alerts = []
        
        # Confidence alert
        if confidence < self.confidence_threshold_min:
            alerts.append(Alert(
                level=AlertLevel.WARNING,
                message=f"Low confidence prediction: {confidence:.3f}",
                metric="confidence",
                current_value=confidence,
                threshold=self.confidence_threshold_min
            ))
        
        # Latency alert
        if inference_time_ms > self.latency_threshold_ms:
            alerts.append(Alert(
                level=AlertLevel.WARNING,
                message=f"High latency: {inference_time_ms:.1f}ms",
                metric="latency",
                current_value=inference_time_ms,
                threshold=self.latency_threshold_ms
            ))
        
        # Drift detection
        drift_alert = self.drift_detector.update(sentiment_score, confidence, label)
        if drift_alert:
            alerts.append(drift_alert)
        
        # Store alerts
        self.alerts.extend(alerts)
        
        return alerts
    
    def get_metrics_snapshot(self) -> PerformanceMetrics:
        """
        Get current performance metrics
        
        Returns:
            PerformanceMetrics object
        """
        if not self.predictions:
            return PerformanceMetrics(
                timestamp=datetime.now(),
                total_predictions=0,
                positive_ratio=0.0,
                negative_ratio=0.0,
                neutral_ratio=0.0,
                avg_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
                model_disagreement_rate=0.0,
                inference_latency_ms=0.0,
                cache_hit_rate=0.0
            )
        
        labels_list = list(self.labels)
        confidences_array = np.array(list(self.confidences))
        
        positive_count = sum(1 for label in labels_list if label == "positive")
        negative_count = sum(1 for label in labels_list if label == "negative")
        neutral_count = sum(1 for label in labels_list if label == "neutral")
        total = len(labels_list)
        
        disagreement_count = sum(1 for d in self.disagreements if d)
        
        total_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            total_predictions=total,
            positive_ratio=positive_count / total if total > 0 else 0.0,
            negative_ratio=negative_count / total if total > 0 else 0.0,
            neutral_ratio=neutral_count / total if total > 0 else 0.0,
            avg_confidence=float(np.mean(confidences_array)),
            min_confidence=float(np.min(confidences_array)),
            max_confidence=float(np.max(confidences_array)),
            model_disagreement_rate=disagreement_count / total if total > 0 else 0.0,
            inference_latency_ms=float(np.mean(list(self.inference_times))),
            cache_hit_rate=cache_hit_rate
        )
    
    def check_health(self) -> Tuple[bool, List[Alert]]:
        """
        Check overall system health
        
        Returns:
            Tuple of (is_healthy, alerts)
        """
        metrics = self.get_metrics_snapshot()
        health_alerts = []
        
        # Check metrics
        if metrics.avg_confidence < self.confidence_threshold_min:
            health_alerts.append(Alert(
                level=AlertLevel.CRITICAL,
                message=f"Average confidence below threshold: {metrics.avg_confidence:.3f}",
                metric="avg_confidence",
                current_value=metrics.avg_confidence,
                threshold=self.confidence_threshold_min
            ))
        
        if metrics.inference_latency_ms > self.latency_threshold_ms:
            health_alerts.append(Alert(
                level=AlertLevel.WARNING,
                message=f"Average latency above threshold: {metrics.inference_latency_ms:.1f}ms",
                metric="avg_latency",
                current_value=metrics.inference_latency_ms,
                threshold=self.latency_threshold_ms
            ))
        
        # Check for excessive disagreement
        if metrics.model_disagreement_rate > 0.2:
            health_alerts.append(Alert(
                level=AlertLevel.WARNING,
                message=f"High model disagreement rate: {metrics.model_disagreement_rate:.3f}",
                metric="disagreement_rate",
                current_value=metrics.model_disagreement_rate,
                threshold=0.2
            ))
        
        is_healthy = len([a for a in health_alerts if a.level == AlertLevel.CRITICAL]) == 0
        
        return is_healthy, health_alerts
    
    def get_time_series(self, minutes: int = 60) -> Dict[str, List[Any]]:
        """
        Get time series of metrics over specified window
        
        Args:
            minutes: Number of minutes to include
        
        Returns:
            Time series data
        """
        time_series = {
            'timestamps': [],
            'sentiments': list(self.predictions),
            'confidences': list(self.confidences),
            'labels': list(self.labels),
            'inference_times': list(self.inference_times),
            'disagreements': [1 if d else 0 for d in self.disagreements]
        }
        
        return time_series
    
    def get_alerts_summary(self) -> Dict[str, Any]:
        """Get summary of recent alerts"""
        critical = [a for a in self.alerts if a.level == AlertLevel.CRITICAL]
        warnings = [a for a in self.alerts if a.level == AlertLevel.WARNING]
        
        return {
            'total_alerts': len(self.alerts),
            'critical_alerts': len(critical),
            'warnings': len(warnings),
            'recent_alerts': [a.to_dict() for a in self.alerts[-10:]]
        }
    
    def reset(self) -> None:
        """Reset monitor"""
        self.predictions.clear()
        self.confidences.clear()
        self.labels.clear()
        self.inference_times.clear()
        self.disagreements.clear()
        self.alerts.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info("Monitor reset")


class ModelComparisonTracker:
    """Track differences between ensemble models"""
    
    def __init__(self):
        """Initialize tracker"""
        self.comparisons: List[Dict[str, Any]] = []
        self.model_pairs = {}
    
    def record_comparison(
        self,
        text: str,
        model1_name: str,
        model1_score: float,
        model1_confidence: float,
        model2_name: str,
        model2_score: float,
        model2_confidence: float
    ) -> None:
        """
        Record model comparison
        
        Args:
            text: Input text
            model1_name: First model name
            model1_score: First model score
            model1_confidence: First model confidence
            model2_name: Second model name
            model2_score: Second model score
            model2_confidence: Second model confidence
        """
        agreement = abs(model1_score - model2_score) < 0.3
        
        pair_key = tuple(sorted([model1_name, model2_name]))
        
        if pair_key not in self.model_pairs:
            self.model_pairs[pair_key] = {
                'comparisons': 0,
                'agreements': 0,
                'avg_score_diff': 0.0
            }
        
        self.model_pairs[pair_key]['comparisons'] += 1
        if agreement:
            self.model_pairs[pair_key]['agreements'] += 1
        
        diff = abs(model1_score - model2_score)
        prev_diff = self.model_pairs[pair_key]['avg_score_diff']
        n = self.model_pairs[pair_key]['comparisons']
        self.model_pairs[pair_key]['avg_score_diff'] = (prev_diff * (n - 1) + diff) / n
        
        self.comparisons.append({
            'text': text,
            'timestamp': datetime.now(),
            'model1': {'name': model1_name, 'score': model1_score, 'confidence': model1_confidence},
            'model2': {'name': model2_name, 'score': model2_score, 'confidence': model2_confidence},
            'agreement': agreement
        })
    
    def get_agreement_stats(self) -> Dict[str, Any]:
        """
        Get model agreement statistics
        
        Returns:
            Agreement statistics
        """
        stats = {}
        
        for pair, data in self.model_pairs.items():
            agreement_rate = (data['agreements'] / data['comparisons']
                            if data['comparisons'] > 0 else 0.0)
            
            stats[f"{pair[0]} vs {pair[1]}"] = {
                'total_comparisons': data['comparisons'],
                'agreements': data['agreements'],
                'agreement_rate': agreement_rate,
                'avg_score_diff': data['avg_score_diff']
            }
        
        return stats
    
    def get_disagreements(self, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Get predictions where models disagreed significantly
        
        Args:
            threshold: Disagreement threshold
        
        Returns:
            List of disagreement records
        """
        disagreements = []
        
        for comp in self.comparisons:
            score_diff = abs(comp['model1']['score'] - comp['model2']['score'])
            
            if score_diff > threshold:
                disagreements.append({
                    'text': comp['text'],
                    'timestamp': comp['timestamp'],
                    'model1': comp['model1'],
                    'model2': comp['model2'],
                    'score_diff': score_diff
                })
        
        return disagreements


class IngestionMonitor:
    """Tracks ingestion health: fetch success/fail ratios and database write latencies."""
    
    def __init__(self, log_filepath: str = "ingestion_metrics.json"):
        import threading
        self.log_filepath = log_filepath
        self.stats = {
            "reddit": {"fetches": 0, "failures": 0, "total_fetch_time_ms": 0.0, "writes": 0, "write_failures": 0, "total_write_time_ms": 0.0},
            "news": {"fetches": 0, "failures": 0, "total_fetch_time_ms": 0.0, "writes": 0, "write_failures": 0, "total_write_time_ms": 0.0},
            "price": {"fetches": 0, "failures": 0, "total_fetch_time_ms": 0.0, "writes": 0, "write_failures": 0, "total_write_time_ms": 0.0},
            "trends": {"fetches": 0, "failures": 0, "total_fetch_time_ms": 0.0, "writes": 0, "write_failures": 0, "total_write_time_ms": 0.0}
        }
        self.lock = threading.Lock()

    def record_fetch(self, source: str, success: bool, latency_ms: float):
        with self.lock:
            source = source.lower()
            if source in self.stats:
                self.stats[source]["fetches"] += 1
                if not success:
                    self.stats[source]["failures"] += 1
                self.stats[source]["total_fetch_time_ms"] += latency_ms
                self._save_to_file()

    def record_write(self, source: str, success: bool, latency_ms: float):
        with self.lock:
            source = source.lower()
            if source in self.stats:
                self.stats[source]["writes"] += 1
                if not success:
                    self.stats[source]["write_failures"] += 1
                self.stats[source]["total_write_time_ms"] += latency_ms
                self._save_to_file()

    def get_summary(self) -> Dict[str, Any]:
        summary = {}
        for source, data in self.stats.items():
            fetches = data["fetches"]
            failures = data["failures"]
            success_rate = (fetches - failures) / fetches if fetches > 0 else 1.0
            avg_fetch_latency = data["total_fetch_time_ms"] / fetches if fetches > 0 else 0.0
            
            writes = data["writes"]
            write_failures = data["write_failures"]
            write_success_rate = (writes - write_failures) / writes if writes > 0 else 1.0
            avg_write_latency = data["total_write_time_ms"] / writes if writes > 0 else 0.0
            
            summary[source] = {
                "total_fetches": fetches,
                "fetch_failures": failures,
                "fetch_success_rate": float(success_rate),
                "avg_fetch_latency_ms": float(avg_fetch_latency),
                "total_writes": writes,
                "write_failures": write_failures,
                "write_success_rate": float(write_success_rate),
                "avg_write_latency_ms": float(avg_write_latency),
                "status": "healthy" if success_rate > 0.9 and write_success_rate > 0.95 else "degraded"
            }
        return summary

    def _save_to_file(self):
        try:
            summary = self.get_summary()
            with open(self.log_filepath, "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "metrics": summary
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save ingestion metrics: {e}")


# Global instance of the ingestion monitor
ingestion_monitor = IngestionMonitor()


# Example usage
if __name__ == "__main__":
    # Create monitor
    monitor = PerformanceMonitor()
    
    # Simulate predictions
    np.random.seed(42)
    
    logger.info("Simulating sentiment predictions...")
    
    for i in range(500):
        score = np.random.randn() * 0.3
        confidence = np.random.beta(5, 2)
        label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
        latency = abs(np.random.normal(250, 50))
        disagreement = np.random.random() < 0.15
        cache_hit = np.random.random() < 0.6
        
        alerts = monitor.record_prediction(
            score, confidence, label, latency, disagreement, cache_hit
        )
        
        if alerts:
            logger.warning(f"Alerts generated: {[a.message for a in alerts]}")
    
    # Get metrics
    metrics = monitor.get_metrics_snapshot()
    logger.info(f"\nMetrics Snapshot:")
    logger.info(f"  Total Predictions: {metrics.total_predictions}")
    logger.info(f"  Avg Confidence: {metrics.avg_confidence:.3f}")
    logger.info(f"  Avg Latency: {metrics.inference_latency_ms:.1f}ms")
    logger.info(f"  Positive Ratio: {metrics.positive_ratio:.3f}")
    logger.info(f"  Disagreement Rate: {metrics.model_disagreement_rate:.3f}")
    logger.info(f"  Cache Hit Rate: {metrics.cache_hit_rate:.3f}")
    
    # Check health
    is_healthy, health_alerts = monitor.check_health()
    logger.info(f"\nSystem Health: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
    
    if health_alerts:
        logger.info("Health Alerts:")
        for alert in health_alerts:
            logger.info(f"  [{alert.level.value}] {alert.message}")
    
    # Alert summary
    alert_summary = monitor.get_alerts_summary()
    logger.info(f"\nAlert Summary: {json.dumps(alert_summary, indent=2, default=str)}")


# ============================================================================
# SYSTEM HEALTH, TELEMETRY ALERTS & FLOWER MONITORING
# ============================================================================

import requests
from config import api_settings

def check_system_health() -> dict:
    """Verifies connection health of SQL DB engines, Redis pools, and local models."""
    from dependencies import engine, get_inference_engine
    
    db_ok = False
    try:
        from sqlalchemy import text
        with engine.sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False
        
    redis_ok = False
    try:
        import redis
        client = redis.Redis.from_url(api_settings.redis_uri, socket_timeout=1.0)
        client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    model_ok = False
    try:
        engine_inst = get_inference_engine()
        if engine_inst and engine_inst.model is not None:
            model_ok = True
    except Exception:
        model_ok = False
        
    status = "healthy" if (db_ok and redis_ok and model_ok) else "degraded"
    return {
        "status": status,
        "database": "connected" if db_ok else "offline",
        "redis": "connected" if redis_ok else "offline",
        "model": "loaded" if model_ok else "unloaded",
        "timestamp": datetime.now().isoformat()
    }


def check_flower_status(flower_url: str = "http://localhost:5555") -> dict:
    """Verifies Celery Flower daemon dashboard connectivity."""
    try:
        res = requests.get(flower_url + "/api/workers", timeout=1.0)
        if res.status_code == 200:
            return {"status": "online", "url": flower_url, "workers_count": len(res.json())}
    except Exception:
        pass
    return {"status": "offline", "url": flower_url, "workers_count": 0}


# ============================================================================
# PROMETHEUS METRICS INTEGRATION
# ============================================================================

try:
    from prometheus_client import Counter, Histogram, Gauge
    
    PREDICTIONS_TOTAL = Counter('moodmarket_predictions_total', 'Total predictions', ['ticker', 'direction'])
    PREDICTION_LATENCY = Histogram('moodmarket_prediction_latency_seconds', 'Prediction latency')
    ACTIVE_WS_CONNECTIONS = Gauge('moodmarket_websocket_connections', 'Active WebSocket connections')
    ANOMALY_ALERTS = Counter('moodmarket_anomaly_alerts_total', 'Anomaly alerts fired', ['ticker', 'level'])
    CACHE_HIT_RATE = Gauge('moodmarket_cache_hit_rate', 'Redis cache hit rate')
    SENTIMENT_DRIFT = Gauge('moodmarket_sentiment_drift_score', 'Current drift magnitude')
except ImportError:
    # Fallback mock class in case prometheus-client is missing
    class MockMetric:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def inc(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        
    PREDICTIONS_TOTAL = MockMetric()
    PREDICTION_LATENCY = MockMetric()
    ACTIVE_WS_CONNECTIONS = MockMetric()
    ANOMALY_ALERTS = MockMetric()
    CACHE_HIT_RATE = MockMetric()
    SENTIMENT_DRIFT = MockMetric()


# clean architecture alignment
