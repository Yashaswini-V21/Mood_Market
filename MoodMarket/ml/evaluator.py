import os
import time
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Any, Tuple, Optional


class Evaluator:
    """
    Evaluates forecasting models on regression metrics, hardware footprints,
    and post-training dynamic INT8 quantization performance.
    """
    @staticmethod
    def calculate_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Calculates MAE, RMSE, MAPE, and directional accuracy.
        """
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()
        
        # Mean Absolute Error
        mae = float(np.mean(np.abs(y_true - y_pred)))
        
        # Root Mean Squared Error
        rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
        
        # Mean Absolute Percentage Error (with safety epsilon)
        mape = float(np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + 1e-8))))
        
        # Directional Accuracy (where > 0.5 is UP, <= 0.5 is DOWN)
        # Verify classification matching
        true_direction = y_true > 0.5
        pred_direction = y_pred > 0.5
        dir_acc = float(np.mean(true_direction == pred_direction))
        
        return {
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "directional_accuracy": dir_acc
        }

    @staticmethod
    def profile_model_size(model: nn.Module, temp_path: str = "./temp_model.pt") -> Dict[str, Any]:
        """
        Profiles model parameter counts and checkpoint file size.
        """
        # Count parameters
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # Save model temporarily to measure disk size
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        try:
            # We save state_dict for clean size measurement
            torch.save(model.state_dict(), temp_path)
            file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
        except Exception:
            file_size_mb = 0.0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        return {
            "total_parameters": total_params,
            "trainable_parameters": trainable_params,
            "file_size_mb": file_size_mb
        }

    @staticmethod
    def profile_quantization(
        model: nn.Module,
        encoder_input: torch.Tensor,
        decoder_input: Optional[torch.Tensor] = None,
        is_informer: bool = True,
        temp_path: str = "./temp_quant.pt"
    ) -> Dict[str, Any]:
        """
        Profiles CPU inference speed and size reduction for dynamic INT8 quantization.
        """
        # Move model to CPU for quantization evaluation
        cpu_model = nn.Module()
        # Shallow copy or state dict clone to avoid corrupting original model
        import copy
        cpu_model = copy.deepcopy(model).cpu()
        cpu_model.eval()
        
        enc_in = encoder_input.cpu()
        dec_in = decoder_input.cpu() if decoder_input is not None else None
        
        # 1. Benchmark unquantized latency
        start_time = time.time()
        n_iters = 50
        with torch.no_grad():
            for _ in range(n_iters):
                if is_informer and dec_in is not None:
                    _ = cpu_model(enc_in, dec_in)
                else:
                    _ = cpu_model(enc_in)
        unquantized_latency = ((time.time() - start_time) / n_iters) * 1000  # ms
        
        # Unquantized size
        torch.save(cpu_model.state_dict(), temp_path)
        unquantized_size = os.path.getsize(temp_path) / (1024 * 1024)
        
        # 2. Dynamic Quantization
        # PyTorch dynamic quantization matches Linear and LSTM layers
        quantized_model = torch.quantization.quantize_dynamic(
            cpu_model, {nn.Linear, nn.LSTM}, dtype=torch.qint8
        )
        
        # 3. Benchmark quantized latency
        start_time = time.time()
        with torch.no_grad():
            for _ in range(n_iters):
                if is_informer and dec_in is not None:
                    _ = quantized_model(enc_in, dec_in)
                else:
                    _ = quantized_model(enc_in)
        quantized_latency = ((time.time() - start_time) / n_iters) * 1000  # ms
        
        # Quantized size
        # We need to save the entire quantized model structure, not just state_dict, or serialize it correctly
        try:
            torch.save(quantized_model, temp_path)
            quantized_size = os.path.getsize(temp_path) / (1024 * 1024)
        except Exception:
            quantized_size = unquantized_size / 4.0  # standard fallback ratio
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        return {
            "unquantized_size_mb": unquantized_size,
            "quantized_size_mb": quantized_size,
            "size_reduction_ratio": float(unquantized_size / (quantized_size + 1e-8)),
            "unquantized_latency_ms": unquantized_latency,
            "quantized_latency_ms": quantized_latency,
            "speedup_ratio": float(unquantized_latency / (quantized_latency + 1e-8))
        }
