"""
Base detector abstract class for anomaly detection.
Provides common interface and utilities for all detector implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Result from a single detector"""
    anomaly_detected: bool
    confidence: float  # 0.0-1.0
    score: float  # Raw detector score
    threshold: float  # What triggered detection
    metadata: Dict = None  # Detector-specific info
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseDetector(ABC):
    """
    Abstract base class for anomaly detectors
    
    All detectors must implement:
    - fit(): Learn baseline from historical data
    - predict(): Generate detection result for current observation
    - get_stats(): Return detector statistics
    """
    
    def __init__(
        self,
        name: str,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0
    ):
        """
        Initialize base detector
        
        Args:
            name: Detector name
            window_size: Days of history to track
            min_history: Minimum days needed before predicting
            sensitivity: Sensitivity multiplier (higher = more sensitive)
        """
        self.name = name
        self.window_size = window_size
        self.min_history = min_history
        self.sensitivity = sensitivity
        self.is_fitted = False
        self.fit_timestamp = None
        self.n_observations = 0
    
    @abstractmethod
    def fit(self, data: np.ndarray, **kwargs) -> None:
        """
        Fit detector on historical data
        
        Args:
            data: Shape (n_samples,) or (n_samples, n_features)
            **kwargs: Additional parameters for specific detectors
        """
        pass
    
    @abstractmethod
    def predict(self, observation: float) -> DetectionResult:
        """
        Detect anomaly in current observation
        
        Args:
            observation: Current value(s)
        
        Returns:
            DetectionResult with anomaly_detected and confidence
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict:
        """Get detector statistics and thresholds"""
        pass
    
    def update(self, observation: float) -> None:
        """
        Update detector with new observation
        Called after prediction to keep baseline fresh
        
        Args:
            observation: New observation value
        """
        self.n_observations += 1
    
    def _validate_data(self, data: np.ndarray, min_samples: int = 2) -> np.ndarray:
        """
        Validate and convert input data
        
        Args:
            data: Input data
            min_samples: Minimum number of samples required
        
        Returns:
            Validated numpy array
        
        Raises:
            ValueError: If data is invalid
        """
        data = np.asarray(data)
        
        if data.ndim == 0:
            raise ValueError("Data must be at least 1-dimensional")
        
        if data.shape[0] < min_samples:
            raise ValueError(
                f"Need at least {min_samples} samples, got {data.shape[0]}"
            )
        
        if np.isnan(data).any():
            logger.warning("Data contains NaN values, replacing with 0")
            data = np.nan_to_num(data, nan=0.0)
        
        if np.isinf(data).any():
            logger.warning("Data contains inf values, replacing with max/min")
            finite_data = data[np.isfinite(data)]
            if len(finite_data) > 0:
                data = np.where(np.isinf(data), np.nanmax(finite_data) * 10, data)
        
        return data
    
    def _normalize(self, data: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        Min-max normalize data to [0, 1]
        
        Args:
            data: Input data
        
        Returns:
            (normalized_data, min_val, max_val)
        """
        min_val = np.min(data)
        max_val = np.max(data)
        
        if max_val - min_val == 0:
            return np.zeros_like(data), min_val, max_val
        
        normalized = (data - min_val) / (max_val - min_val)
        return normalized, min_val, max_val
    
    def _denormalize(self, data: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
        """Reverse min-max normalization"""
        if max_val - min_val == 0:
            return np.full_like(data, min_val)
        return data * (max_val - min_val) + min_val
    
    def _check_fitted(self) -> None:
        """Check if detector is fitted"""
        if not self.is_fitted:
            raise RuntimeError(f"{self.name} detector not fitted. Call fit() first.")
    
    def _check_sufficient_history(self) -> None:
        """Check if enough history to make prediction"""
        if self.n_observations < self.min_history:
            raise RuntimeError(
                f"Only {self.n_observations} observations, "
                f"need {self.min_history} for reliable prediction"
            )


class MultiVariateDetector(BaseDetector):
    """Base class for detectors that handle multiple variables"""
    
    def __init__(
        self,
        name: str,
        n_features: int = 1,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0
    ):
        """
        Initialize multivariate detector
        
        Args:
            name: Detector name
            n_features: Number of features to track
            window_size: Days of history
            min_history: Minimum observations before predicting
            sensitivity: Sensitivity multiplier
        """
        super().__init__(name, window_size, min_history, sensitivity)
        self.n_features = n_features
        self.feature_names = [f"feature_{i}" for i in range(n_features)]


class TimeSeriesDetector(BaseDetector):
    """Base class for time series anomaly detection"""
    
    def __init__(
        self,
        name: str,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0,
        lookback_period: int = 5
    ):
        """
        Initialize time series detector
        
        Args:
            name: Detector name
            window_size: Days of history
            min_history: Minimum observations before predicting
            sensitivity: Sensitivity multiplier
            lookback_period: How many points to look back
        """
        super().__init__(name, window_size, min_history, sensitivity)
        self.lookback_period = lookback_period
        self.history = []
    
    def add_observation(self, value: float) -> None:
        """Add to history without predicting"""
        self.history.append(value)
        if len(self.history) > self.window_size * 96:  # 96 = 15-min windows per day
            self.history.pop(0)
        self.update(value)
