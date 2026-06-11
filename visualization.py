"""
Visualization data generators for SHAP explanations
Creates JSON-serializable data structures for frontend charts and plots.
"""

import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class BarChartData:
    """Data structure for token importance bar chart"""
    tokens: List[str]
    values: List[float]
    colors: List[str]
    title: str = "Token Importance (SHAP Values)"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ForcePlotData:
    """Data structure for SHAP force plot"""
    base_value: float
    output_value: float
    features: List[str]
    values: List[float]
    effects: List[float]
    title: str = "SHAP Force Plot"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class WaterfallData:
    """Data structure for SHAP waterfall plot"""
    base_value: float
    values: List[Dict[str, Any]]  # [{"name": str, "value": float, "color": str}, ...]
    output_value: float
    title: str = "SHAP Waterfall Plot"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "base_value": self.base_value,
            "values": self.values,
            "output_value": self.output_value,
            "title": self.title
        }


@dataclass
class DependencePlotData:
    """Data structure for SHAP dependence plot"""
    feature_values: List[float]
    shap_values: List[float]
    feature_name: str
    title: str = "SHAP Dependence Plot"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class SHAPVisualizer:
    """Generate visualization data for SHAP explanations"""
    
    def __init__(self, color_positive: str = "#4CAF50", color_negative: str = "#F44336"):
        """
        Initialize visualizer
        
        Args:
            color_positive: Color for positive SHAP values
            color_negative: Color for negative SHAP values
        """
        self.color_positive = color_positive
        self.color_negative = color_negative
    
    def create_bar_chart(
        self,
        tokens: List[str],
        shap_values: List[float],
        top_k: int = 10,
        sort_by: str = "magnitude"
    ) -> BarChartData:
        """
        Create bar chart data for token importances
        
        Args:
            tokens: List of tokens
            shap_values: SHAP values for tokens
            top_k: Number of top tokens to show
            sort_by: "magnitude" (absolute value) or "value" (signed)
        
        Returns:
            BarChartData object
        """
        if len(tokens) != len(shap_values):
            raise ValueError("Tokens and SHAP values length mismatch")
        
        # Create pairs and sort
        pairs = list(zip(tokens, shap_values))
        
        if sort_by == "magnitude":
            pairs.sort(key=lambda x: abs(x[1]), reverse=True)
        else:
            pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Take top k
        pairs = pairs[:top_k]
        
        tokens_sorted = [p[0] for p in pairs]
        values_sorted = [p[1] for p in pairs]
        
        # Assign colors
        colors = [
            self.color_positive if v > 0 else self.color_negative
            for v in values_sorted
        ]
        
        return BarChartData(
            tokens=tokens_sorted,
            values=values_sorted,
            colors=colors
        )
    
    def create_force_plot(
        self,
        base_value: float,
        tokens: List[str],
        shap_values: List[float],
        max_display: int = 15
    ) -> ForcePlotData:
        """
        Create force plot data showing how predictions are built from base value
        
        Args:
            base_value: Base value (model's expected output)
            tokens: List of tokens
            shap_values: SHAP values
            max_display: Maximum features to display
        
        Returns:
            ForcePlotData object
        """
        if len(tokens) != len(shap_values):
            raise ValueError("Tokens and SHAP values length mismatch")
        
        # Sort by magnitude
        pairs = sorted(
            zip(tokens, shap_values),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:max_display]
        
        tokens_display = [p[0] for p in pairs]
        values_display = [p[1] for p in pairs]
        
        # Calculate cumulative effects
        cumulative = base_value
        effects = []
        for val in values_display:
            effects.append(cumulative)
            cumulative += val
        
        output_value = base_value + sum(values_display)
        
        return ForcePlotData(
            base_value=base_value,
            output_value=output_value,
            features=tokens_display,
            values=values_display,
            effects=effects
        )
    
    def create_waterfall_plot(
        self,
        base_value: float,
        tokens: List[str],
        shap_values: List[float],
        max_display: int = 10
    ) -> WaterfallData:
        """
        Create waterfall plot data
        
        Args:
            base_value: Base value
            tokens: List of tokens
            shap_values: SHAP values
            max_display: Maximum features to show
        
        Returns:
            WaterfallData object
        """
        if len(tokens) != len(shap_values):
            raise ValueError("Tokens and SHAP values length mismatch")
        
        # Sort by magnitude and limit
        pairs = sorted(
            zip(tokens, shap_values),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:max_display]
        
        # Build waterfall
        values = []
        current_value = base_value
        
        for token, shap_val in pairs:
            color = self.color_positive if shap_val > 0 else self.color_negative
            values.append({
                "name": token,
                "value": shap_val,
                "color": color,
                "cumulative": current_value + shap_val
            })
            current_value += shap_val
        
        return WaterfallData(
            base_value=base_value,
            values=values,
            output_value=current_value
        )
    
    def create_summary_plot(
        self,
        tokens_list: List[List[str]],
        shap_values_list: List[List[float]],
        max_display: int = 10
    ) -> Dict[str, Any]:
        """
        Create summary plot data (aggregated importance across texts)
        
        Args:
            tokens_list: List of token lists
            shap_values_list: List of SHAP value lists
            max_display: Maximum features to show
        
        Returns:
            Summary plot data
        """
        # Aggregate SHAP values by token
        token_importance = {}
        
        for tokens, shap_values in zip(tokens_list, shap_values_list):
            for token, shap_val in zip(tokens, shap_values):
                if token not in token_importance:
                    token_importance[token] = []
                token_importance[token].append(abs(shap_val))
        
        # Compute mean importance
        mean_importance = {
            token: np.mean(values)
            for token, values in token_importance.items()
        }
        
        # Sort and take top k
        sorted_tokens = sorted(
            mean_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_display]
        
        tokens = [t[0] for t in sorted_tokens]
        values = [t[1] for t in sorted_tokens]
        colors = [self.color_positive for _ in tokens]  # All positive for magnitude
        
        return {
            "type": "summary",
            "tokens": tokens,
            "mean_importance": values,
            "colors": colors,
            "title": "Feature Importance Summary"
        }
    
    def create_comparison_plot(
        self,
        text1_tokens: List[str],
        text1_shap: List[float],
        text2_tokens: List[str],
        text2_shap: List[float],
        max_display: int = 10
    ) -> Dict[str, Any]:
        """
        Create comparison plot between two texts
        
        Args:
            text1_tokens: First text tokens
            text1_shap: First text SHAP values
            text2_tokens: Second text tokens
            text2_shap: Second text SHAP values
            max_display: Maximum features to show
        
        Returns:
            Comparison plot data
        """
        # Get important tokens from both
        pairs1 = sorted(
            zip(text1_tokens, text1_shap),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:max_display]
        
        pairs2 = sorted(
            zip(text2_tokens, text2_shap),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:max_display]
        
        return {
            "type": "comparison",
            "text1": {
                "tokens": [p[0] for p in pairs1],
                "shap_values": [p[1] for p in pairs1]
            },
            "text2": {
                "tokens": [p[0] for p in pairs2],
                "shap_values": [p[1] for p in pairs2]
            }
        }
    
    def create_decision_plot(
        self,
        base_value: float,
        tokens: List[str],
        shap_values: List[float],
        cumulative_shap_values: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Create decision plot showing path from base to output
        
        Args:
            base_value: Base value
            tokens: List of tokens
            shap_values: SHAP values
            cumulative_shap_values: Cumulative SHAP values
        
        Returns:
            Decision plot data
        """
        if cumulative_shap_values is None:
            cumulative_shap_values = np.cumsum([base_value] + shap_values).tolist()[:-1]
        
        final_value = base_value + sum(shap_values)
        
        return {
            "type": "decision",
            "base_value": base_value,
            "tokens": tokens,
            "shap_values": shap_values,
            "cumulative_values": cumulative_shap_values,
            "output_value": final_value,
            "contributions": [
                {
                    "token": token,
                    "shap_value": shap_val,
                    "cumulative": cum_val
                }
                for token, shap_val, cum_val in zip(tokens, shap_values, cumulative_shap_values)
            ]
        }
    
    def create_heatmap_data(
        self,
        tokens: List[str],
        shap_values: List[float],
        text_string: str
    ) -> Dict[str, Any]:
        """
        Create data for token heatmap (color-coded text)
        
        Args:
            tokens: List of tokens
            shap_values: SHAP values
            text_string: Original text string
        
        Returns:
            Heatmap data
        """
        # Normalize SHAP values for color intensity
        abs_values = np.abs(shap_values)
        max_abs = np.max(abs_values) if abs_values.size > 0 else 1.0
        normalized = abs_values / max_abs
        
        # Create HTML-like representation with color codes
        token_info = []
        
        for token, shap_val, norm_val in zip(tokens, shap_values, normalized):
            if shap_val > 0:
                # Green for positive
                color = self._interpolate_color("#ffffff", "#4CAF50", norm_val)
            else:
                # Red for negative
                color = self._interpolate_color("#ffffff", "#F44336", norm_val)
            
            token_info.append({
                "token": token,
                "shap_value": shap_val,
                "color": color,
                "intensity": norm_val
            })
        
        return {
            "type": "heatmap",
            "text": text_string,
            "tokens": token_info,
            "scale": {
                "min_color": "#ffffff",
                "mid_color": "#E0E0E0",
                "max_positive": "#4CAF50",
                "max_negative": "#F44336"
            }
        }
    
    @staticmethod
    def _interpolate_color(color1: str, color2: str, factor: float) -> str:
        """
        Interpolate between two colors
        
        Args:
            color1: First color (hex)
            color2: Second color (hex)
            factor: Interpolation factor (0-1)
        
        Returns:
            Interpolated color (hex)
        """
        # Convert hex to RGB
        rgb1 = tuple(int(color1[i:i+2], 16) for i in (1, 3, 5))
        rgb2 = tuple(int(color2[i:i+2], 16) for i in (1, 3, 5))
        
        # Interpolate
        rgb = tuple(
            int(rgb1[i] * (1 - factor) + rgb2[i] * factor)
            for i in range(3)
        )
        
        # Convert back to hex
        return "#{:02x}{:02x}{:02x}".format(*rgb)
    
    def create_frontend_bundle(
        self,
        base_value: float,
        tokens: List[str],
        shap_values: List[float],
        text: str,
        model_name: str = "ensemble"
    ) -> Dict[str, Any]:
        """
        Create complete visualization bundle for frontend
        
        Args:
            base_value: Base value
            tokens: Tokens list
            shap_values: SHAP values
            text: Original text
            model_name: Model name
        
        Returns:
            Complete visualization bundle
        """
        bar_chart = self.create_bar_chart(tokens, shap_values)
        force_plot = self.create_force_plot(base_value, tokens, shap_values)
        waterfall = self.create_waterfall_plot(base_value, tokens, shap_values)
        decision = self.create_decision_plot(base_value, tokens, shap_values)
        heatmap = self.create_heatmap_data(tokens, shap_values, text)
        
        return {
            "model": model_name,
            "text": text,
            "base_value": base_value,
            "output_value": force_plot.output_value,
            "visualizations": {
                "bar_chart": bar_chart.to_dict(),
                "force_plot": force_plot.to_dict(),
                "waterfall": waterfall.to_dict(),
                "decision_plot": decision,
                "heatmap": heatmap
            },
            "summary": {
                "total_tokens": len(tokens),
                "positive_contribution": sum(v for v in shap_values if v > 0),
                "negative_contribution": sum(v for v in shap_values if v < 0),
                "top_positive": max(shap_values) if shap_values else 0,
                "top_negative": min(shap_values) if shap_values else 0
            }
        }


class ExplanationAggregator:
    """Aggregate and compare multiple explanations"""
    
    def __init__(self):
        """Initialize aggregator"""
        self.explanations = []
    
    def add_explanation(
        self,
        tokens: List[str],
        shap_values: List[float],
        text: str,
        sentiment: float,
        confidence: float
    ) -> None:
        """
        Add explanation
        
        Args:
            tokens: Tokens list
            shap_values: SHAP values
            text: Original text
            sentiment: Sentiment score
            confidence: Confidence score
        """
        self.explanations.append({
            "tokens": tokens,
            "shap_values": shap_values,
            "text": text,
            "sentiment": sentiment,
            "confidence": confidence
        })
    
    def get_feature_importance_distribution(self) -> Dict[str, List[float]]:
        """
        Get distribution of feature importances
        
        Returns:
            Feature importance distributions
        """
        feature_values = {}
        
        for exp in self.explanations:
            for token, shap_val in zip(exp["tokens"], exp["shap_values"]):
                if token not in feature_values:
                    feature_values[token] = []
                feature_values[token].append(abs(shap_val))
        
        # Compute statistics
        stats = {}
        for token, values in feature_values.items():
            values_array = np.array(values)
            stats[token] = {
                "mean": float(np.mean(values_array)),
                "std": float(np.std(values_array)),
                "min": float(np.min(values_array)),
                "max": float(np.max(values_array)),
                "count": len(values)
            }
        
        return stats
    
    def get_sentiment_correlations(self) -> Dict[str, float]:
        """
        Correlate token importance with sentiment
        
        Returns:
            Correlation coefficients
        """
        correlations = {}
        sentiments = np.array([exp["sentiment"] for exp in self.explanations])
        
        all_tokens = set()
        for exp in self.explanations:
            all_tokens.update(exp["tokens"])
        
        for token in all_tokens:
            importances = []
            
            for exp in self.explanations:
                if token in exp["tokens"]:
                    idx = exp["tokens"].index(token)
                    importances.append(abs(exp["shap_values"][idx]))
                else:
                    importances.append(0.0)
            
            if len(set(importances)) > 1:  # Avoid constant arrays
                corr = np.corrcoef(sentiments, importances)[0, 1]
                correlations[token] = float(corr)
        
        return correlations


# Example usage
if __name__ == "__main__":
    visualizer = SHAPVisualizer()
    
    # Example data
    tokens = ["Apple", "stock", "surged", "15%", "due", "to", "strong", "earnings"]
    shap_values = [0.05, -0.02, 0.35, 0.20, -0.05, -0.01, 0.25, 0.18]
    base_value = 0.0
    
    # Create bar chart
    bar_chart = visualizer.create_bar_chart(tokens, shap_values)
    logger.info(f"Bar Chart: {json.dumps(bar_chart.to_dict(), indent=2)}")
    
    # Create force plot
    force_plot = visualizer.create_force_plot(base_value, tokens, shap_values)
    logger.info(f"Force Plot: {json.dumps(force_plot.to_dict(), indent=2)}")
    
    # Create complete bundle
    text = " ".join(tokens)
    bundle = visualizer.create_frontend_bundle(base_value, tokens, shap_values, text)
    logger.info(f"Frontend Bundle: {json.dumps(bundle, indent=2, default=str)}")


import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

class AttentionVisualizer:
    """Generates gorgeous plots for Informer self-attention weight analysis."""
    
    @staticmethod
    def plot_attention_heatmap(
        attn_matrix: np.ndarray,
        timestamps: List[str],
        save_path: str = "results/attention_heatmap.png"
    ):
        plt.figure(figsize=(10, 8), dpi=150)
        sns.heatmap(
            attn_matrix,
            cmap="viridis",
            xticklabels=max(1, len(timestamps) // 6),
            yticklabels=max(1, len(timestamps) // 6),
            cbar_kws={'label': 'Attention Weight'}
        )
        plt.title("Informer Encoder Self-Attention Weight Matrix", fontsize=14, fontweight="bold", pad=15)
        plt.xlabel("Key (Historical Timesteps)", fontsize=12)
        plt.ylabel("Query (Historical Timesteps)", fontsize=12)
        plt.tight_layout()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Attention heatmap saved to {save_path}")

    @staticmethod
    def plot_step_importance(
        importance: np.ndarray,
        timestamps: List[str],
        save_path: str = "results/step_importance.png"
    ):
        plt.figure(figsize=(12, 5), dpi=150)
        # Create a nice gradient color representation
        colors = plt.cm.plasma(importance / (np.max(importance) + 1e-8))
        
        plt.bar(range(len(importance)), importance, color=colors, edgecolor="none")
        plt.title("Step-Level Attention Importance", fontsize=14, fontweight="bold", pad=15)
        plt.xlabel("Historical Timesteps (Relative)", fontsize=12)
        plt.ylabel("Attention Weight", fontsize=12)
        plt.grid(True, linestyle="--", alpha=0.5)
        
        # Show key tick marks for time references
        step = max(1, len(importance) // 6)
        plt.xticks(range(0, len(importance), step), [timestamps[i] for i in range(0, len(importance), step)], rotation=15)
        
        plt.tight_layout()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Step importance bar chart saved to {save_path}")


class EvaluationVisualizer:
    """Generates comparison charts between Informer and LSTM baseline."""
    
    @staticmethod
    def plot_equity_curves(
        informer_equity: List[float],
        lstm_equity: List[float],
        save_path: str = "results/equity_curves.png"
    ):
        plt.figure(figsize=(12, 6), dpi=150)
        plt.plot(informer_equity, label="Informer Strategy", color="#1F77B4", linewidth=2.5)
        plt.plot(lstm_equity, label="LSTM Strategy", color="#FF7F0E", linewidth=2.0, linestyle="--")
        
        # Plot benchmark (buy and hold equivalent or initial line)
        plt.axhline(informer_equity[0], color="grey", linestyle=":", label="Initial Capital")
        
        plt.title("Trading Strategy Equity Curves (Informer vs LSTM)", fontsize=14, fontweight="bold", pad=15)
        plt.xlabel("Trading Intervals (15-min)", fontsize=12)
        plt.ylabel("Portfolio Value ($)", fontsize=12)
        plt.legend(loc="upper left", frameon=True)
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Equity curve plot saved to {save_path}")

    @staticmethod
    def plot_metrics_comparison(
        metrics_comparison_dict: Dict[str, Any],
        save_path: str = "results/metrics_comparison.png"
    ):
        # We compare Directional Accuracy, MAE, and Sharpe ratio
        models = ["Informer", "LSTM"]
        
        inf_data = metrics_comparison_dict["metrics"]["Informer"]
        lstm_data = metrics_comparison_dict["metrics"]["LSTM"]
        
        # Gather metrics values
        inf_vals = [
            inf_data["directional_accuracy"],
            inf_data["mae"],
            inf_data["backtest"]["sharpe_ratio"]
        ]
        
        lstm_vals = [
            lstm_data["directional_accuracy"],
            lstm_data["mae"],
            lstm_data["backtest"]["sharpe_ratio"]
        ]
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=150)
        titles = ["Directional Accuracy (Higher Better)", "Mean Absolute Error (Lower Better)", "Annualized Sharpe (Higher Better)"]
        colors = ["#1F77B4", "#FF7F0E"]
        
        for i in range(3):
            ax = axes[i]
            y = [inf_vals[i], lstm_vals[i]]
            ax.bar(models, y, color=colors, width=0.5)
            ax.set_title(titles[i], fontsize=11, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.5, axis="y")
            # Label bars
            for idx, val in enumerate(y):
                ax.text(idx, val + (max(y)*0.01), f"{val:.4f}", ha="center", va="bottom", fontweight="bold")
                
        plt.suptitle("Model Evaluation Summary: Informer vs LSTM Baseline", fontsize=15, fontweight="bold", y=1.02)
        plt.tight_layout()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Metrics comparison plot saved to {save_path}")

