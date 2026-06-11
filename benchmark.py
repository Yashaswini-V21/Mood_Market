import os
import time
import json
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
import logging
from pathlib import Path

from model import Informer, InformerConfig
from data_loader import create_walk_forward_dataloaders, preprocess_data, generate_synthetic_3y_data
from evaluator import Evaluator
from backtester import Backtester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("benchmark")


class LSTMModel(nn.Module):
    """LSTM baseline model for comparison"""
    def __init__(
        self,
        input_size: int = 8,
        hidden_size: int = 256,
        num_layers: int = 2,
        dropout: float = 0.1,
        output_size: int = 1
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True
        )
        self.output_layer = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.GELU(),
            nn.Linear(hidden_size // 2, output_size + 1)  # +1 for uncertainty
        )
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        lstm_out, _ = self.lstm(x)
        last_output = lstm_out[:, -1, :]
        logits = self.output_layer(last_output)
        
        prediction = torch.sigmoid(logits[..., :1])
        uncertainty = torch.nn.functional.softplus(logits[..., 1:])
        return prediction, uncertainty
    
    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def run_latency_benchmark(
    models: Dict[str, nn.Module],
    encoder_input: torch.Tensor,
    decoder_input: torch.Tensor,
    n_iterations: int = 1000,
    warm_up: int = 50,
    device: torch.device = torch.device("cpu")
) -> Dict[str, Dict[str, float]]:
    """
    Profiles inference latency distribution (P50, P95, P99) and throughput.
    """
    logger.info(f"Running latency benchmark on {device} ({n_iterations} iterations)...")
    results = {}
    
    for name, model in models.items():
        model.to(device)
        model.eval()
        
        enc_in = encoder_input.to(device)
        dec_in = decoder_input.to(device)
        
        # Warmup
        with torch.no_grad():
            for _ in range(warm_up):
                if name == "LSTM":
                    _ = model(enc_in)
                else:
                    _ = model(enc_in, dec_in)
                    
        # Latency collection
        latencies = []
        with torch.no_grad():
            for _ in range(n_iterations):
                start = time.perf_counter()
                if name == "LSTM":
                    _ = model(enc_in)
                else:
                    _ = model(enc_in, dec_in)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)  # to ms
                
        latencies = np.array(latencies)
        p50 = float(np.percentile(latencies, 50))
        p95 = float(np.percentile(latencies, 95))
        p99 = float(np.percentile(latencies, 99))
        mean_latency = float(np.mean(latencies))
        
        total_time = np.sum(latencies) / 1000.0  # seconds
        throughput = (n_iterations * enc_in.size(0)) / total_time  # samples/sec
        
        results[name] = {
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
            "mean_latency_ms": mean_latency,
            "throughput_samples_per_sec": throughput
        }
        
        logger.info(f"{name} Latency: P50={p50:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms | Throughput={throughput:.1f} samples/s")
        
    return results


def run_evaluation_benchmark(
    models: Dict[str, nn.Module],
    test_loader: torch.utils.data.DataLoader,
    raw_close_prices: np.ndarray,
    device: torch.device
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Evaluates regression accuracy and backtested trading performance.
    """
    logger.info("Running regression and backtesting benchmark...")
    accuracy_results = {}
    backtest_results = {}
    
    # Setup backtester
    backtester = Backtester()
    
    for name, model in models.items():
        model.to(device)
        model.eval()
        
        all_preds = []
        all_targets = []
        
        with torch.no_grad():
            for enc_in, dec_in, target in test_loader:
                enc_in = enc_in.to(device)
                target = target.to(device)
                
                if name == "LSTM":
                    pred, _ = model(enc_in)
                else:
                    dec_in = dec_in.to(device)
                    pred, _, _ = model(enc_in, dec_in)
                    
                all_preds.append(pred.squeeze().cpu().numpy())
                all_targets.append(target.squeeze().cpu().numpy())
                
        preds = np.concatenate(all_preds).flatten()
        targets = np.concatenate(all_targets).flatten()
        
        # Calculate Regression Metrics
        reg_metrics = Evaluator.calculate_regression_metrics(targets, preds)
        accuracy_results[name] = reg_metrics
        
        # Run Backtest Simulation
        # Close prices length matches predictions + 1
        # The raw close prices in the test set correspond to test sequence steps
        # We align the close prices sequence for the predictions
        test_close_prices = raw_close_prices[-len(preds) - 1:]
        backtest = backtester.simulate(preds, test_close_prices, strategy_type="long_short")
        
        backtest_results[name] = {
            "total_return": backtest["total_return"],
            "sharpe_ratio": backtest["sharpe_ratio"],
            "max_drawdown": backtest["max_drawdown"],
            "win_rate": backtest["win_rate"],
            "equity_curve": backtest["equity_curve"]
        }
        
        logger.info(
            f"{name} Metrics: MAE={reg_metrics['mae']:.4f}, DirAcc={reg_metrics['directional_accuracy']:.4f} | "
            f"Trading Return={backtest['total_return']*100:.1f}%, Sharpe={backtest['sharpe_ratio']:.2f}, MaxDD={backtest['max_drawdown']*100:.1f}%"
        )
        
    return accuracy_results, backtest_results


def run_full_comparison():
    """Main benchmark execution flow."""
    os.makedirs("results", exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Running comparisons on device: {device}")
    
    # 1. Load Data
    df = generate_synthetic_3y_data(seed=42)
    data, _ = preprocess_data(df)
    
    train_loader, val_loader, test_loader, _ = create_walk_forward_dataloaders(
        data=data,
        seq_len=72,
        pred_len=1,
        train_ratio=0.65,
        val_ratio=0.15,
        batch_size=64
    )
    
    raw_close_prices = df["close"].values
    
    # 2. Instantiate/Load Models
    # Informer Config
    informer_cfg = InformerConfig(
        seq_len=72,
        pred_len=1,
        enc_in=8,
        dec_in=8,
        c_out=1,
        d_model=256,
        n_heads=8,
        n_encoder_layers=2,
        n_decoder_layers=2,
        d_ff=1024,
        device=device
    )
    
    # Check if a trained Informer model exists
    informer_path = "checkpoints/best_model.pt"
    if os.path.exists(informer_path):
        logger.info(f"Loading trained Informer model from {informer_path}...")
        informer, _ = Informer.load_checkpoint(informer_path, device)
    else:
        logger.info("Trained Informer model checkpoint not found. Creating a fresh instance...")
        informer = Informer(informer_cfg)
        # Briefly save checkpoint so we can profile file size
        informer.save_checkpoint("checkpoints/best_model.pt")
        
    # LSTM Config
    lstm = LSTMModel(input_size=8, hidden_size=256, num_layers=2, output_size=1)
    
    models = {
        "Informer": informer,
        "LSTM": lstm
    }
    
    # 3. Model Sizes
    logger.info("\n" + "="*50 + "\nMODEL PARAMETERS AND SIZE\n" + "="*50)
    sizes = {}
    for name, model in models.items():
        chk_path = "checkpoints/best_model.pt" if name == "Informer" else "checkpoints/lstm_mock.pt"
        if name == "LSTM":
            os.makedirs("checkpoints", exist_ok=True)
            torch.save(model.state_dict(), chk_path)
        sizes[name] = Evaluator.profile_model_size(model, chk_path)
        logger.info(f"{name}: Parameters={sizes[name]['total_parameters']:,} | Checkpoint Size={sizes[name]['file_size_mb']:.2f} MB")
        if name == "LSTM" and os.path.exists(chk_path):
            os.remove(chk_path)
            
    # 4. Latency benchmark
    logger.info("\n" + "="*50 + "\nLATENCY AND THROUGHPUT PROFILE\n" + "="*50)
    sample_enc = torch.randn(1, 72, 8)
    sample_dec = torch.randn(1, 1, 8)
    latency_results = run_latency_benchmark(models, sample_enc, sample_dec, n_iterations=1000, device=device)
    
    # 5. Regression Accuracy & Backtesting
    logger.info("\n" + "="*50 + "\nACCURACY AND BACKTEST COMPARISON\n" + "="*50)
    acc_results, backtest_results = run_evaluation_benchmark(models, test_loader, raw_close_prices, device)
    
    # 6. Dynamic INT8 Quantization Profile (on CPU)
    logger.info("\n" + "="*50 + "\nDYNAMIC INT8 CPU QUANTIZATION PROFILE\n" + "="*50)
    quantization_results = {}
    for name, model in models.items():
        is_inf = (name == "Informer")
        quant_profile = Evaluator.profile_quantization(model, sample_enc, sample_dec if is_inf else None, is_informer=is_inf)
        quantization_results[name] = quant_profile
        logger.info(
            f"{name}: CPU Latency Speedup={quant_profile['speedup_ratio']:.2f}x "
            f"({quant_profile['unquantized_latency_ms']:.2f}ms -> {quant_profile['quantized_latency_ms']:.2f}ms) | "
            f"Size Reduction={quant_profile['size_reduction_ratio']:.2f}x "
            f"({quant_profile['unquantized_size_mb']:.2f}MB -> {quant_profile['quantized_size_mb']:.2f}MB)"
        )
        
    # Compile comparison metrics JSON
    comparison_data = {
        "metadata": {
            "timestamp": pd.Timestamp.now().isoformat(),
            "device": str(device)
        },
        "metrics": {
            "Informer": {
                **acc_results["Informer"],
                **sizes["Informer"],
                **latency_results["Informer"],
                "backtest": {
                    "total_return": backtest_results["Informer"]["total_return"],
                    "sharpe_ratio": backtest_results["Informer"]["sharpe_ratio"],
                    "max_drawdown": backtest_results["Informer"]["max_drawdown"],
                    "win_rate": backtest_results["Informer"]["win_rate"]
                },
                "quantization": quantization_results["Informer"]
            },
            "LSTM": {
                **acc_results["LSTM"],
                **sizes["LSTM"],
                **latency_results["LSTM"],
                "backtest": {
                    "total_return": backtest_results["LSTM"]["total_return"],
                    "sharpe_ratio": backtest_results["LSTM"]["sharpe_ratio"],
                    "max_drawdown": backtest_results["LSTM"]["max_drawdown"],
                    "win_rate": backtest_results["LSTM"]["win_rate"]
                },
                "quantization": quantization_results["LSTM"]
            }
        }
    }
    
    # Save to metrics_comparison.json
    json_path = "results/metrics_comparison.json"
    with open(json_path, "w") as f:
        json.dump(comparison_data, f, indent=2)
    logger.info(f"✓ Metrics comparison saved to {json_path}")
    
    # Compile comparison metrics CSV (flattened format)
    rows = []
    for model_name, data_dict in comparison_data["metrics"].items():
        row = {
            "model": model_name,
            "mae": data_dict["mae"],
            "rmse": data_dict["rmse"],
            "mape": data_dict["mape"],
            "directional_accuracy": data_dict["directional_accuracy"],
            "total_parameters": data_dict["total_parameters"],
            "checkpoint_size_mb": data_dict["file_size_mb"],
            "p50_latency_ms": data_dict["p50_latency_ms"],
            "p95_latency_ms": data_dict["p95_latency_ms"],
            "p99_latency_ms": data_dict["p99_latency_ms"],
            "mean_latency_ms": data_dict["mean_latency_ms"],
            "throughput_samples_per_sec": data_dict["throughput_samples_per_sec"],
            "trading_return": data_dict["backtest"]["total_return"],
            "trading_sharpe": data_dict["backtest"]["sharpe_ratio"],
            "trading_max_drawdown": data_dict["backtest"]["max_drawdown"],
            "trading_win_rate": data_dict["backtest"]["win_rate"],
            "cpu_quantized_speedup": data_dict["quantization"]["speedup_ratio"],
            "cpu_quantized_size_reduction": data_dict["quantization"]["size_reduction_ratio"]
        }
        rows.append(row)
        
    csv_df = pd.DataFrame(rows)
    csv_path = "results/benchmark_results.csv"
    csv_df.to_csv(csv_path, index=False)
    logger.info(f"✓ Benchmark results CSV saved to {csv_path}")
    
    # Save equity curve curves for visualization overlay
    equity_curves = {
        "Informer": backtest_results["Informer"]["equity_curve"],
        "LSTM": backtest_results["LSTM"]["equity_curve"]
    }
    with open("results/equity_curves.json", "w") as f:
        json.dump(equity_curves, f)
        
    # Generate Visualizations
    logger.info("\n" + "="*50 + "\nGENERATING PLOTS\n" + "="*50)
    try:
        from visualization import EvaluationVisualizer
        EvaluationVisualizer.plot_equity_curves(
            informer_equity=backtest_results["Informer"]["equity_curve"],
            lstm_equity=backtest_results["LSTM"]["equity_curve"],
            save_path="results/equity_curves.png"
        )
        EvaluationVisualizer.plot_metrics_comparison(
            metrics_comparison_dict=comparison_data,
            save_path="results/metrics_comparison.png"
        )
        logger.info("✓ Visualizations generated successfully.")
    except Exception as e:
        logger.error(f"Failed to generate visualizations: {e}")
        
    logger.info("✓ Full evaluation comparisons finished successfully!")


if __name__ == "__main__":
    run_full_comparison()
