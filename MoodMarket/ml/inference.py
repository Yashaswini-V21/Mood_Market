"""
Inference script for Informer model
Includes batch prediction, confidence intervals, and uncertainty quantification
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Tuple, Dict, List, Optional
from pathlib import Path
import logging
from model import Informer, InformerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InferenceEngine:
    """Inference engine for Informer model"""
    
    def __init__(
        self,
        model_path: str,
        device: Optional[torch.device] = None,
        quantize: bool = False
    ) -> None:
        """
        Initialize inference engine
        
        Args:
            model_path: Path to model checkpoint
            device: Device to run inference on
            quantize: Whether to use quantized model
        """
        if device is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.device = device
        logger.info(f"Using device: {device}")
        
        # Load model
        self.model, _ = Informer.load_checkpoint(model_path, device)
        self.model.eval()
        
        # Apply quantization if requested
        if quantize:
            logger.info("Applying int8 quantization...")
            self.model.quantize_int8()
            self.model.to(device)
        
        logger.info(f"✓ Model loaded from {model_path}")
        logger.info(f"✓ Model parameters: {self.model.count_parameters():,}")
    
    def predict_single(
        self,
        encoder_input: np.ndarray,
        decoder_input: np.ndarray,
        confidence_level: float = 0.95,
        n_samples_mc: int = 10
    ) -> Dict[str, np.ndarray]:
        """
        Single prediction with uncertainty quantification
        
        Args:
            encoder_input: Encoder input (seq_len, n_features)
            decoder_input: Decoder input (pred_len, n_features)
            confidence_level: Confidence level for intervals
            n_samples_mc: Number of MC samples for uncertainty
        
        Returns:
            Dictionary with predictions, uncertainties, and intervals
        """
        # Convert to tensors
        enc_input = torch.from_numpy(encoder_input).float().unsqueeze(0).to(self.device)
        dec_input = torch.from_numpy(decoder_input).float().unsqueeze(0).to(self.device)
        
        # Run inference
        with torch.no_grad():
            prediction, uncertainty, attention_weights = self.model(enc_input, dec_input)
        
        pred = prediction.cpu().numpy().squeeze()
        uncert = uncertainty.cpu().numpy().squeeze()
        
        # Compute confidence intervals using uncertainty
        z_score = self._get_z_score(confidence_level)
        margin = z_score * uncert
        
        lower_bound = np.clip(pred - margin, 0, 1)
        upper_bound = np.clip(pred + margin, 0, 1)
        
        return {
            'prediction': pred,
            'uncertainty': uncert,
            'confidence_level': confidence_level,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'attention_weights': attention_weights
        }
    
    def predict_batch(
        self,
        encoder_inputs: np.ndarray,
        decoder_inputs: np.ndarray,
        confidence_level: float = 0.95,
        batch_size: int = 32
    ) -> Dict[str, np.ndarray]:
        """
        Batch prediction with confidence intervals
        
        Args:
            encoder_inputs: Encoder inputs (n_samples, seq_len, n_features)
            decoder_inputs: Decoder inputs (n_samples, pred_len, n_features)
            confidence_level: Confidence level for intervals
            batch_size: Batch size for inference
        
        Returns:
            Dictionary with batch predictions and uncertainties
        """
        n_samples = len(encoder_inputs)
        
        predictions = []
        uncertainties = []
        lower_bounds = []
        upper_bounds = []
        
        logger.info(f"Running batch inference on {n_samples} samples...")
        
        for i in range(0, n_samples, batch_size):
            batch_end = min(i + batch_size, n_samples)
            
            enc_batch = torch.from_numpy(encoder_inputs[i:batch_end]).float().to(self.device)
            dec_batch = torch.from_numpy(decoder_inputs[i:batch_end]).float().to(self.device)
            
            with torch.no_grad():
                pred, uncert, _ = self.model(enc_batch, dec_batch)
            
            pred = pred.cpu().numpy()
            uncert = uncert.cpu().numpy()
            
            # Compute confidence intervals
            z_score = self._get_z_score(confidence_level)
            margin = z_score * uncert
            
            lower = np.clip(pred - margin, 0, 1)
            upper = np.clip(pred + margin, 0, 1)
            
            predictions.append(pred)
            uncertainties.append(uncert)
            lower_bounds.append(lower)
            upper_bounds.append(upper)
            
            if (i + batch_size) % (batch_size * 10) == 0:
                logger.info(f"  Processed {min(i + batch_size, n_samples)}/{n_samples}")
        
        return {
            'predictions': np.concatenate(predictions, axis=0),
            'uncertainties': np.concatenate(uncertainties, axis=0),
            'lower_bounds': np.concatenate(lower_bounds, axis=0),
            'upper_bounds': np.concatenate(upper_bounds, axis=0),
            'confidence_level': confidence_level
        }
    
    def predict_streaming(
        self,
        data_stream: List[np.ndarray],
        seq_len: int = 72,
        pred_len: int = 1,
        confidence_level: float = 0.95
    ) -> Dict[str, np.ndarray]:
        """
        Streaming prediction for real-time scenarios
        
        Args:
            data_stream: List of recent data points
            seq_len: Sequence length
            pred_len: Prediction length
            confidence_level: Confidence level for intervals
        
        Returns:
            Prediction dictionary
        """
        if len(data_stream) < seq_len:
            raise ValueError(f"Need at least {seq_len} data points, got {len(data_stream)}")
        
        # Use last seq_len points as encoder input
        encoder_input = np.array(data_stream[-seq_len:])
        # Decoder input: use last point repeated (or generate from pattern)
        decoder_input = np.tile(data_stream[-1], (pred_len, 1))
        
        result = self.predict_single(encoder_input, decoder_input, confidence_level)
        
        return result
    
    def get_attention_visualization(
        self,
        encoder_input: np.ndarray,
        decoder_input: np.ndarray,
        layer_idx: int = 0,
        head_idx: int = 0
    ) -> Dict[str, np.ndarray]:
        """
        Extract attention weights for explainability
        
        Args:
            encoder_input: Encoder input
            decoder_input: Decoder input
            layer_idx: Layer index
            head_idx: Head index
        
        Returns:
            Dictionary with attention weights
        """
        enc_input = torch.from_numpy(encoder_input).float().unsqueeze(0).to(self.device)
        dec_input = torch.from_numpy(decoder_input).float().unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            _, _, attention_weights = self.model(enc_input, dec_input)
        
        encoder_attn = attention_weights['encoder']
        decoder_self_attn = attention_weights['decoder_self']
        decoder_cross_attn = attention_weights['decoder_cross']
        
        return {
            'encoder_attention': encoder_attn[layer_idx][0, head_idx].cpu().numpy() if layer_idx < len(encoder_attn) else None,
            'decoder_self_attention': decoder_self_attn[layer_idx][0, head_idx].cpu().numpy() if layer_idx < len(decoder_self_attn) else None,
            'decoder_cross_attention': decoder_cross_attn[layer_idx][0, head_idx].cpu().numpy() if layer_idx < len(decoder_cross_attn) else None
        }
    
    def calibrate_uncertainty(
        self,
        encoder_inputs: np.ndarray,
        decoder_inputs: np.ndarray,
        targets: np.ndarray,
        num_bins: int = 10
    ) -> Dict[str, np.ndarray]:
        """
        Calibrate uncertainty estimates using validation data
        
        Args:
            encoder_inputs: Encoder inputs
            decoder_inputs: Decoder inputs
            targets: Target values
            num_bins: Number of bins for calibration
        
        Returns:
            Calibration statistics
        """
        logger.info("Calibrating uncertainty estimates...")
        
        batch_results = self.predict_batch(encoder_inputs, decoder_inputs)
        predictions = batch_results['predictions'].squeeze()
        uncertainties = batch_results['uncertainties'].squeeze()
        
        # Bin predictions by uncertainty
        uncertainty_bins = np.linspace(uncertainties.min(), uncertainties.max(), num_bins + 1)
        accuracies = []
        avg_uncertainties = []
        
        for i in range(num_bins):
            mask = (uncertainties >= uncertainty_bins[i]) & (uncertainties < uncertainty_bins[i + 1])
            
            if mask.sum() > 0:
                bin_predictions = predictions[mask]
                bin_targets = targets[mask]
                bin_uncertainties = uncertainties[mask]
                
                bin_accuracy = ((bin_predictions > 0.5) == (bin_targets > 0.5)).mean()
                accuracies.append(bin_accuracy)
                avg_uncertainties.append(bin_uncertainties.mean())
        
        return {
            'uncertainty_bins': uncertainty_bins,
            'accuracies_per_bin': np.array(accuracies),
            'avg_uncertainties_per_bin': np.array(avg_uncertainties),
            'calibration_metric': np.abs(np.array(accuracies) - np.array(avg_uncertainties)).mean()
        }
    
    def optimize_for_deployment(
        self,
        output_path: str,
        quantize: bool = True,
        prune: bool = False
    ) -> None:
        """
        Optimize model for deployment
        
        Args:
            output_path: Path to save optimized model
            quantize: Whether to quantize model
            prune: Whether to prune model
        """
        logger.info("Optimizing model for deployment...")
        
        model = self.model
        
        # Quantization
        if quantize:
            logger.info("Applying int8 quantization...")
            model.quantize_int8()
        
        # Pruning (structured)
        if prune:
            logger.info("Applying structured pruning...")
            for name, module in model.named_modules():
                if isinstance(module, nn.Linear):
                    torch.nn.utils.prune.l1_structured(
                        module, name='weight', amount=0.3
                    )
                    torch.nn.utils.prune.remove(module, name='weight')
        
        # Save optimized model
        torch.save(model.state_dict(), output_path)
        logger.info(f"✓ Saved optimized model to {output_path}")
        logger.info(f"✓ Model size: {Path(output_path).stat().st_size / (1024**2):.2f} MB")
    
    @staticmethod
    def _get_z_score(confidence_level: float) -> float:
        """
        Get z-score for confidence level
        
        Args:
            confidence_level: Confidence level (e.g., 0.95)
        
        Returns:
            Z-score
        """
        from scipy import stats
        alpha = 1 - confidence_level
        return stats.norm.ppf(1 - alpha / 2)


class RealTimePredictor:
    """Real-time predictor for streaming data"""
    
    def __init__(
        self,
        model_path: str,
        seq_len: int = 72,
        pred_len: int = 1,
        device: Optional[torch.device] = None
    ) -> None:
        """
        Initialize real-time predictor
        
        Args:
            model_path: Path to model
            seq_len: Sequence length
            pred_len: Prediction length
            device: Device to use
        """
        self.inference_engine = InferenceEngine(model_path, device)
        self.seq_len = seq_len
        self.pred_len = pred_len
        self.data_buffer = []
    
    def add_data_point(self, data_point: np.ndarray) -> Optional[Dict[str, np.ndarray]]:
        """
        Add new data point and get prediction if enough data
        
        Args:
            data_point: New data point (n_features,)
        
        Returns:
            Prediction if enough data, None otherwise
        """
        self.data_buffer.append(data_point)
        
        # Keep buffer at manageable size
        if len(self.data_buffer) > self.seq_len * 2:
            self.data_buffer.pop(0)
        
        # Generate prediction if enough data
        if len(self.data_buffer) >= self.seq_len:
            prediction = self.inference_engine.predict_streaming(
                self.data_buffer,
                self.seq_len,
                self.pred_len
            )
            return prediction
        
        return None
    
    def get_latest_prediction(
        self,
        confidence_level: float = 0.95
    ) -> Optional[Dict[str, np.ndarray]]:
        """
        Get latest prediction from buffer
        
        Args:
            confidence_level: Confidence level
        
        Returns:
            Latest prediction or None
        """
        if len(self.data_buffer) >= self.seq_len:
            return self.inference_engine.predict_streaming(
                self.data_buffer,
                self.seq_len,
                self.pred_len,
                confidence_level
            )
        return None


def example_usage() -> None:
    """Example usage of inference engine"""
    
    # Initialize inference engine
    # Assuming checkpoint exists at './checkpoints/best_model.pt'
    
    try:
        engine = InferenceEngine(
            model_path='./checkpoints/best_model.pt',
            quantize=False
        )
        
        # Generate example data
        encoder_input = np.random.randn(72, 8)
        decoder_input = np.random.randn(1, 8)
        
        # Single prediction
        result = engine.predict_single(encoder_input, decoder_input)
        print(f"Prediction: {result['prediction']:.4f}")
        print(f"Uncertainty: {result['uncertainty']:.6f}")
        print(f"Confidence Interval: [{result['lower_bound']:.4f}, {result['upper_bound']:.4f}]")
        
        # Batch prediction
        encoder_batch = np.random.randn(100, 72, 8)
        decoder_batch = np.random.randn(100, 1, 8)
        
        batch_results = engine.predict_batch(encoder_batch, decoder_batch)
        print(f"\nBatch predictions shape: {batch_results['predictions'].shape}")
        print(f"Mean prediction: {batch_results['predictions'].mean():.4f}")
        
        # Real-time streaming
        predictor = RealTimePredictor('./checkpoints/best_model.pt')
        
        # Simulate data stream
        for i in range(100):
            new_data = np.random.randn(8)
            prediction = predictor.add_data_point(new_data)
            
            if prediction is not None and i % 10 == 0:
                print(f"\nStreaming prediction at step {i}:")
                print(f"  Prediction: {prediction['prediction']:.4f}")
                print(f"  Interval: [{prediction['lower_bound']:.4f}, {prediction['upper_bound']:.4f}]")
        
        logger.info("✓ Inference examples completed")
        
    except FileNotFoundError:
        logger.error("Model checkpoint not found. Train model first using train.py")


if __name__ == "__main__":
    example_usage()
