"""
Isolation Forest based anomaly detector.
Detects non-linear anomalies by isolating unusual points in feature space.
"""

import numpy as np
from typing import Dict, Optional
from sklearn.ensemble import IsolationForest
from .base_detector import BaseDetector, DetectionResult
import logging

logger = logging.getLogger(__name__)


class IsolationForestDetector(BaseDetector):
    """
    Isolation Forest anomaly detector
    
    Algorithm:
    - Isolates anomalies by random partitioning
    - Anomalies are closer to root (need fewer partitions to isolate)
    - Non-linear, works well with mixed distributions
    
    Advantages:
    - Handles non-linear anomalies
    - Robust to high-dimensional data
    - Fast training and prediction
    - No distribution assumptions
    
    Disadvantages:
    - Requires training data to establish baseline
    - May have false positives on rare but normal events
    - Less interpretable than Z-score
    """
    
    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 100,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0,
        random_state: int = 42
    ):
        """
        Initialize Isolation Forest detector
        
        Args:
            contamination: Expected proportion of anomalies (0.01-0.5)
            n_estimators: Number of trees to use
            window_size: Days of history
            min_history: Minimum observations
            sensitivity: Sensitivity multiplier (< 1.0 = less sensitive)
            random_state: For reproducibility
        """
        super().__init__("isolation_forest", window_size, min_history, sensitivity)
        
        # Adjust contamination based on sensitivity
        self.contamination = max(0.01, min(0.5, contamination / sensitivity))
        self.n_estimators = n_estimators
        self.random_state = random_state
        
        self.model = None
        self.offset = None  # Decision boundary
        self.history = []
    
    def fit(self, data: np.ndarray, **kwargs) -> None:
        """
        Train Isolation Forest on historical data
        
        Args:
            data: Historical data, shape (n_samples,) or (n_samples, n_features)
            **kwargs: Additional parameters
        """
        data = self._validate_data(data, min_samples=max(self.min_history, 10))
        
        # Convert 1D to 2D for sklearn
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        self.history = list(data[-self.window_size * 96:])
        
        # Train Isolation Forest
        try:
            self.model = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                random_state=self.random_state,
                n_jobs=-1,  # Parallel processing
                verbose=0
            )
            self.model.fit(data)
            
            # Get decision scores
            scores = self.model.score_samples(data)
            self.offset = self.model.offset_  # Decision threshold
            
            self.is_fitted = True
            self.n_observations = len(data)
            
            logger.info(
                f"Isolation Forest detector fitted: samples={len(data)}, "
                f"contamination={self.contamination:.3f}"
            )
        
        except Exception as e:
            logger.error(f"Failed to fit Isolation Forest: {e}")
            raise
    
    def predict(self, observation: float) -> DetectionResult:
        """
        Detect anomaly using Isolation Forest
        
        Args:
            observation: Current value(s)
        
        Returns:
            DetectionResult
        """
        self._check_fitted()
        
        # Format input
        if isinstance(observation, (int, float)):
            obs_array = np.array([[observation]])
        else:
            obs_array = np.asarray(observation).reshape(1, -1)
        
        # Get anomaly score and prediction
        score = self.model.score_samples(obs_array)[0]  # Negative for anomalies
        prediction = self.model.predict(obs_array)[0]  # -1 for anomaly, 1 for normal
        
        is_anomaly = (prediction == -1)
        
        # Convert score to confidence (0-1)
        # score_samples returns negative values; more negative = more anomalous.
        # Typical range: [-0.8, 0]. Normalize so extreme outliers reach >0.5.
        raw_conf = max(0.0, -score)  # 0 to ~0.8
        confidence = min(raw_conf * 1.5, 0.99)  # scale up: 0.4 raw -> 0.6 conf
        
        return DetectionResult(
            anomaly_detected=is_anomaly,
            confidence=confidence if is_anomaly else 0.0,
            score=float(score),
            threshold=0.0,  # Score = 0 is typically the boundary
            metadata={
                "if_score": float(score),
                "if_prediction": int(prediction),
                "observation": float(observation)
            }
        )
    
    def update(self, observation: float) -> None:
        """Update detector with new observation"""
        super().update(observation)
        
        # Periodically retrain on new data for concept drift
        if self.n_observations % (30 * 96) == 0:  # Every 30 days
            if len(self.history) >= self.min_history:
                self._retrain()
    
    def _retrain(self) -> None:
        """Retrain model on recent history with concept drift handling"""
        if len(self.history) < self.min_history:
            return
        
        data = np.array(self.history[-self.window_size * 96:])
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        try:
            # Retrain with slight perturbation for stability
            self.fit(data)
            logger.info(f"Isolation Forest retrained with {len(data)} samples")
        except Exception as e:
            logger.warning(f"Failed to retrain Isolation Forest: {e}")
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "detector": "isolation_forest",
            "contamination": float(self.contamination),
            "n_estimators": int(self.n_estimators),
            "offset": float(self.offset) if self.offset is not None else None,
            "observations": self.n_observations,
            "fitted": self.is_fitted
        }


class MultiVarIsolationForestDetector(BaseDetector):
    """
    Multi-variable Isolation Forest detector
    Detects anomalies in multivariate data
    """
    
    def __init__(
        self,
        n_features: int = 3,
        contamination: float = 0.05,
        n_estimators: int = 100,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0
    ):
        """
        Initialize multi-variable IF detector
        
        Args:
            n_features: Number of features
            contamination: Expected anomaly proportion
            n_estimators: Number of trees
            window_size: Days of history
            min_history: Minimum observations
            sensitivity: Sensitivity multiplier
        """
        super().__init__("multivar_isolation_forest", window_size, min_history, sensitivity)
        self.n_features = n_features
        self.contamination = max(0.01, min(0.5, contamination / sensitivity))
        self.n_estimators = n_estimators
        
        self.model = None
        self.history = []
        self.feature_names = ["reddit_volume", "google_trends", "twitter_volume"]
    
    def fit(self, data: np.ndarray, **kwargs) -> None:
        """
        Train multi-variable IF
        
        Args:
            data: Shape (n_samples, n_features)
        """
        data = self._validate_data(data, min_samples=max(self.min_history, 10))
        
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        if data.shape[1] != self.n_features:
            raise ValueError(
                f"Expected {self.n_features} features, got {data.shape[1]}"
            )
        
        self.history = [list(row) for row in data[-self.window_size * 96:]]
        
        try:
            self.model = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                random_state=42,
                n_jobs=-1
            )
            self.model.fit(data)
            
            self.is_fitted = True
            self.n_observations = len(data)
            
            logger.info(
                f"Multi-var Isolation Forest fitted: features={self.n_features}, "
                f"samples={len(data)}"
            )
        
        except Exception as e:
            logger.error(f"Failed to fit multi-var IF: {e}")
            raise
    
    def predict(self, observation: np.ndarray) -> DetectionResult:
        """
        Detect anomalies in multi-dimensional observation
        
        Args:
            observation: Current values, shape (n_features,)
        
        Returns:
            DetectionResult
        """
        self._check_fitted()
        
        observation = np.asarray(observation).reshape(1, -1)
        
        score = self.model.score_samples(observation)[0]
        prediction = self.model.predict(observation)[0]
        
        is_anomaly = (prediction == -1)
        confidence = max(0, min(1, -score / 2))
        
        return DetectionResult(
            anomaly_detected=is_anomaly,
            confidence=confidence if is_anomaly else 0.0,
            score=float(score),
            threshold=0.0,
            metadata={
                "if_score": float(score),
                "observations": {
                    self.feature_names[i]: float(observation[0, i])
                    for i in range(self.n_features)
                }
            }
        )
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "detector": "multivar_isolation_forest",
            "n_features": self.n_features,
            "feature_names": self.feature_names,
            "contamination": float(self.contamination),
            "n_estimators": int(self.n_estimators),
            "observations": self.n_observations,
            "fitted": self.is_fitted
        }

# clean architecture alignment
