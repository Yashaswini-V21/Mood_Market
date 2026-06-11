import unittest
import os
import sys
import numpy as np
import shutil
import tempfile
import torch

# Adjust path to import from parent folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluator import Evaluator
from backtester import Backtester
from visualization import AttentionVisualizer, EvaluationVisualizer


class TestEvaluationSuite(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_backtester_simulation(self):
        """Test backtest returns correct performance ratios and shapes."""
        # Setup dummy predictions: alternating UP/DOWN signals
        predictions = np.array([0.8, 0.2, 0.9, 0.1, 0.7, 0.3, 0.8, 0.2])
        
        # Setup dummy prices: steady uptrend
        actual_prices = np.array([100.0, 101.0, 100.5, 102.0, 101.0, 103.0, 102.0, 104.0, 103.0])
        
        backtester = Backtester(initial_capital=1000.0, transaction_cost=0.0, annualization_factor=252)
        
        # Long-Short Strategy
        result_ls = backtester.simulate(predictions, actual_prices, strategy_type="long_short")
        self.assertIn("total_return", result_ls)
        self.assertIn("sharpe_ratio", result_ls)
        self.assertIn("max_drawdown", result_ls)
        self.assertIn("win_rate", result_ls)
        self.assertEqual(len(result_ls["equity_curve"]), len(predictions) + 1)
        
        # Long-Only Strategy
        result_lo = backtester.simulate(predictions, actual_prices, strategy_type="long_only")
        self.assertLessEqual(result_lo["max_drawdown"], 0.0)
        self.assertGreaterEqual(result_lo["win_rate"], 0.0)

    def test_evaluator_regression_metrics(self):
        """Test MAE, RMSE, MAPE, and directional accuracy calculations."""
        y_true = np.array([1.0, 0.0, 1.0, 0.0])
        y_pred = np.array([0.9, 0.1, 0.8, 0.2])
        
        metrics = Evaluator.calculate_regression_metrics(y_true, y_pred)
        self.assertAlmostEqual(metrics["mae"], 0.15, places=5)
        self.assertAlmostEqual(metrics["directional_accuracy"], 1.0, places=5)
        self.assertTrue(metrics["rmse"] > 0)
        self.assertTrue(metrics["mape"] > 0)

    def test_visualizers_rendering(self):
        """Test matplotlib rendering saves valid file outputs without crashes."""
        # 1. Attention Heatmap & Step Importance
        dummy_matrix = np.random.rand(16, 16)
        dummy_importance = np.random.rand(16)
        timestamps = [f"Step {i}" for i in range(16)]
        
        heatmap_path = os.path.join(self.test_dir, "heatmap.png")
        importance_path = os.path.join(self.test_dir, "importance.png")
        
        AttentionVisualizer.plot_attention_heatmap(dummy_matrix, timestamps, heatmap_path)
        AttentionVisualizer.plot_step_importance(dummy_importance, timestamps, importance_path)
        
        self.assertTrue(os.path.exists(heatmap_path))
        self.assertTrue(os.path.exists(importance_path))
        
        # 2. Equity Curves & Metrics Comparison
        informer_equity = [1000.0 + i*5 for i in range(10)]
        lstm_equity = [1000.0 + i*2 for i in range(10)]
        
        equity_path = os.path.join(self.test_dir, "equity.png")
        metrics_path = os.path.join(self.test_dir, "metrics.png")
        
        EvaluationVisualizer.plot_equity_curves(informer_equity, lstm_equity, equity_path)
        
        # Setup dummy comparison dict
        comparison_dict = {
            "metrics": {
                "Informer": {
                    "directional_accuracy": 0.55,
                    "mae": 0.49,
                    "backtest": {"sharpe_ratio": 1.2}
                },
                "LSTM": {
                    "directional_accuracy": 0.51,
                    "mae": 0.50,
                    "backtest": {"sharpe_ratio": 0.4}
                }
            }
        }
        
        EvaluationVisualizer.plot_metrics_comparison(comparison_dict, metrics_path)
        
        self.assertTrue(os.path.exists(equity_path))
        self.assertTrue(os.path.exists(metrics_path))


if __name__ == "__main__":
    unittest.main()
