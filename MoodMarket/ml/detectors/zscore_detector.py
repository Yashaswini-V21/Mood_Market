"""
Z-score based anomaly detector.
Detects anomalies when value exceeds mean ± 3σ (statistically rare events).
"""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
from .base_detector import BaseDetector, DetectionResult
import logging

logger = logging.getLogger(__name__)


class ZScoreDetector(BaseDetector):
    """
    Z-score based anomaly detector
    
    Flags anomalies when:
    - |z_score| > threshold (default 3.0 = 99.7% CI)
    
    Advantages:
    - Simple and interpretable
    - Fast computation
    - Good for Gaussian distributions
    
    Disadvantages:
    - Assumes normal distribution
    - Sensitive to outliers in training data
    - May miss non-linear anomalies
    """
    
    def __init__(
        self,
        threshold: float = 3.0,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0,
        adapt_threshold: bool = True,
        min_std: float = 1e-6
    ):
        """
        Initialize Z-score detector
        
        Args:
            threshold: Z-score threshold (default 3.0 = ±3σ)
            window_size: Days to track
            min_history: Minimum observations
            sensitivity: Sensitivity multiplier (< 1.0 = less sensitive)
            adapt_threshold: Adapt threshold based on observed distribution
            min_std: Minimum std dev to prevent division by zero
        """
        super().__init__("zscore", window_size, min_history, sensitivity)
        self.threshold = threshold * sensitivity
        self.adapt_threshold = adapt_threshold
        self.min_std = min_std
        
        # Statistics
        self.mean = None
        self.std = None
        self.min_val = None
        self.max_val = None
        self.history = []
    
    def fit(self, data: np.ndarray, **kwargs) -> None:
        """
        Fit on historical data
        
        Args:
            data: Historical volume data (n_samples,)
            **kwargs: Additional parameters
        """
        data = self._validate_data(data, min_samples=self.min_history)
        
        self.history = list(data[-self.window_size * 96:])  # Keep last 30 days
        
        # Calculate statistics
        self.mean = np.mean(data)
        self.std = np.std(data)
        self.min_val = np.min(data)
        self.max_val = np.max(data)
        
        # Ensure minimum std to prevent division by zero
        if self.std < self.min_std:
            self.std = self.min_std
        
        self.is_fitted = True
        self.n_observations = len(data)
        
        logger.info(
            f"Z-score detector fitted: mean={self.mean:.2f}, "
            f"std={self.std:.2f}, threshold={self.threshold:.2f}"
        )
    
    def predict(self, observation: float) -> DetectionResult:
        """
        Detect anomaly using Z-score
        
        Args:
            observation: Current volume
        
        Returns:
            DetectionResult with anomaly_detected and confidence
        """
        self._check_fitted()
        
        # Calculate z-score
        if self.std == 0:
            z_score = 0.0
        else:
            z_score = (observation - self.mean) / self.std
        
        # Check if anomaly
        is_anomaly = abs(z_score) > self.threshold
        
        # Confidence increases with |z_score|
        # Formula: 1 - exp(-k * excess - 0.5 * z/thresh) gives >0.8 at 4σ
        excess = max(0.0, abs(z_score) - self.threshold)
        confidence = min(1.0 - np.exp(-1.5 * excess - 0.5 * (abs(z_score) / self.threshold)), 0.99)
        
        # Add history
        self.history.append(observation)
        if len(self.history) > self.window_size * 96:
            self.history.pop(0)
            # Periodically update statistics
            if len(self.history) % 96 == 0:
                self._update_statistics()
        
        return DetectionResult(
            anomaly_detected=is_anomaly,
            confidence=confidence if is_anomaly else 0.0,
            score=abs(z_score),
            threshold=self.threshold,
            metadata={
                "z_score": float(z_score),
                "mean": float(self.mean),
                "std": float(self.std),
                "observation": float(observation),
                "upper_bound": float(self.mean + self.threshold * self.std),
                "lower_bound": float(self.mean - self.threshold * self.std)
            }
        )
    
    def update(self, observation: float) -> None:
        """Update with new observation"""
        super().update(observation)
        
        # Exponential moving average update (slow adaptation)
        alpha = 0.01  # Learning rate
        self.mean = self.mean * (1 - alpha) + observation * alpha
    
    def _update_statistics(self) -> None:
        """Recalculate statistics from recent history"""
        if len(self.history) < self.min_history:
            return
        
        history_array = np.array(self.history[-self.window_size * 96:])
        self.mean = np.mean(history_array)
        new_std = np.std(history_array)
        
        # Smooth std dev update
        alpha = 0.1
        self.std = self.std * (1 - alpha) + max(new_std, self.min_std) * alpha
        
        self.min_val = np.min(history_array)
        self.max_val = np.max(history_array)
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "detector": "zscore",
            "mean": float(self.mean) if self.mean else None,
            "std": float(self.std) if self.std else None,
            "threshold": float(self.threshold),
            "min_value": float(self.min_val) if self.min_val else None,
            "max_value": float(self.max_val) if self.max_val else None,
            "observations": self.n_observations,
            "fitted": self.is_fitted
        }
    
    def set_threshold(self, threshold: float) -> None:
        """
        Dynamically adjust Z-score threshold
        
        Args:
            threshold: New Z-score threshold (e.g., 2.0, 3.0, 4.0)
        """
        self.threshold = threshold * self.sensitivity
        logger.info(f"Z-score threshold updated to {self.threshold:.2f}")


class MultiVarZScoreDetector(BaseDetector):
    """
    Multi-variable Z-score detector
    Detects anomalies in multiple dimensions simultaneously
    """
    
    def __init__(
        self,
        n_features: int = 3,
        threshold: float = 3.0,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0,
        min_std: float = 1e-6
    ):
        """
        Initialize multi-variable detector
        
        Args:
            n_features: Number of variables (Reddit, Google Trends, Twitter)
            threshold: Z-score threshold per feature
            window_size: Days of history
            min_history: Minimum observations
            sensitivity: Sensitivity multiplier
            min_std: Minimum std dev
        """
        super().__init__("multivar_zscore", window_size, min_history, sensitivity)
        self.n_features = n_features
        self.threshold = threshold * sensitivity
        self.min_std = min_std
        
        # Per-feature statistics
        self.means = np.zeros(n_features)
        self.stds = np.ones(n_features) * self.min_std
        self.history = []
        
        self.feature_names = ["reddit_volume", "google_trends", "twitter_volume"]
    
    def fit(self, data: np.ndarray, **kwargs) -> None:
        """
        Fit on multi-dimensional data
        
        Args:
            data: Shape (n_samples, n_features)
        """
        data = self._validate_data(data, min_samples=self.min_history)
        
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        if data.shape[1] != self.n_features:
            raise ValueError(
                f"Expected {self.n_features} features, got {data.shape[1]}"
            )
        
        self.history = [list(row) for row in data[-self.window_size * 96:]]
        
        # Calculate per-feature statistics
        for i in range(self.n_features):
            self.means[i] = np.mean(data[:, i])
            std = np.std(data[:, i])
            self.stds[i] = max(std, self.min_std)
        
        self.is_fitted = True
        self.n_observations = len(data)
        
        logger.info(
            f"Multi-var Z-score detector fitted: features={self.n_features}, "
            f"threshold={self.threshold:.2f}"
        )
    
    def predict(self, observation: np.ndarray) -> DetectionResult:
        """
        Detect anomalies in multi-dimensional observation
        
        Args:
            observation: Current values, shape (n_features,)
        
        Returns:
            DetectionResult
        """
        self._check_fitted()
        
        observation = np.asarray(observation)
        if observation.shape[0] != self.n_features:
            raise ValueError(f"Expected {self.n_features} values, got {observation.shape[0]}")
        
        # Calculate z-scores per feature
        z_scores = (observation - self.means) / self.stds
        
        # Aggregate: any feature anomaly = overall anomaly
        max_zscore = np.max(np.abs(z_scores))
        is_anomaly = max_zscore > self.threshold
        
        # Confidence based on maximum anomaly
        confidence = min((max_zscore / 5.0) ** 1.5, 0.99)
        
        return DetectionResult(
            anomaly_detected=is_anomaly,
            confidence=confidence if is_anomaly else 0.0,
            score=float(max_zscore),
            threshold=self.threshold,
            metadata={
                "z_scores": {
                    self.feature_names[i]: float(z_scores[i])
                    for i in range(self.n_features)
                },
                "means": {
                    self.feature_names[i]: float(self.means[i])
                    for i in range(self.n_features)
                },
                "stds": {
                    self.feature_names[i]: float(self.stds[i])
                    for i in range(self.n_features)
                }
            }
        )
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "detector": "multivar_zscore",
            "n_features": self.n_features,
            "feature_names": self.feature_names,
            "means": {self.feature_names[i]: float(self.means[i]) for i in range(self.n_features)},
            "stds": {self.feature_names[i]: float(self.stds[i]) for i in range(self.n_features)},
            "threshold": float(self.threshold),
            "observations": self.n_observations,
            "fitted": self.is_fitted
        }
