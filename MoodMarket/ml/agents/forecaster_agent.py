import numpy as np
import logging
import sys
import os
from typing import Dict, Any
import asyncio
from agents.base_agent import BaseAgent

# Add root directory to path if needed for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from model import Informer, InformerConfig
try:
    from inference import InferenceEngine
    HAS_INFERENCE = True
except ImportError:
    HAS_INFERENCE = False

logger = logging.getLogger(__name__)

class ForecasterAgent(BaseAgent):
    """
    Forecaster Agent
    
    Inputs: Sentiment + Technical + Trend data (8 features over 72 timesteps)
    Task: Run Informer model inference to predict next 4h price direction
    Outputs: prediction, direction, probability, timeframe
    """
    
    def __init__(self, config: Dict[str, Any], cache_ttl: int = 300):
        super().__init__("forecaster", config, cache_ttl)
        self.seq_len = config.get("seq_len", 72)
        self.pred_len = config.get("pred_len", 1)
        self.model_path = config.get("model_path", "checkpoints/best_model.pt")
        self.fallback_to_random = config.get("fallback_to_random", True)
        self.prob_threshold = config.get("probability_threshold", 0.5)
        
        self.engine = None
        self._ensure_model_checkpoint()
        self._lazy_load_engine()

    def get_relevant_input_keys(self) -> list:
        # Relies on the outputs of sentiment and technical agents, plus prices/volumes and google_trends/reddit_hype
        return ["prices", "volumes", "google_trends", "reddit_hype", "agents"]
        
    def _ensure_model_checkpoint(self):
        """Ensure a model checkpoint exists. If not, create one with random weights to allow execution."""
        if os.path.exists(self.model_path):
            return
            
        self.logger.info(f"Model checkpoint not found at {self.model_path}. Generating mock Informer checkpoint...")
        try:
            # Ensure directories exist
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            # Initialize Informer and save
            model_config = InformerConfig(
                seq_len=self.seq_len,
                pred_len=self.pred_len,
                enc_in=8,
                dec_in=8,
                c_out=1,
                device=torch.device("cpu")  # Default to CPU for testing/portability
            )
            model = Informer(model_config)
            model.save_checkpoint(self.model_path)
            self.logger.info(f"Mock Informer checkpoint successfully saved to {self.model_path}")
        except Exception as e:
            self.logger.error(f"Failed to generate mock Informer checkpoint: {e}")

    def _lazy_load_engine(self):
        """Lazily load the InferenceEngine."""
        if self.engine is not None:
            return
            
        if HAS_INFERENCE and os.path.exists(self.model_path):
            try:
                # Use CPU device to ensure compatibility in test containers
                device = torch.device("cpu")
                self.engine = InferenceEngine(model_path=self.model_path, device=device)
                self.logger.info("InferenceEngine loaded successfully inside ForecasterAgent.")
            except Exception as e:
                self.logger.warning(f"Failed to load InferenceEngine: {e}. Running in rule-based fallback mode.")
                self.engine = None
        else:
            self.logger.info("InferenceEngine not available or checkpoint missing. Running in rule-based fallback mode.")

    def _compile_features(self, payload: Dict[str, Any]) -> np.ndarray:
        """
        Compile the 8 input features over 72 timesteps.
        Features: [sentiment_score, price, volume, RSI, MACD, Bollinger_Band, google_trends, reddit_hype]
        """
        # Get data from payload
        prices = payload.get("prices", [])
        volumes = payload.get("volumes", [])
        
        # Pull latest values from other agents if available
        sentiment_data = payload.get("agents", {}).get("sentiment_analyst", {})
        technical_data = payload.get("agents", {}).get("technical_analyst", {})
        
        current_sentiment = sentiment_data.get("sentiment", 0.0)
        current_rsi = technical_data.get("rsi", 50.0)
        current_macd = 0.5 if "BULLISH" in technical_data.get("macd_signal", "NEUTRAL") else -0.5
        
        bb = technical_data.get("bollinger_bands", {})
        current_bb_width = float(bb.get("upper", 1.05) - bb.get("lower", 0.95))
        
        google_trends = payload.get("google_trends", 50.0)
        reddit_hype = payload.get("reddit_hype", 0.5)
        
        # Build historic arrays. If inputs are shorter than 72, pad or project them
        # Let's verify prices length
        if len(prices) >= self.seq_len:
            price_arr = np.array(prices[-self.seq_len:])
            vol_arr = np.array(volumes[-self.seq_len:]) if len(volumes) >= self.seq_len else np.ones(self.seq_len) * 1000
        else:
            # Pad front if too short
            pad_len = self.seq_len - len(prices)
            price_arr = np.pad(np.array(prices), (pad_len, 0), mode='edge')
            if len(volumes) > 0:
                vol_arr = np.pad(np.array(volumes), (pad_len, 0), mode='edge')
            else:
                vol_arr = np.ones(self.seq_len) * 1000
        
        # Create full arrays for other indicators
        # We can back-propagate the current indicator values or simulate simple trajectories
        sentiment_arr = np.ones(self.seq_len) * current_sentiment
        rsi_arr = np.ones(self.seq_len) * current_rsi
        macd_arr = np.ones(self.seq_len) * current_macd
        bb_width_arr = np.ones(self.seq_len) * current_bb_width
        trends_arr = np.ones(self.seq_len) * google_trends
        hype_arr = np.ones(self.seq_len) * reddit_hype
        
        # Combine into shape (72, 8)
        features = np.column_stack([
            sentiment_arr,
            price_arr,
            vol_arr,
            rsi_arr,
            macd_arr,
            bb_width_arr,
            trends_arr,
            hype_arr
        ])
        
        return features

    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Compile features
        try:
            encoder_input = self._compile_features(payload)
        except Exception as e:
            self.logger.error(f"Error compiling features for forecasting: {e}")
            return self.get_fallback_output(payload, e)
            
        # Try running InferenceEngine
        self._lazy_load_engine()
        if self.engine is not None:
            try:
                # Decoder input: shape (1, 8)
                decoder_input = encoder_input[-1:].copy()
                
                # Execute in thread executor to keep it async
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    self.engine.predict_single, 
                    encoder_input, 
                    decoder_input
                )
                
                pred_prob = float(result['prediction'])
                
                # Map to direction & probability
                direction = "UP" if pred_prob >= self.prob_threshold else "DOWN"
                probability = pred_prob if direction == "UP" else (1.0 - pred_prob)
                
                return {
                    "prediction": float(round(pred_prob, 4)),
                    "direction": direction,
                    "probability": float(round(probability, 4)),
                    "timeframe": "4h",
                    "uncertainty": float(round(float(result.get('uncertainty', 0.0)), 6))
                }
            except Exception as e:
                self.logger.warning(f"Informer model inference failed: {e}. Falling back to rule-based forecasting.")
        
        # Rule-based fallback forecasting (combining Sentiment + Technical + Hype signals)
        return self._rule_based_forecast(payload)

    def _rule_based_forecast(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simple rule-based forecasting combining sentiment score and technical indicators"""
        sentiment_data = payload.get("agents", {}).get("sentiment_analyst", {})
        technical_data = payload.get("agents", {}).get("technical_analyst", {})
        
        sentiment = sentiment_data.get("sentiment", 0.0)
        tech_signal = technical_data.get("technical_signal", "HOLD")
        
        # Combine score (-1.0 to +1.0)
        score = sentiment * 0.4
        if tech_signal == "BUY":
            score += 0.4
        elif tech_signal == "SELL":
            score -= 0.4
            
        # Factor in trends/hype if present
        reddit_hype = payload.get("reddit_hype", 0.5)
        if reddit_hype > 0.7:
            # Amplifies direction
            score *= 1.2
            
        # Map score to probability in [0, 1]
        pred_prob = 0.5 + (score * 0.5)
        pred_prob = max(0.01, min(0.99, pred_prob))
        
        direction = "UP" if pred_prob >= self.prob_threshold else "DOWN"
        probability = pred_prob if direction == "UP" else (1.0 - pred_prob)
        
        return {
            "prediction": float(round(pred_prob, 4)),
            "direction": direction,
            "probability": float(round(probability, 4)),
            "timeframe": "4h",
            "uncertainty": 0.05
        }

    def get_fallback_output(self, payload: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Default fallback if forecasting process crashes"""
        return {
            "prediction": 0.5,
            "direction": "UP",
            "probability": 0.5,
            "timeframe": "4h",
            "uncertainty": 0.1,
            "error_fallback": str(error)
        }

# clean architecture alignment
