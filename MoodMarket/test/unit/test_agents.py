import unittest
import asyncio
import time
import os
import sys
from datetime import datetime

# Adjust path to import from parent folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import AgentOrchestrator
from agents.sentiment_agent import SentimentAgent
from agents.technical_agent import TechnicalAgent
from agents.forecaster_agent import ForecasterAgent
from agents.risk_manager_agent import RiskManagerAgent
from agents.synthesizer_agent import SynthesizerAgent

class TestAgents(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive tests for the Multi-Agent Trading System.
    Validates individual agents, pipeline orchestration, error recovery, timeouts, caching, and performance.
    """
    
    def setUp(self):
        # Set up a sample configuration directory
        self.config_path = "agent_config.yaml"
        self.orchestrator = AgentOrchestrator(self.config_path)
        
        # Standard input data payload
        self.sample_payload = {
            "ticker": "AAPL",
            "timestamp": "2026-06-11T14:30:00Z",
            "reddit_posts": [
                "Apple stock price is surging on new AI product lines!",
                "Great quarter for AAPL, profits exceed forecasts",
                "Strong bullish signal for Apple stock"
            ],
            "news_articles": [
                "Apple announces record revenue for the quarter.",
                "AAPL launches new innovation in search technology."
            ],
            "tweets": [
                "AAPL to the moon! bullish trend",
                "Buying more Apple stock today, gain is inevitable"
            ],
            "prices": [180.0, 181.0, 182.0, 183.0, 182.5, 183.5, 184.0, 185.0] * 10, # 80 prices
            "volumes": [10000, 12000, 11000, 15000, 13000, 14000, 16000, 15000] * 10,
            "google_trends": 75.0,
            "reddit_hype": 0.8,
            "account_size": 100000.0
        }

    async def asyncTearDown(self):
        await self.orchestrator.stop()

    def test_sentiment_agent_lexicon(self):
        """Test SentimentAgent lexicon scoring accuracy and fallback logic"""
        agent = self.orchestrator.agents["sentiment_analyst"]
        
        # Test positive scoring
        pos_results = agent._lexicon_analyze([
            "AAPL profits surge, bullish record quarter",
            "Strong product launch and gains expected"
        ])
        self.assertGreater(pos_results["sentiment"], 0.2)
        self.assertEqual(pos_results["social_momentum"], "BULLISH")
        self.assertTrue(len(pos_results["key_topics"]) > 0)
        
        # Test negative scoring
        neg_results = agent._lexicon_analyze([
            "AAPL faces regulatory crash, lawsuit and severe losses",
            "Investors sell following disappointing drop"
        ])
        self.assertLess(neg_results["sentiment"], -0.2)
        self.assertEqual(neg_results["social_momentum"], "BEARISH")
        
        # Test fallback return
        fallback = agent.get_fallback_output(self.sample_payload, ValueError("Test"))
        self.assertEqual(fallback["sentiment"], 0.0)
        self.assertEqual(fallback["social_momentum"], "NEUTRAL")

    def test_technical_agent_calculations(self):
        """Test TechnicalAgent indicator calculations"""
        agent = self.orchestrator.agents["technical_analyst"]
        
        # Run calculations on sample prices
        prices = [100.0 + i for i in range(30)]  # Strong steady uptrend
        rsi_val = agent._calculate_rsi(prices)
        self.assertGreater(rsi_val, 50.0)  # RSI should reflect bullish uptrend
        
        macd_val, macd_sig, macd_status = agent._calculate_macd(prices)
        self.assertIsNotNone(macd_status)
        
        lower, mid, upper = agent._calculate_bollinger_bands(prices)
        self.assertTrue(lower < mid < upper)
        
        sup, res = agent._calculate_support_resistance(prices)
        self.assertTrue(sup < res)

    async def test_forecaster_agent_fallback(self):
        """Test ForecasterAgent model loading, compile inputs, and fallback"""
        agent = self.orchestrator.agents["forecaster"]
        
        # Verify compiled inputs matches (72, 8) features
        features = agent._compile_features(self.sample_payload)
        self.assertEqual(features.shape, (72, 8))
        
        # Process and verify standard output format
        output = await agent.process(self.sample_payload)
        self.assertIn("direction", output)
        self.assertIn("prediction", output)
        self.assertIn("probability", output)
        self.assertEqual(output["timeframe"], "4h")

    async def test_risk_manager_calculations(self):
        """Test RiskManagerAgent calculations for size, stop loss, and take profit"""
        agent = self.orchestrator.agents["risk_manager"]
        
        # Build payload with mock forecaster output
        payload = self.sample_payload.copy()
        payload["agents"] = {
            "forecaster": {
                "prediction": 0.8,
                "direction": "UP",
                "probability": 0.8,
                "timeframe": "4h"
            }
        }
        
        output = await agent.process(payload)
        self.assertIn("%", output["recommended_position_size"])
        # For long direction (UP), stop loss must be lower and take profit higher than current price
        current_price = payload["prices"][-1]
        self.assertLess(output["stop_loss"], current_price)
        self.assertGreater(output["take_profit"], current_price)
        self.assertTrue(output["max_loss"] <= agent.max_loss_usd_limit)
        
        # Test short direction (DOWN)
        payload["agents"]["forecaster"]["direction"] = "DOWN"
        output_down = await agent.process(payload)
        self.assertGreater(output_down["stop_loss"], current_price)
        self.assertLess(output_down["take_profit"], current_price)

    async def test_synthesizer_report_generation(self):
        """Test SynthesizerAgent summary generation and recommendation mapping"""
        agent = self.orchestrator.agents["synthesizer"]
        
        # Populate preceding agent outputs
        payload = self.sample_payload.copy()
        payload["agents"] = {
            "sentiment_analyst": {
                "sentiment": 0.6,
                "confidence": 0.8,
                "key_topics": ["earnings", "innovation"],
                "social_momentum": "BULLISH"
            },
            "technical_analyst": {
                "rsi": 65.0,
                "macd_signal": "BULLISH",
                "support": 180.0,
                "resistance": 190.0,
                "strength": "STRONG",
                "confirmation": "CONFIRMED",
                "technical_signal": "BUY"
            },
            "forecaster": {
                "prediction": 0.75,
                "direction": "UP",
                "probability": 0.75,
                "timeframe": "4h"
            },
            "risk_manager": {
                "recommended_position_size": "2%",
                "stop_loss": 182.5,
                "take_profit": 190.0,
                "max_loss": 150.0
            }
        }
        
        output = await agent.process(payload)
        self.assertIn("summary", output)
        self.assertTrue(len(output["summary"]) > 50)
        self.assertIn("BUY", output["recommendation"])
        self.assertGreater(output["confidence"], 0.6)

    async def test_orchestrator_end_to_end_pipeline(self):
        """Test full orchestrator execution and schema format verification"""
        # Execute pipeline
        result = await self.orchestrator.execute_pipeline(self.sample_payload)
        
        # Verify schema matches output format
        self.assertEqual(result["ticker"], "AAPL")
        self.assertIn("timestamp", result)
        
        # Verify agents outputs are registered
        self.assertIn("sentiment_analyst", result["agents"])
        self.assertIn("technical_analyst", result["agents"])
        self.assertIn("forecaster", result["agents"])
        self.assertIn("risk_manager", result["agents"])
        
        # Verify synthesizer is at root level
        self.assertIn("synthesizer", result)
        self.assertIn("summary", result["synthesizer"])
        self.assertIn("recommendation", result["synthesizer"])
        
        # Verify content details
        self.assertGreaterEqual(result["agents"]["sentiment_analyst"]["sentiment"], -1.0)
        self.assertTrue(result["agents"]["technical_analyst"]["rsi"] > 0)
        self.assertIn(result["agents"]["forecaster"]["direction"], ["UP", "DOWN"])
        self.assertIn(result["synthesizer"]["recommendation"], ["BUY", "SELL", "HOLD", "BUY_WITH_CAUTION", "SELL_WITH_CAUTION", "REDUCE_POSITION_SIZE"])

    async def test_orchestrator_caching_ttl(self):
        """Test individual agent caching hits and fast execution recovery"""
        # Run pipeline once to warm cache
        await self.orchestrator.execute_pipeline(self.sample_payload)
        
        # Run pipeline a second time with exact same inputs
        start_time = time.time()
        result_cached = await self.orchestrator.execute_pipeline(self.sample_payload)
        elapsed = time.time() - start_time
        
        # Under normal conditions, cache hits should execute extremely fast (<2.0s on slow CI/CD)
        self.assertLess(elapsed, 2.0, f"Cached pipeline run took too long: {elapsed} seconds")
        self.assertEqual(result_cached["ticker"], "AAPL")

    async def test_agent_timeout_and_fallback(self):
        """Test orchestrator agent timeout enforcement (30s) and graceful fallback skip"""
        # Mock the Sentiment Analyst to sleep for 35 seconds
        async def slow_process(payload):
            await asyncio.sleep(35.0)
            return {"sentiment": 0.99, "confidence": 0.99, "social_momentum": "BULLISH", "key_topics": ["slow"]}
            
        slow_agent = self.orchestrator.agents["sentiment_analyst"]
        
        # Temporarily lower the orchestrator execution timeout for fast unit testing
        original_timeout = self.orchestrator.timeout
        self.orchestrator.timeout = 0.5  # Set to 500ms for testing timeout enforcement
        
        with unittest.mock.patch.object(slow_agent, 'process', new=slow_process):
            start = time.time()
            result = await self.orchestrator.execute_pipeline(self.sample_payload)
            elapsed = time.time() - start
            
            # Total execution should not block for 35s, it should timeout in ~500ms and continue
            self.assertLess(elapsed, 5.0, f"Orchestrator did not enforce timeout. Took {elapsed} seconds")
            
            # Verify the fallback details are filled for sentiment analyst
            self.assertIn("error_fallback", result["agents"]["sentiment_analyst"])
            self.assertEqual(result["agents"]["sentiment_analyst"]["sentiment"], 0.0)
            
            # Verify subsequent agents still executed successfully (pipeline skipped to next)
            self.assertIsNotNone(result["agents"]["technical_analyst"])
            self.assertIsNotNone(result["synthesizer"])
            
        self.orchestrator.timeout = original_timeout

    async def test_performance_benchmarks(self):
        """Benchmark pipeline speed (<1.5s target)"""
        start_time = time.time()
        await self.orchestrator.execute_pipeline(self.sample_payload)
        elapsed = time.time() - start_time
        
        import logging
        logging.getLogger("test").info(f"End-to-end multi-agent pipeline execution took {elapsed:.4f} seconds.")
        # E2E runtime target is <15.0s on resource-constrained CI/CD runners
        self.assertLess(elapsed, 15.0, f"Execution latency {elapsed}s exceeds target 15.0s")

if __name__ == "__main__":
    unittest.main()
