"""
Autoencoder-based anomaly detector.
Learns normal patterns and flags deviations from them.
"""

import numpy as np
from typing import Dict, List, Tuple
import logging
from .base_detector import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)

# Simple autoencoder implementation (no heavy dependencies)
class SimpleAutoencoder:
    """
    Simple autoencoder for anomaly detection
    Learns to reconstruct normal data, flags high reconstruction error
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 16,
        learning_rate: float = 0.001,
        epochs: int = 50,
        batch_size: int = 32
    ):
        """
        Initialize autoencoder
        
        Args:
            input_size: Input dimension
            hidden_size: Size of hidden layer
            learning_rate: Learning rate for gradient descent
            epochs: Training epochs
            batch_size: Batch size
        """
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        
        # Initialize weights randomly
        self.encoder_w = np.random.randn(input_size, hidden_size) * 0.01
        self.encoder_b = np.zeros((1, hidden_size))
        
        self.decoder_w = np.random.randn(hidden_size, input_size) * 0.01
        self.decoder_b = np.zeros((1, input_size))
        
        self.is_trained = False
        self.mean = None
        self.std = None
    
    def _relu(self, x: np.ndarray) -> np.ndarray:
        """ReLU activation"""
        return np.maximum(0, x)
    
    def _relu_derivative(self, x: np.ndarray) -> np.ndarray:
        """ReLU derivative"""
        return (x > 0).astype(float)
    
    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        """Sigmoid activation"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """Normalize data"""
        self.mean = np.mean(data, axis=0)
        self.std = np.std(data, axis=0)
        self.std[self.std == 0] = 1
        return (data - self.mean) / self.std
    
    def _denormalize(self, data: np.ndarray) -> np.ndarray:
        """Denormalize data"""
        return data * self.std + self.mean
    
    def encode(self, x: np.ndarray) -> np.ndarray:
        """Encode input to latent space"""
        z = np.dot(x, self.encoder_w) + self.encoder_b
        return self._relu(z)
    
    def decode(self, z: np.ndarray) -> np.ndarray:
        """Decode from latent space"""
        return np.dot(z, self.decoder_w) + self.decoder_b
    
    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Forward pass"""
        z = self.encode(x)
        reconstruction = self.decode(z)
        return reconstruction, z, x
    
    def train(self, data: np.ndarray) -> List[float]:
        """
        Train autoencoder
        
        Args:
            data: Training data, shape (n_samples, input_size)
        
        Returns:
            List of loss values per epoch
        """
        # Normalize data
        data = self._normalize(data)
        
        losses = []
        
        for epoch in range(self.epochs):
            epoch_loss = 0
            n_batches = 0
            
            # Shuffle data
            indices = np.random.permutation(len(data))
            
            for i in range(0, len(data), self.batch_size):
                batch_indices = indices[i:i + self.batch_size]
                x_batch = data[batch_indices]
                
                # Forward pass
                reconstruction, z, x = self.forward(x_batch)
                
                # Reconstruction loss
                loss = np.mean((reconstruction - x) ** 2)
                epoch_loss += loss
                n_batches += 1
                
                # Backward pass (simplified SGD)
                delta_out = (reconstruction - x) / len(x_batch)
                
                # Update decoder
                dw_decoder = np.dot(z.T, delta_out)
                db_decoder = np.sum(delta_out, axis=0, keepdims=True)
                
                self.decoder_w -= self.learning_rate * dw_decoder
                self.decoder_b -= self.learning_rate * db_decoder
                
                # Backprop to encoder
                delta_z = np.dot(delta_out, self.decoder_w.T)
                delta_z *= self._relu_derivative(np.dot(x_batch, self.encoder_w) + self.encoder_b)
                
                # Update encoder
                dw_encoder = np.dot(x_batch.T, delta_z)
                db_encoder = np.sum(delta_z, axis=0, keepdims=True)
                
                self.encoder_w -= self.learning_rate * dw_encoder
                self.encoder_b -= self.learning_rate * db_encoder
            
            avg_loss = epoch_loss / n_batches if n_batches > 0 else 0
            losses.append(avg_loss)
            
            if (epoch + 1) % 10 == 0:
                logger.debug(f"Autoencoder epoch {epoch + 1}/{self.epochs}, loss={avg_loss:.6f}")
        
        self.is_trained = True
        return losses
    
    def reconstruct(self, x: np.ndarray) -> np.ndarray:
        """Reconstruct input"""
        x_norm = (x - self.mean) / self.std
        reconstruction = self.forward(x_norm)[0]
        return self._denormalize(reconstruction)
    
    def reconstruction_error(self, x: np.ndarray) -> np.ndarray:
        """
        Compute reconstruction error
        
        Args:
            x: Input data
        
        Returns:
            Error per sample
        """
        reconstruction = self.reconstruct(x)
        error = np.mean((reconstruction - x) ** 2, axis=1 if x.ndim > 1 else 0)
        return error


class AutoencoderDetector(BaseDetector):
    """
    Autoencoder-based anomaly detector
    
    Algorithm:
    - Trains autoencoder on normal data
    - Flags high reconstruction errors as anomalies
    - Learns non-linear patterns
    
    Advantages:
    - Captures complex patterns
    - Works with sequences
    - Adaptable to new patterns
    
    Disadvantages:
    - Slower training
    - Requires more data
    - Less interpretable
    """
    
    def __init__(
        self,
        hidden_size: int = 16,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0,
        threshold_percentile: float = 95.0
    ):
        """
        Initialize autoencoder detector
        
        Args:
            hidden_size: Hidden layer dimension
            window_size: Days of history
            min_history: Minimum observations
            sensitivity: Sensitivity multiplier
            threshold_percentile: Percentile for anomaly threshold
        """
        super().__init__("autoencoder", window_size, min_history, sensitivity)
        self.hidden_size = hidden_size
        self.threshold_percentile = threshold_percentile * (1 + (1 - sensitivity))
        
        self.model = SimpleAutoencoder(
            input_size=1,
            hidden_size=hidden_size,
            learning_rate=0.01,
            epochs=50,
            batch_size=32
        )
        
        self.history = []
        self.error_threshold = None
        self.reconstruction_errors = []
    
    def fit(self, data: np.ndarray, **kwargs) -> None:
        """
        Train autoencoder on historical data
        
        Args:
            data: Historical data, shape (n_samples,)
            **kwargs: Additional parameters
        """
        data = self._validate_data(data, min_samples=max(self.min_history, 10))
        
        self.history = list(data[-self.window_size * 96:])
        
        # Reshape for autoencoder: (n_samples, 1)
        data_reshaped = data.reshape(-1, 1)
        
        # Train
        logger.info(f"Training autoencoder on {len(data)} samples...")
        losses = self.model.train(data_reshaped)
        logger.info(f"Autoencoder training complete. Final loss: {losses[-1]:.6f}")
        
        # Calculate reconstruction errors on training data
        self.reconstruction_errors = self.model.reconstruction_error(data_reshaped)
        
        # Set threshold at percentile
        self.error_threshold = np.percentile(
            self.reconstruction_errors,
            self.threshold_percentile
        )
        
        self.is_fitted = True
        self.n_observations = len(data)
        
        logger.info(
            f"Autoencoder detector fitted: threshold={self.error_threshold:.6f}, "
            f"percentile={self.threshold_percentile:.1f}"
        )
    
    def predict(self, observation: float) -> DetectionResult:
        """
        Detect anomaly using reconstruction error
        
        Args:
            observation: Current value
        
        Returns:
            DetectionResult
        """
        self._check_fitted()
        
        # Compute reconstruction error
        obs_array = np.array([[observation]])
        error = self.model.reconstruction_error(obs_array)[0]
        
        # Check if anomaly
        is_anomaly = error > self.error_threshold
        
        # Confidence based on error ratio
        confidence = min(error / self.error_threshold, 1.0) if self.error_threshold > 0 else 0.0
        
        self.history.append(observation)
        if len(self.history) > self.window_size * 96:
            self.history.pop(0)
        
        return DetectionResult(
            anomaly_detected=is_anomaly,
            confidence=confidence if is_anomaly else 0.0,
            score=float(error),
            threshold=float(self.error_threshold),
            metadata={
                "reconstruction_error": float(error),
                "threshold": float(self.error_threshold),
                "error_ratio": float(error / self.error_threshold if self.error_threshold > 0 else 0)
            }
        )
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "detector": "autoencoder",
            "hidden_size": int(self.hidden_size),
            "error_threshold": float(self.error_threshold) if self.error_threshold else None,
            "threshold_percentile": float(self.threshold_percentile),
            "is_trained": self.model.is_trained,
            "observations": self.n_observations,
            "fitted": self.is_fitted
        }


class MultiVarAutoencoderDetector(BaseDetector):
    """
    Multi-variable autoencoder detector
    Learns patterns in 3 social media metrics
    """
    
    def __init__(
        self,
        n_features: int = 3,
        hidden_size: int = 16,
        window_size: int = 30,
        min_history: int = 10,
        sensitivity: float = 1.0,
        threshold_percentile: float = 95.0
    ):
        """
        Initialize multi-variable autoencoder
        
        Args:
            n_features: Number of features (3 for Reddit/Google/Twitter)
            hidden_size: Hidden layer size
            window_size: Days of history
            min_history: Minimum observations
            sensitivity: Sensitivity multiplier
            threshold_percentile: Error percentile for threshold
        """
        super().__init__("multivar_autoencoder", window_size, min_history, sensitivity)
        self.n_features = n_features
        self.hidden_size = hidden_size
        self.threshold_percentile = threshold_percentile * (1 + (1 - sensitivity))
        
        self.model = SimpleAutoencoder(
            input_size=n_features,
            hidden_size=hidden_size,
            learning_rate=0.01,
            epochs=50,
            batch_size=32
        )
        
        self.history = []
        self.error_threshold = None
        self.feature_names = ["reddit_volume", "google_trends", "twitter_volume"]
    
    def fit(self, data: np.ndarray, **kwargs) -> None:
        """
        Train on multi-variable data
        
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
        
        # Train
        logger.info(f"Training multi-var autoencoder on {len(data)} samples...")
        self.model.train(data)
        
        # Calculate errors
        errors = self.model.reconstruction_error(data)
        self.error_threshold = np.percentile(errors, self.threshold_percentile)
        
        self.is_fitted = True
        self.n_observations = len(data)
        
        logger.info(f"Multi-var autoencoder fitted: threshold={self.error_threshold:.6f}")
    
    def predict(self, observation: np.ndarray) -> DetectionResult:
        """Detect anomalies in multi-variable data"""
        self._check_fitted()
        
        observation = np.asarray(observation).reshape(1, -1)
        error = self.model.reconstruction_error(observation)[0]
        
        is_anomaly = error > self.error_threshold
        confidence = min(error / self.error_threshold, 1.0) if self.error_threshold > 0 else 0.0
        
        return DetectionResult(
            anomaly_detected=is_anomaly,
            confidence=confidence if is_anomaly else 0.0,
            score=float(error),
            threshold=float(self.error_threshold),
            metadata={
                "reconstruction_error": float(error),
                "observations": {
                    self.feature_names[i]: float(observation[0, i])
                    for i in range(self.n_features)
                }
            }
        )
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "detector": "multivar_autoencoder",
            "n_features": self.n_features,
            "feature_names": self.feature_names,
            "hidden_size": int(self.hidden_size),
            "error_threshold": float(self.error_threshold) if self.error_threshold else None,
            "threshold_percentile": float(self.threshold_percentile),
            "observations": self.n_observations,
            "fitted": self.is_fitted
        }
