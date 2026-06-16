"""
EWMA (Exponentially Weighted Moving Average) volatility spike detector.
Detects sudden increases in volatility/variance.
"""

import numpy as np
from typing import Dict, List
from .base_detector import BaseDetector, DetectionResult
import logging

logger = logging.getLogger(__name__)


class EWMADetector(BaseDetector):
    """
    EWMA-based volatility spike detector
    
    Algorithm:
    - Tracks EWMA of volatility
    - Flags when volatility > EWMA + threshold
    - Fast and efficient
    
    Advantages:
    - Fast computation
    - Captures volatility spikes
    - Adaptive baseline
    - Good for time series
    
    Disadvantages:
    - Sensitive to sudden level changes
    - Requires tuning
    - May lag in response
    """
    
    def __init__(
        self,
        alpha: float = 0.2,
        spike_multiplier: float = 2.0,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0,
        lookback: int = 5
    ):
        """
        Initialize EWMA detector
        
        Args:
            alpha: EWMA smoothing factor (0-1), higher = more responsive
            spike_multiplier: Threshold for spike (volatility > ewma_vol * multiplier)
            window_size: Days of history
            min_history: Minimum observations
            sensitivity: Sensitivity multiplier
            lookback: Periods to look back for volatility
        """
        super().__init__("ewma", window_size, min_history, sensitivity)
        
        # Adjust sensitivity
        self.alpha = min(1.0, alpha * sensitivity)
        self.spike_multiplier = spike_multiplier / sensitivity  # Lower = more sensitive
        self.lookback = lookback
        
        # State
        self.history = []
        self.volatility_history = []
        self.ewma_volatility = None
    
    def fit(self, data: np.ndarray, **kwargs) -> None:
        """
        Initialize on historical data
        
        Args:
            data: Historical volume data
        """
        data = self._validate_data(data, min_samples=max(self.min_history, 5))
        
        self.history = list(data[-self.window_size * 96:])
        
        # Calculate initial volatility
        self._update_volatility()
        
        self.is_fitted = True
        self.n_observations = len(data)
        
        logger.info(
            f"EWMA detector fitted: alpha={self.alpha:.3f}, "
            f"spike_multiplier={self.spike_multiplier:.2f}"
        )
    
    def predict(self, observation: float) -> DetectionResult:
        """
        Detect volatility spike
        
        Args:
            observation: Current value
        
        Returns:
            DetectionResult
        """
        self._check_fitted()
        
        # Add to history
        self.history.append(observation)
        if len(self.history) > self.window_size * 96:
            self.history.pop(0)
        
        # Calculate current volatility
        if len(self.history) >= self.lookback + 1:
            recent_values = self.history[-(self.lookback + 1):]
            current_volatility = np.std(recent_values)
        else:
            current_volatility = 0.0
        
        self.volatility_history.append(current_volatility)
        if len(self.volatility_history) > self.window_size * 96:
            self.volatility_history.pop(0)
        
        # Update EWMA
        if self.ewma_volatility is None:
            self.ewma_volatility = current_volatility
        else:
            self.ewma_volatility = (
                self.alpha * current_volatility +
                (1 - self.alpha) * self.ewma_volatility
            )
        
        # Check for spike
        if self.ewma_volatility > 0:
            volatility_ratio = current_volatility / self.ewma_volatility
            is_spike = volatility_ratio > self.spike_multiplier
        else:
            is_spike = False
            volatility_ratio = 0.0
        
        # Confidence
        if is_spike:
            confidence = min((volatility_ratio - self.spike_multiplier) / self.spike_multiplier, 1.0)
        else:
            confidence = 0.0
        
        return DetectionResult(
            anomaly_detected=is_spike,
            confidence=confidence,
            score=float(volatility_ratio),
            threshold=float(self.spike_multiplier),
            metadata={
                "current_volatility": float(current_volatility),
                "ewma_volatility": float(self.ewma_volatility),
                "volatility_ratio": float(volatility_ratio),
                "observation": float(observation)
            }
        )
    
    def _update_volatility(self) -> None:
        """Recalculate volatility from history"""
        if len(self.history) >= 2:
            self.ewma_volatility = np.std(self.history)
        else:
            self.ewma_volatility = 0.0
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "detector": "ewma",
            "alpha": float(self.alpha),
            "spike_multiplier": float(self.spike_multiplier),
            "lookback": int(self.lookback),
            "ewma_volatility": float(self.ewma_volatility) if self.ewma_volatility else None,
            "observations": self.n_observations,
            "fitted": self.is_fitted
        }


class AdaptiveEWMADetector(BaseDetector):
    """
    Adaptive EWMA detector that adjusts parameters based on regime
    
    Features:
    - Detects market regime (normal, high_vol, low_vol)
    - Adapts thresholds accordingly
    - More robust to changing conditions
    """
    
    def __init__(
        self,
        alpha: float = 0.2,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0,
        lookback: int = 5,
        regime_window: int = 240  # 4 hours at 15-min intervals
    ):
        """
        Initialize adaptive EWMA detector
        
        Args:
            alpha: Base EWMA alpha
            window_size: Days of history
            min_history: Minimum observations
            sensitivity: Sensitivity multiplier
            lookback: Lookback period for volatility
            regime_window: Window for regime detection (96 = 1 day)
        """
        super().__init__("adaptive_ewma", window_size, min_history, sensitivity)
        self.alpha = min(1.0, alpha * sensitivity)
        self.lookback = lookback
        self.regime_window = regime_window
        
        # State
        self.history = []
        self.volatility_history = []
        self.ewma_volatility = None
        self.regime = "normal"  # normal, low_vol, high_vol
        
        # Thresholds per regime
        self.spike_thresholds = {
            "low_vol": 3.0,
            "normal": 2.0,
            "high_vol": 1.5
        }
    
    def fit(self, data: np.ndarray, **kwargs) -> None:
        """Initialize on historical data"""
        data = self._validate_data(data, min_samples=max(self.min_history, 20))
        
        self.history = list(data[-self.window_size * 96:])
        self._update_volatility()
        self._detect_regime()
        
        self.is_fitted = True
        self.n_observations = len(data)
        
        logger.info(f"Adaptive EWMA detector fitted: regime={self.regime}")
    
    def predict(self, observation: float) -> DetectionResult:
        """Detect volatility spike with adaptive thresholds"""
        self._check_fitted()
        
        # Add to history
        self.history.append(observation)
        if len(self.history) > self.window_size * 96:
            self.history.pop(0)
        
        # Update regime every 96 observations (daily)
        if self.n_observations % 96 == 0:
            self._detect_regime()
        
        # Calculate current volatility
        if len(self.history) >= self.lookback + 1:
            recent_values = self.history[-(self.lookback + 1):]
            current_volatility = np.std(recent_values)
        else:
            current_volatility = 0.0
        
        self.volatility_history.append(current_volatility)
        
        # Update EWMA
        if self.ewma_volatility is None:
            self.ewma_volatility = current_volatility
        else:
            self.ewma_volatility = (
                self.alpha * current_volatility +
                (1 - self.alpha) * self.ewma_volatility
            )
        
        # Get adaptive threshold
        threshold = self.spike_thresholds.get(self.regime, 2.0)
        
        # Check for spike
        if self.ewma_volatility > 0:
            volatility_ratio = current_volatility / self.ewma_volatility
            is_spike = volatility_ratio > threshold
        else:
            is_spike = False
            volatility_ratio = 0.0
        
        # Confidence
        if is_spike:
            confidence = min((volatility_ratio - threshold) / threshold, 1.0)
        else:
            confidence = 0.0
        
        self.n_observations += 1
        
        return DetectionResult(
            anomaly_detected=is_spike,
            confidence=confidence,
            score=float(volatility_ratio),
            threshold=float(threshold),
            metadata={
                "current_volatility": float(current_volatility),
                "ewma_volatility": float(self.ewma_volatility),
                "volatility_ratio": float(volatility_ratio),
                "regime": self.regime,
                "adaptive_threshold": float(threshold)
            }
        )
    
    def _detect_regime(self) -> None:
        """Detect current volatility regime"""
        if len(self.history) < self.regime_window:
            return
        
        recent_vol = np.std(self.history[-self.regime_window:])
        baseline_vol = np.std(self.history[:-self.regime_window])
        
        if baseline_vol > 0:
            vol_ratio = recent_vol / baseline_vol
            
            if vol_ratio > 1.5:
                self.regime = "high_vol"
            elif vol_ratio < 0.7:
                self.regime = "low_vol"
            else:
                self.regime = "normal"
        else:
            self.regime = "normal"
        
        logger.debug(f"Regime detected: {self.regime}")
    
    def _update_volatility(self) -> None:
        """Recalculate EWMA volatility"""
        if len(self.history) >= 2:
            self.ewma_volatility = np.std(self.history)
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "detector": "adaptive_ewma",
            "alpha": float(self.alpha),
            "lookback": int(self.lookback),
            "regime": self.regime,
            "spike_thresholds": {k: float(v) for k, v in self.spike_thresholds.items()},
            "ewma_volatility": float(self.ewma_volatility) if self.ewma_volatility else None,
            "observations": self.n_observations,
            "fitted": self.is_fitted
        }

# clean architecture alignment
