import logging
from typing import Dict, Any
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class SynthesizerAgent(BaseAgent):
    """
    Synthesizer Agent (Master Agent)
    
    Inputs: Outputs from Sentiment, Technical, Forecaster, and Risk Manager agents
    Task: Aggregate inputs, compute weighted confidence, and generate trading recommendation summary report
    Outputs: summary, confidence, recommendation
    """
    
    def __init__(self, config: Dict[str, Any], cache_ttl: int = 300):
        super().__init__("synthesizer", config, cache_ttl)
        self.weights = config.get("confidence_weights", {
            "sentiment": 0.3,
            "technical": 0.3,
            "forecasting": 0.4
        })
        
    def get_relevant_input_keys(self) -> list:
        return ["agents"]
        
    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        agents_data = payload.get("agents", {})
        
        # 1. Pull individual agent reports
        sent_data = agents_data.get("sentiment_analyst", {})
        tech_data = agents_data.get("technical_analyst", {})
        fore_data = agents_data.get("forecaster", {})
        risk_data = agents_data.get("risk_manager", {})
        
        # 2. Extract values
        sentiment_score = sent_data.get("sentiment", 0.0)
        social_momentum = sent_data.get("social_momentum", "NEUTRAL")
        key_topics = sent_data.get("key_topics", ["market"])
        
        rsi = tech_data.get("rsi", 50.0)
        macd = tech_data.get("macd_signal", "NEUTRAL")
        tech_signal = tech_data.get("technical_signal", "HOLD")
        tech_strength = tech_data.get("strength", "NEUTRAL")
        
        fore_direction = fore_data.get("direction", "UP")
        fore_prob = fore_data.get("probability", 0.5)
        fore_timeframe = fore_data.get("timeframe", "4h")
        
        risk_size = risk_data.get("recommended_position_size", "1%")
        stop_loss = risk_data.get("stop_loss", 0.0)
        take_profit = risk_data.get("take_profit", 0.0)
        
        # 3. Compute Weighted Confidence
        # Sentiment confidence
        sent_conf = sent_data.get("confidence", 0.5)
        # Technical confidence mapping
        tech_conf = 0.5
        if tech_strength == "STRONG":
            tech_conf = 0.85 if tech_data.get("confirmation") == "CONFIRMED" else 0.7
        elif tech_strength == "WEAK":
            tech_conf = 0.6
            
        # Forecasting confidence is the directional probability
        fore_conf = fore_prob
        
        # Calculate weighted confidence
        w_s = self.weights.get("sentiment", 0.3)
        w_t = self.weights.get("technical", 0.3)
        w_f = self.weights.get("forecasting", 0.4)
        
        weighted_conf = (sent_conf * w_s) + (tech_conf * w_t) + (fore_conf * w_f)
        weighted_conf = float(round(weighted_conf, 2))
        
        # 4. Synthesizer Recommendation and Summary
        # Simple agreement engine
        signals_align = False
        recommendation = "HOLD"
        
        if fore_direction == "UP" and tech_signal == "BUY":
            signals_align = True
            if sentiment_score > 0.2:
                recommendation = "BUY" if weighted_conf > 0.75 else "BUY_WITH_CAUTION"
            else:
                recommendation = "BUY_WITH_CAUTION"
        elif fore_direction == "DOWN" and tech_signal == "SELL":
            signals_align = True
            if sentiment_score < -0.2:
                recommendation = "SELL" if weighted_conf > 0.75 else "SELL_WITH_CAUTION"
            else:
                recommendation = "SELL_WITH_CAUTION"
        elif tech_signal == "BUY":
            recommendation = "BUY_WITH_CAUTION"
        elif tech_signal == "SELL":
            recommendation = "SELL_WITH_CAUTION"
            
        # If there are extreme warnings or high risk metrics
        if payload.get("anomaly_detected") or payload.get("alert_type") == "HYPE_STORM":
            # Override to warning
            recommendation = "REDUCE_POSITION_SIZE"
            
        # Coherent Summary Construction
        summary_parts = []
        summary_parts.append(
            f"Sentiment is {social_momentum} (score: {sentiment_score:+.2f}) focusing on topics: {', '.join(key_topics)}."
        )
        summary_parts.append(
            f"Technical indicators show a {tech_signal} signal (RSI: {rsi}, MACD: {macd}) with {tech_strength.lower()} strength."
        )
        summary_parts.append(
            f"Forecaster model predicts price moving {fore_direction} with {int(fore_prob * 100)}% probability in next {fore_timeframe}."
        )
        
        if recommendation == "REDUCE_POSITION_SIZE":
            summary_parts.append("Hype storm or anomaly detected on social media. Recommendation is to REDUCE position sizes immediately.")
        else:
            summary_parts.append(
                f"We recommend {recommendation.replace('_', ' ')}: position sizing is {risk_size} with stop loss at {stop_loss} and take profit at {take_profit}."
            )
            
        summary = " ".join(summary_parts)
        
        return {
            "summary": summary,
            "confidence": weighted_conf,
            "recommendation": recommendation
        }
        
    def get_fallback_output(self, payload: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Synthesizer fallback output"""
        return {
            "summary": "Error occurred during agent synthesis. Falling back to default HOLD strategy.",
            "confidence": 0.5,
            "recommendation": "HOLD",
            "error_fallback": str(error)
        }
