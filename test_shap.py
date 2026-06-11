"""
Comprehensive tests for SHAP explainability layer
Tests token importance calculation, visualization, and edge cases.
"""

import unittest
import numpy as np
import json
import time
import logging
from typing import List, Tuple
from unittest.mock import Mock, patch, MagicMock

from visualization import (
    SHAPVisualizer,
    BarChartData,
    ForcePlotData,
    WaterfallData,
    DependencePlotData,
    ExplanationAggregator
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSHAPVisualizer(unittest.TestCase):
    """Test SHAP visualization generator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.visualizer = SHAPVisualizer()
        
        # Sample data
        self.tokens = ["Apple", "stock", "surged", "15%", "due", "to", "strong", "earnings"]
        self.shap_values = [0.05, -0.02, 0.35, 0.20, -0.05, -0.01, 0.25, 0.18]
        self.base_value = 0.0
        self.text = " ".join(self.tokens)
    
    def test_bar_chart_creation(self):
        """Test bar chart data creation"""
        bar_chart = self.visualizer.create_bar_chart(
            self.tokens,
            self.shap_values,
            top_k=5
        )
        
        self.assertEqual(len(bar_chart.tokens), 5)
        self.assertEqual(len(bar_chart.values), 5)
        self.assertEqual(len(bar_chart.colors), 5)
        
        # Should be sorted by magnitude
        abs_values = [abs(v) for v in bar_chart.values]
        self.assertEqual(abs_values, sorted(abs_values, reverse=True))
    
    def test_bar_chart_colors(self):
        """Test bar chart color assignment"""
        bar_chart = self.visualizer.create_bar_chart(
            self.tokens,
            self.shap_values
        )
        
        # Positive values should have positive color
        for i, value in enumerate(bar_chart.values):
            if value > 0:
                self.assertEqual(bar_chart.colors[i], "#4CAF50")
            else:
                self.assertEqual(bar_chart.colors[i], "#F44336")
    
    def test_force_plot_creation(self):
        """Test force plot data creation"""
        force_plot = self.visualizer.create_force_plot(
            self.base_value,
            self.tokens,
            self.shap_values
        )
        
        self.assertEqual(force_plot.base_value, self.base_value)
        self.assertEqual(len(force_plot.features), len(self.tokens))
        self.assertEqual(len(force_plot.values), len(self.tokens))
        
        # Output should equal base + sum of values
        expected_output = self.base_value + sum(self.shap_values)
        self.assertAlmostEqual(force_plot.output_value, expected_output, places=5)
    
    def test_force_plot_effects(self):
        """Test force plot cumulative effects"""
        force_plot = self.visualizer.create_force_plot(
            self.base_value,
            self.tokens,
            self.shap_values,
            max_display=5
        )
        
        # Check cumulative calculation
        cumulative = self.base_value
        for i, val in enumerate(force_plot.values):
            self.assertAlmostEqual(force_plot.effects[i], cumulative, places=5)
            cumulative += val
    
    def test_waterfall_plot_creation(self):
        """Test waterfall plot data creation"""
        waterfall = self.visualizer.create_waterfall_plot(
            self.base_value,
            self.tokens,
            self.shap_values
        )
        
        self.assertEqual(waterfall.base_value, self.base_value)
        self.assertGreater(len(waterfall.values), 0)
        
        # Output should equal base + sum of contributions
        total_contribution = sum(v["value"] for v in waterfall.values)
        expected_output = self.base_value + total_contribution
        self.assertAlmostEqual(waterfall.output_value, expected_output, places=5)
    
    def test_waterfall_colors(self):
        """Test waterfall plot color assignment"""
        waterfall = self.visualizer.create_waterfall_plot(
            self.base_value,
            self.tokens,
            self.shap_values
        )
        
        for entry in waterfall.values:
            if entry["value"] > 0:
                self.assertEqual(entry["color"], "#4CAF50")
            else:
                self.assertEqual(entry["color"], "#F44336")
    
    def test_summary_plot_aggregation(self):
        """Test summary plot aggregation"""
        tokens_list = [
            ["Apple", "stock", "up"],
            ["Apple", "stock", "down"],
            ["Apple", "down"]
        ]
        shap_values_list = [
            [0.3, 0.2, 0.4],
            [0.1, 0.3, -0.2],
            [0.4, -0.3]
        ]
        
        summary = self.visualizer.create_summary_plot(
            tokens_list,
            shap_values_list,
            max_display=3
        )
        
        self.assertEqual(summary["type"], "summary")
        self.assertGreater(len(summary["tokens"]), 0)
        self.assertEqual(len(summary["tokens"]), len(summary["mean_importance"]))
    
    def test_comparison_plot(self):
        """Test comparison plot creation"""
        text2_tokens = ["Microsoft", "revenue", "disappoints", "analysts"]
        text2_shap = [-0.1, -0.3, -0.4, -0.15]
        
        comparison = self.visualizer.create_comparison_plot(
            self.tokens,
            self.shap_values,
            text2_tokens,
            text2_shap
        )
        
        self.assertEqual(comparison["type"], "comparison")
        self.assertIn("text1", comparison)
        self.assertIn("text2", comparison)
        self.assertEqual(len(comparison["text1"]["tokens"]), len(comparison["text1"]["shap_values"]))
    
    def test_decision_plot(self):
        """Test decision plot creation"""
        decision = self.visualizer.create_decision_plot(
            self.base_value,
            self.tokens,
            self.shap_values
        )
        
        self.assertEqual(decision["type"], "decision")
        self.assertEqual(decision["base_value"], self.base_value)
        self.assertEqual(len(decision["tokens"]), len(self.tokens))
        self.assertEqual(len(decision["contributions"]), len(self.tokens))
        
        # Check final output value
        expected_output = self.base_value + sum(self.shap_values)
        self.assertAlmostEqual(decision["output_value"], expected_output, places=5)
    
    def test_heatmap_data(self):
        """Test heatmap data creation"""
        heatmap = self.visualizer.create_heatmap_data(
            self.tokens,
            self.shap_values,
            self.text
        )
        
        self.assertEqual(heatmap["type"], "heatmap")
        self.assertEqual(heatmap["text"], self.text)
        self.assertEqual(len(heatmap["tokens"]), len(self.tokens))
        
        # Check color assignments
        for token_info in heatmap["tokens"]:
            self.assertIn("token", token_info)
            self.assertIn("shap_value", token_info)
            self.assertIn("color", token_info)
            self.assertIn("intensity", token_info)
            
            # Intensity should be between 0 and 1
            self.assertGreaterEqual(token_info["intensity"], 0)
            self.assertLessEqual(token_info["intensity"], 1)
    
    def test_frontend_bundle(self):
        """Test complete frontend bundle creation"""
        bundle = self.visualizer.create_frontend_bundle(
            self.base_value,
            self.tokens,
            self.shap_values,
            self.text,
            model_name="ensemble"
        )
        
        self.assertEqual(bundle["model"], "ensemble")
        self.assertEqual(bundle["text"], self.text)
        self.assertEqual(bundle["base_value"], self.base_value)
        
        # Check all visualizations present
        self.assertIn("bar_chart", bundle["visualizations"])
        self.assertIn("force_plot", bundle["visualizations"])
        self.assertIn("waterfall", bundle["visualizations"])
        self.assertIn("decision_plot", bundle["visualizations"])
        self.assertIn("heatmap", bundle["visualizations"])
        
        # Check summary statistics
        summary = bundle["summary"]
        self.assertEqual(summary["total_tokens"], len(self.tokens))
        self.assertGreater(summary["positive_contribution"], 0)
        self.assertLess(summary["negative_contribution"], 0)


class TestDataClasses(unittest.TestCase):
    """Test data classes"""
    
    def test_bar_chart_serialization(self):
        """Test BarChartData serialization"""
        bar_chart = BarChartData(
            tokens=["token1", "token2"],
            values=[0.5, -0.3],
            colors=["#4CAF50", "#F44336"]
        )
        
        data_dict = bar_chart.to_dict()
        
        self.assertIsInstance(data_dict, dict)
        self.assertEqual(data_dict["tokens"], ["token1", "token2"])
        self.assertEqual(data_dict["values"], [0.5, -0.3])
        
        # Should be JSON serializable
        json_str = json.dumps(data_dict)
        self.assertIsInstance(json_str, str)
    
    def test_force_plot_serialization(self):
        """Test ForcePlotData serialization"""
        force_plot = ForcePlotData(
            base_value=0.0,
            output_value=0.5,
            features=["token1", "token2"],
            values=[0.3, 0.2],
            effects=[0.0, 0.3]
        )
        
        data_dict = force_plot.to_dict()
        json_str = json.dumps(data_dict)
        self.assertIsInstance(json_str, str)
    
    def test_waterfall_serialization(self):
        """Test WaterfallData serialization"""
        waterfall = WaterfallData(
            base_value=0.0,
            values=[{"name": "token1", "value": 0.3, "color": "#4CAF50"}],
            output_value=0.3
        )
        
        data_dict = waterfall.to_dict()
        json_str = json.dumps(data_dict)
        self.assertIsInstance(json_str, str)


class TestExplanationAggregator(unittest.TestCase):
    """Test explanation aggregation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.aggregator = ExplanationAggregator()
    
    def test_add_explanation(self):
        """Test adding explanations"""
        self.aggregator.add_explanation(
            tokens=["Apple", "up"],
            shap_values=[0.4, 0.3],
            text="Apple up",
            sentiment=0.7,
            confidence=0.9
        )
        
        self.assertEqual(len(self.aggregator.explanations), 1)
    
    def test_feature_importance_distribution(self):
        """Test feature importance distribution"""
        # Add multiple explanations
        self.aggregator.add_explanation(
            tokens=["Apple", "up", "strong"],
            shap_values=[0.3, 0.4, 0.3],
            text="Apple up strong",
            sentiment=0.8,
            confidence=0.9
        )
        
        self.aggregator.add_explanation(
            tokens=["Apple", "down"],
            shap_values=[0.2, -0.5],
            text="Apple down",
            sentiment=-0.3,
            confidence=0.85
        )
        
        distributions = self.aggregator.get_feature_importance_distribution()
        
        # Apple should appear twice
        self.assertIn("Apple", distributions)
        self.assertEqual(distributions["Apple"]["count"], 2)
    
    def test_sentiment_correlations(self):
        """Test sentiment correlations"""
        # Add explanations with varying sentiments
        self.aggregator.add_explanation(
            tokens=["strong", "positive"],
            shap_values=[0.4, 0.3],
            text="strong positive",
            sentiment=0.8,
            confidence=0.9
        )
        
        self.aggregator.add_explanation(
            tokens=["weak", "negative"],
            shap_values=[0.1, -0.4],
            text="weak negative",
            sentiment=-0.7,
            confidence=0.85
        )
        
        correlations = self.aggregator.get_sentiment_correlations()
        
        self.assertGreater(len(correlations), 0)
        
        # All correlations should be between -1 and 1
        for token, corr in correlations.items():
            self.assertGreaterEqual(corr, -1.0)
            self.assertLessEqual(corr, 1.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.visualizer = SHAPVisualizer()
    
    def test_single_token(self):
        """Test with single token"""
        bar_chart = self.visualizer.create_bar_chart(
            tokens=["Apple"],
            shap_values=[0.5],
            top_k=10
        )
        
        self.assertEqual(len(bar_chart.tokens), 1)
        self.assertEqual(bar_chart.values[0], 0.5)
    
    def test_all_zero_shap_values(self):
        """Test with all zero SHAP values"""
        tokens = ["token1", "token2", "token3"]
        shap_values = [0.0, 0.0, 0.0]
        
        bar_chart = self.visualizer.create_bar_chart(tokens, shap_values)
        
        self.assertEqual(len(bar_chart.values), 3)
        self.assertTrue(all(v == 0.0 for v in bar_chart.values))
    
    def test_mixed_large_small_values(self):
        """Test with mixed large and small SHAP values"""
        tokens = ["large", "tiny", "medium"]
        shap_values = [1.0, 0.001, 0.5]
        
        bar_chart = self.visualizer.create_bar_chart(tokens, shap_values)
        
        # Should sort by magnitude correctly
        self.assertEqual(bar_chart.tokens[0], "large")
    
    def test_negative_base_value(self):
        """Test with negative base value"""
        force_plot = self.visualizer.create_force_plot(
            base_value=-0.5,
            tokens=["token1", "token2"],
            shap_values=[0.3, 0.4]
        )
        
        expected_output = -0.5 + 0.3 + 0.4
        self.assertAlmostEqual(force_plot.output_value, expected_output, places=5)
    
    def test_very_long_text(self):
        """Test with very long text"""
        tokens = [f"token_{i}" for i in range(1000)]
        shap_values = np.random.randn(1000).tolist()
        
        bar_chart = self.visualizer.create_bar_chart(
            tokens,
            shap_values,
            top_k=10
        )
        
        self.assertEqual(len(bar_chart.tokens), 10)
    
    def test_special_characters_in_tokens(self):
        """Test with special characters in tokens"""
        tokens = ["$AAPL", "it's", "50%", "❤️", "<html>"]
        shap_values = [0.3, 0.2, 0.4, 0.1, -0.2]
        
        bar_chart = self.visualizer.create_bar_chart(tokens, shap_values)
        
        self.assertEqual(len(bar_chart.tokens), 5)
        self.assertIn("$AAPL", bar_chart.tokens)


class TestFinancialTextExamples(unittest.TestCase):
    """Test with realistic financial text examples"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.visualizer = SHAPVisualizer()
    
    def test_bullish_sentiment(self):
        """Test with bullish financial text"""
        tokens = ["AAPL", "exceeds", "earnings", "expectations", "strong", "growth"]
        shap_values = [0.05, 0.15, 0.25, 0.20, 0.30, 0.25]  # All positive
        
        bar_chart = self.visualizer.create_bar_chart(tokens, shap_values)
        
        # All colors should be positive
        self.assertTrue(all(c == "#4CAF50" for c in bar_chart.colors))
        
        # Most positive should be "strong" or "growth"
        max_idx = shap_values.index(max(shap_values))
        self.assertIn(tokens[max_idx], ["strong", "growth"])
    
    def test_bearish_sentiment(self):
        """Test with bearish financial text"""
        tokens = ["TSLA", "plunges", "disappoints", "guidance", "concerns", "losses"]
        shap_values = [-0.05, -0.35, -0.30, -0.25, -0.20, -0.15]  # All negative
        
        bar_chart = self.visualizer.create_bar_chart(tokens, shap_values)
        
        # All colors should be negative
        self.assertTrue(all(c == "#F44336" for c in bar_chart.colors))
    
    def test_mixed_sentiment(self):
        """Test with mixed sentiment text"""
        tokens = ["Stock", "tanked", "but", "fundamentals", "strong"]
        shap_values = [0.0, -0.6, -0.05, 0.3, 0.4]
        
        force_plot = self.visualizer.create_force_plot(0.0, tokens, shap_values)
        
        # Should capture mixed sentiment
        self.assertLess(force_plot.output_value, 0.5)
        self.assertGreater(force_plot.output_value, -0.5)
    
    def test_reddit_post(self):
        """Test with Reddit post"""
        reddit_post = "AAPL calls printing! This stock is absolutely crushing it. Q3 earnings were massive. Loading up on more shares. Diamond hands! 🚀"
        tokens = reddit_post.split()
        # Simulate SHAP values (more positive for positive words)
        shap_values = [0.1] * len(tokens)
        shap_values[tokens.index("crushing")] = 0.5
        shap_values[tokens.index("massive")] = 0.4
        shap_values[tokens.index("🚀")] = 0.3
        
        summary = self.visualizer.create_summary_plot(
            [tokens],
            [shap_values],
            max_display=5
        )
        
        self.assertEqual(summary["type"], "summary")
    
    def test_news_headline(self):
        """Test with news headline"""
        headline = "Fed raises rates amid inflation concerns, market declines"
        tokens = headline.split()
        shap_values = [0.05, -0.1, -0.15, -0.2, -0.25, -0.1]
        
        bundle = self.visualizer.create_frontend_bundle(
            0.0,
            tokens,
            shap_values,
            headline,
            model_name="finbert"
        )
        
        self.assertEqual(bundle["model"], "finbert")
        self.assertLess(bundle["summary"]["negative_contribution"], 0)


class TestPerformance(unittest.TestCase):
    """Performance benchmarks"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.visualizer = SHAPVisualizer()
    
    def test_bar_chart_performance(self):
        """Benchmark bar chart creation"""
        tokens = [f"token_{i}" for i in range(500)]
        shap_values = np.random.randn(500).tolist()
        
        start = time.time()
        for _ in range(100):
            self.visualizer.create_bar_chart(tokens, shap_values)
        elapsed = time.time() - start
        
        avg_time_ms = (elapsed / 100) * 1000
        logger.info(f"Bar chart creation: {avg_time_ms:.2f}ms per call")
        
        # Should be very fast
        self.assertLess(avg_time_ms, 50)
    
    def test_frontend_bundle_performance(self):
        """Benchmark frontend bundle creation"""
        tokens = [f"token_{i}" for i in range(100)]
        shap_values = np.random.randn(100).tolist()
        text = " ".join(tokens)
        
        start = time.time()
        for _ in range(100):
            self.visualizer.create_frontend_bundle(0.0, tokens, shap_values, text)
        elapsed = time.time() - start
        
        avg_time_ms = (elapsed / 100) * 1000
        logger.info(f"Frontend bundle creation: {avg_time_ms:.2f}ms per call")
        
        # Should complete within 200ms
        self.assertLess(avg_time_ms, 200)
    
    def test_aggregation_performance(self):
        """Benchmark explanation aggregation"""
        aggregator = ExplanationAggregator()
        
        start = time.time()
        for i in range(1000):
            aggregator.add_explanation(
                tokens=[f"token_{j}" for j in range(50)],
                shap_values=np.random.randn(50).tolist(),
                text=f"text_{i}",
                sentiment=np.random.randn(),
                confidence=np.random.random()
            )
        elapsed = time.time() - start
        
        avg_time_ms = (elapsed / 1000) * 1000
        logger.info(f"Aggregation: {avg_time_ms:.2f}ms per explanation")
        
        self.assertLess(avg_time_ms, 10)


# Test runner
def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSHAPVisualizer))
    suite.addTests(loader.loadTestsFromTestCase(TestDataClasses))
    suite.addTests(loader.loadTestsFromTestCase(TestExplanationAggregator))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestFinancialTextExamples))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
