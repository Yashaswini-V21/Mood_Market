import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List, Union


class Backtester:
    """
    Simulates trading strategies based on predicted directions and calculates
    financial performance metrics (Sharpe ratio, max drawdown, win rate).
    """
    def __init__(
        self,
        initial_capital: float = 100000.0,
        transaction_cost: float = 0.0005,  # 5 bps per trade
        annualization_factor: float = 252 * 6.5 * 4  # 15-min bars for US equity market
    ):
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.annualization_factor = annualization_factor

    def simulate(
        self,
        predictions: np.ndarray,
        actual_prices: np.ndarray,
        strategy_type: str = "long_short"
    ) -> Dict[str, Any]:
        """
        Runs backtest simulation.
        
        Args:
            predictions: Array of probabilities of shape (N,) predicting close price goes UP.
            actual_prices: Close prices of the asset of shape (N+1,) or (N,) to calculate returns.
            strategy_type: "long_only" or "long_short".
            
        Returns:
            Dict containing backtest metrics and equity curve series.
        """
        n_steps = len(predictions)
        
        # Calculate asset returns: R_t = (P_t - P_{t-1}) / P_{t-1}
        # Assuming actual_prices has length matching N + 1 (since returns require t and t-1)
        if len(actual_prices) == n_steps + 1:
            asset_returns = np.diff(actual_prices) / actual_prices[:-1]
        elif len(actual_prices) == n_steps:
            asset_returns = np.zeros(n_steps)
            asset_returns[1:] = np.diff(actual_prices) / actual_prices[:-1]
        else:
            raise ValueError(f"Prices length ({len(actual_prices)}) must be N or N+1 where N={n_steps}.")
            
        # Determine positions based on prediction threshold (0.5)
        # Position at step t is taken at start of period t, based on prediction at t-1
        positions = np.zeros(n_steps)
        if strategy_type == "long_short":
            positions = np.where(predictions > 0.5, 1.0, -1.0)
        elif strategy_type == "long_only":
            positions = np.where(predictions > 0.5, 1.0, 0.0)
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
            
        # Compute trading costs
        # Triggers when position changes
        position_changes = np.zeros(n_steps)
        position_changes[0] = abs(positions[0])
        position_changes[1:] = abs(np.diff(positions))
        
        costs = position_changes * self.transaction_cost
        
        # Strategy returns
        strategy_returns = (positions * asset_returns) - costs
        
        # Equity curve starting at initial capital
        equity_curve = self.initial_capital * np.cumprod(1.0 + strategy_returns)
        # Prepend initial capital for start of curve
        equity_curve = np.insert(equity_curve, 0, self.initial_capital)
        
        # Financial metrics calculation
        total_return = (equity_curve[-1] - self.initial_capital) / self.initial_capital
        
        # Sharpe Ratio
        mean_ret = np.mean(strategy_returns)
        std_ret = np.std(strategy_returns)
        if std_ret > 0:
            sharpe_ratio = (mean_ret / std_ret) * np.sqrt(self.annualization_factor)
        else:
            sharpe_ratio = 0.0
            
        # Max Drawdown
        running_max = np.maximum.accumulate(equity_curve)
        drawdowns = (equity_curve - running_max) / running_max
        max_drawdown = float(np.min(drawdowns))
        
        # Win Rate
        winning_trades = np.sum(strategy_returns > 0)
        total_trades = np.sum(positions != 0)
        win_rate = float(winning_trades / total_trades) if total_trades > 0 else 0.0
        
        return {
            "total_return": float(total_return),
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "equity_curve": equity_curve.tolist(),
            "strategy_returns": strategy_returns.tolist()
        }
