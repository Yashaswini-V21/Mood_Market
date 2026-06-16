"""
Main anomaly detection orchestrator.
Combines multiple detectors with ensemble voting for "Hype Storm" detection.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
import logging
from collections import defaultdict

from detectors.zscore_detector import ZScoreDetector, MultiVarZScoreDetector
from detectors.isolation_forest_detector import IsolationForestDetector, MultiVarIsolationForestDetector
from detectors.autoencoder_detector import AutoencoderDetector, MultiVarAutoencoderDetector
from detectors.ewma_detector import EWMADetector, AdaptiveEWMADetector
from detectors.base_detector import DetectionResult

logger = logging.getLogger(__name__)


@dataclass
class AnomalyAlert:
    """Alert for detected anomaly"""
    timestamp: datetime
    ticker: str
    anomaly_detected: bool
    confidence: float  # 0-1
    alert_type: str  # HYPE_STORM, VOLATILITY_SPIKE, etc.
    
    # Data metrics
    reddit_volume: float
    reddit_baseline: float
    reddit_zscore: float
    
    google_trends_spike: bool
    twitter_volume: float
    volatility_jump: bool
    
    # Methods triggered
    methods_triggered: List[str]  # ["zscore", "isolation_forest", etc.]
    method_scores: Dict[str, float]  # Score per method
    
    # Recommendation
    recommendation: str  # REDUCE_POSITION_SIZE, INVESTIGATE, IGNORE
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


@dataclass
class TickerBaseline:
    """Historical baseline for a ticker"""
    ticker: str
    reddit_mean: float
    reddit_std: float
    google_trends_mean: float
    google_trends_std: float
    twitter_mean: float
    twitter_std: float
    last_updated: datetime

    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "reddit_mean": self.reddit_mean,
            "reddit_std": self.reddit_std,
            "google_trends_mean": self.google_trends_mean,
            "google_trends_std": self.google_trends_std,
            "twitter_mean": self.twitter_mean,
            "twitter_std": self.twitter_std,
            "last_updated": self.last_updated.isoformat(),
        }


class AnomalyDetector:
    """
    Main anomaly detection orchestrator
    
    Combines 4 detection methods:
    1. Z-score: Statistical outliers
    2. Isolation Forest: Non-linear patterns
    3. Autoencoder: Learned patterns
    4. EWMA: Volatility spikes
    
    Features:
    - Thread-safe for concurrent updates
    - Per-ticker baseline tracking
    - Ensemble voting with confidence
    - Real-time monitoring
    """
    
    def __init__(
        self,
        zscore_threshold: float = 3.0,
        if_contamination: float = 0.05,
        ewma_alpha: float = 0.2,
        ensemble_threshold: float = 0.65,
        confidence_threshold: float = 0.7,
        n_stocks: int = 500
    ):
        """
        Initialize anomaly detector
        
        Args:
            zscore_threshold: Z-score for anomaly (default 3.0 = ±3σ)
            if_contamination: IF expected anomaly rate
            ewma_alpha: EWMA smoothing
            ensemble_threshold: Fraction of methods needed to trigger alert
            confidence_threshold: Min confidence for alert
            n_stocks: Expected number of stocks to monitor
        """
        self.zscore_threshold = zscore_threshold
        self.if_contamination = if_contamination
        self.ewma_alpha = ewma_alpha
        self.ensemble_threshold = ensemble_threshold
        self.confidence_threshold = confidence_threshold
        
        # Per-ticker detectors
        self.detectors: Dict[str, Dict] = {}
        self.baselines: Dict[str, TickerBaseline] = {}
        
        # Alert history
        self.alert_history: List[AnomalyAlert] = []
        self.false_positive_count: Dict[str, int] = defaultdict(int)
        self.total_alerts: Dict[str, int] = defaultdict(int)
        
        # Thread safety
        self.lock = threading.RLock()
        
        logger.info(
            f"AnomalyDetector initialized: "
            f"ensemble_threshold={ensemble_threshold}, "
            f"confidence_threshold={confidence_threshold}"
        )
    
    def _get_or_create_detectors(self, ticker: str) -> Dict:
        """Get or create detector suite for ticker"""
        if ticker not in self.detectors:
            with self.lock:
                if ticker not in self.detectors:
                    self.detectors[ticker] = {
                        "zscore": ZScoreDetector(
                            threshold=self.zscore_threshold,
                            sensitivity=1.0
                        ),
                        "isolation_forest": IsolationForestDetector(
                            contamination=self.if_contamination
                        ),
                        "autoencoder": AutoencoderDetector(
                            hidden_size=16
                        ),
                        "ewma": AdaptiveEWMADetector(
                            alpha=self.ewma_alpha
                        ),
                        "multivar_zscore": MultiVarZScoreDetector(n_features=3),
                        "multivar_if": MultiVarIsolationForestDetector(n_features=3),
                        "multivar_autoencoder": MultiVarAutoencoderDetector(n_features=3),
                    }
        
        return self.detectors[ticker]
    
    def fit_baseline(
        self,
        ticker: str,
        reddit_history: np.ndarray,
        google_trends_history: np.ndarray,
        twitter_history: np.ndarray
    ) -> None:
        """
        Learn baseline from 30-day history
        
        Args:
            ticker: Stock ticker
            reddit_history: Reddit volume history (n_samples,)
            google_trends_history: Google Trends scores (n_samples,)
            twitter_history: Twitter volume history (n_samples,)
        """
        with self.lock:
            logger.info(f"Fitting baseline for {ticker}...")
            
            # Get or create detectors
            detectors = self._get_or_create_detectors(ticker)
            
            # Univariate fitting
            detectors["zscore"].fit(reddit_history)
            detectors["isolation_forest"].fit(reddit_history)
            detectors["autoencoder"].fit(reddit_history)
            detectors["ewma"].fit(reddit_history)
            
            # Multivariate fitting
            multivar_data = np.column_stack([
                reddit_history,
                google_trends_history,
                twitter_history
            ])
            
            detectors["multivar_zscore"].fit(multivar_data)
            detectors["multivar_if"].fit(multivar_data)
            detectors["multivar_autoencoder"].fit(multivar_data)
            
            # Store baseline
            self.baselines[ticker] = TickerBaseline(
                ticker=ticker,
                reddit_mean=float(np.mean(reddit_history)),
                reddit_std=float(np.std(reddit_history)),
                google_trends_mean=float(np.mean(google_trends_history)),
                google_trends_std=float(np.std(google_trends_history)),
                twitter_mean=float(np.mean(twitter_history)),
                twitter_std=float(np.std(twitter_history)),
                last_updated=datetime.now()
            )
            
            logger.info(f"Baseline fitted for {ticker}")
    
    def predict(
        self,
        ticker: str,
        reddit_volume: float,
        google_trends_score: float,
        twitter_volume: float
    ) -> AnomalyAlert:
        """
        Detect anomaly in real-time data
        
        Args:
            ticker: Stock ticker
            reddit_volume: Current Reddit mention count
            google_trends_score: Google Trends score (0-100)
            twitter_volume: Twitter tweets/minute
        
        Returns:
            AnomalyAlert with detection results
        """
        with self.lock:
            detectors = self._get_or_create_detectors(ticker)
            baseline = self.baselines.get(ticker)
            
            if baseline is None:
                raise RuntimeError(f"Baseline not fitted for {ticker}")
            
            # Run univariate detectors
            zscore_result = detectors["zscore"].predict(reddit_volume)
            if_result = detectors["isolation_forest"].predict(reddit_volume)
            ae_result = detectors["autoencoder"].predict(reddit_volume)
            ewma_result = detectors["ewma"].predict(reddit_volume)
            
            # Run multivariate detectors
            multivar_data = np.array([reddit_volume, google_trends_score, twitter_volume])
            multivar_zscore_result = detectors["multivar_zscore"].predict(multivar_data)
            multivar_if_result = detectors["multivar_if"].predict(multivar_data)
            multivar_ae_result = detectors["multivar_autoencoder"].predict(multivar_data)
            
            # Collect results
            results = {
                "zscore": zscore_result,
                "isolation_forest": if_result,
                "autoencoder": ae_result,
                "ewma": ewma_result,
                "multivar_zscore": multivar_zscore_result,
                "multivar_if": multivar_if_result,
                "multivar_autoencoder": multivar_ae_result,
            }
            
            # Ensemble voting
            anomalies_triggered = sum(1 for r in results.values() if r.anomaly_detected)
            total_methods = len(results)
            vote_ratio = anomalies_triggered / total_methods
            
            ensemble_anomaly = vote_ratio >= self.ensemble_threshold
            ensemble_confidence = self._compute_ensemble_confidence(results)
            
            # Alert generation
            methods_triggered = [name for name, r in results.items() if r.anomaly_detected]
            method_scores = {name: r.score for name, r in results.items()}
            
            # Calculate metrics
            reddit_zscore = zscore_result.metadata["z_score"]
            google_trends_spike = (google_trends_score > 
                                   baseline.google_trends_mean + 2 * baseline.google_trends_std)
            
            # Determine alert type and recommendation
            alert_type, recommendation = self._determine_alert_type(
                reddit_zscore=reddit_zscore,
                google_trends_spike=google_trends_spike,
                ewma_triggered=ewma_result.anomaly_detected,
                ensemble_confidence=ensemble_confidence,
                vote_ratio=vote_ratio
            )
            
            # Create alert
            alert = AnomalyAlert(
                timestamp=datetime.now(),
                ticker=ticker,
                anomaly_detected=ensemble_anomaly and ensemble_confidence >= self.confidence_threshold,
                confidence=ensemble_confidence,
                alert_type=alert_type,
                reddit_volume=float(reddit_volume),
                reddit_baseline=baseline.reddit_mean,
                reddit_zscore=float(reddit_zscore),
                google_trends_spike=google_trends_spike,
                twitter_volume=float(twitter_volume),
                volatility_jump=ewma_result.anomaly_detected,
                methods_triggered=methods_triggered,
                method_scores=method_scores,
                recommendation=recommendation
            )
            
            # Track alert
            self.alert_history.append(alert)
            if alert.anomaly_detected:
                self.total_alerts[ticker] += 1
            
            # Update detectors
            for detector in detectors.values():
                detector.update(reddit_volume)
            
            return alert
    
    def _compute_ensemble_confidence(self, results: Dict[str, DetectionResult]) -> float:
        """
        Compute ensemble confidence from individual detectors
        
        Strategy:
        - Weight detectors by type (univariate more important for single variable)
        - Average confidences
        - Boost if multiple detectors agree
        """
        weights = {
            "zscore": 1.0,
            "isolation_forest": 0.8,
            "autoencoder": 0.7,
            "ewma": 0.9,
            "multivar_zscore": 0.6,
            "multivar_if": 0.5,
            "multivar_autoencoder": 0.5,
        }
        
        total_weight = 0
        weighted_confidence = 0
        
        for method, result in results.items():
            weight = weights.get(method, 1.0)
            confidence = result.confidence if result.anomaly_detected else 0.0
            weighted_confidence += weight * confidence
            total_weight += weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def _determine_alert_type(
        self,
        reddit_zscore: float,
        google_trends_spike: bool,
        ewma_triggered: bool,
        ensemble_confidence: float,
        vote_ratio: float
    ) -> Tuple[str, str]:
        """
        Determine alert type and recommendation
        
        Returns:
            (alert_type, recommendation)
        """
        # Alert type logic
        if abs(reddit_zscore) > 5 and google_trends_spike and ewma_triggered:
            alert_type = "HYPE_STORM"  # Full multi-source extreme spike
            recommendation = "REDUCE_POSITION_SIZE"
        elif abs(reddit_zscore) > 4 and vote_ratio > 0.7:
            # High-confidence extreme spike — classify as HYPE_STORM
            alert_type = "HYPE_STORM"
            recommendation = "REDUCE_POSITION_SIZE"
        elif abs(reddit_zscore) > 3 and google_trends_spike:
            alert_type = "MAJOR_SPIKE"
            recommendation = "INVESTIGATE"
        elif ewma_triggered and vote_ratio > 0.6:
            alert_type = "VOLATILITY_SPIKE"
            recommendation = "MONITOR_CLOSELY"
        else:
            alert_type = "ANOMALY_DETECTED"
            recommendation = "INVESTIGATE"

        return alert_type, recommendation
    
    def get_alert_summary(self, ticker: str) -> Dict:
        """Get alert summary for ticker"""
        total = self.total_alerts[ticker]
        false_pos = self.false_positive_count[ticker]
        
        fpr = (false_pos / total) if total > 0 else 0
        
        return {
            "ticker": ticker,
            "total_alerts": total,
            "false_positives": false_pos,
            "false_positive_rate": float(fpr),
            "recent_alerts": [a.to_dict() for a in self.alert_history[-10:] 
                             if a.ticker == ticker]
        }
    
    def mark_false_positive(self, ticker: str) -> None:
        """Mark most recent alert for ticker as false positive"""
        with self.lock:
            for alert in reversed(self.alert_history):
                if alert.ticker == ticker:
                    self.false_positive_count[ticker] += 1
                    break
    
    def get_detector_stats(self, ticker: str) -> Dict:
        """Get statistics for all detectors of a ticker"""
        detectors = self._get_or_create_detectors(ticker)
        
        stats = {
            "ticker": ticker,
            "baseline": self.baselines[ticker].to_dict() if ticker in self.baselines else None,
            "detectors": {
                name: detector.get_stats()
                for name, detector in detectors.items()
            }
        }
        
        return stats
    
    def get_global_stats(self) -> Dict:
        """Get global system statistics"""
        return {
            "n_stocks": len(self.detectors),
            "total_alerts": sum(self.total_alerts.values()),
            "total_false_positives": sum(self.false_positive_count.values()),
            "false_positive_rate": (
                sum(self.false_positive_count.values()) / sum(self.total_alerts.values())
                if sum(self.total_alerts.values()) > 0 else 0
            ),
            "alerts_per_stock": dict(self.total_alerts),
            "fpr_per_stock": {
                ticker: (self.false_positive_count[ticker] / self.total_alerts[ticker]
                         if self.total_alerts[ticker] > 0 else 0)
                for ticker in self.total_alerts.keys()
            }
        }

# clean architecture alignment
