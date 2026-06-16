"""Detectors module - Anomaly detection algorithms for Hype Storm detection"""

from .base_detector import BaseDetector, MultiVariateDetector, TimeSeriesDetector, DetectionResult
from .zscore_detector import ZScoreDetector, MultiVarZScoreDetector
from .isolation_forest_detector import IsolationForestDetector, MultiVarIsolationForestDetector
from .autoencoder_detector import AutoencoderDetector, MultiVarAutoencoderDetector
from .ewma_detector import EWMADetector, AdaptiveEWMADetector

__all__ = [
    "BaseDetector",
    "MultiVariateDetector",
    "TimeSeriesDetector",
    "DetectionResult",
    "ZScoreDetector",
    "MultiVarZScoreDetector",
    "IsolationForestDetector",
    "MultiVarIsolationForestDetector",
    "AutoencoderDetector",
    "MultiVarAutoencoderDetector",
    "EWMADetector",
    "AdaptiveEWMADetector",
]

# clean architecture alignment
