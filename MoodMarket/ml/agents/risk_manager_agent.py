import logging
from typing import Dict, Any
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class RiskManagerAgent(BaseAgent):
    """
    Risk Manager Agent
    
    Inputs: Forecaster prediction, current price, account size, risk config
    Task: Calculate recommended position sizing, stop-loss, and take-profit levels
    Outputs: recommended_position_size, stop_loss, take_profit, max_loss
    """
    
    def __init__(self, config: Dict[str, Any], cache_ttl: int = 300):
        super().__init__("risk_manager", config, cache_ttl)
        self.default_size_str = config.get("default_position_size", "2%")
        self.stop_loss_pct = config.get("stop_loss_pct", 0.02)
        self.take_profit_pct = config.get("take_profit_pct", 0.05)
        self.max_loss_usd_limit = config.get("max_loss_usd", 150.0)
        
    def get_relevant_input_keys(self) -> list:
        return ["prices", "agents", "account_size"]
        
    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prices = payload.get("prices", [])
        if not prices:
            return self.get_fallback_output(payload, ValueError("Missing prices"))
            
        current_price = float(prices[-1])
        
        # Get forecaster outputs
        forecaster_data = payload.get("agents", {}).get("forecaster", {})
        direction = forecaster_data.get("direction", "UP")
        probability = forecaster_data.get("probability", 0.5)
        
        # Get account size (default to $10,000)
        account_size = float(payload.get("account_size", 10000.0))
        
        # Parse default position size percentage (e.g. "2%" -> 0.02)
        try:
            base_size_pct = float(self.default_size_str.strip().replace("%", "")) / 100.0
        except ValueError:
            base_size_pct = 0.02
            
        # Adjust position size based on prediction confidence (probability)
        # Scale sizing between 0.5x and 1.5x of base size based on prediction confidence
        confidence_multiplier = 1.0
        if probability > 0.7:
            confidence_multiplier = 1.5
        elif probability < 0.55:
            confidence_multiplier = 0.5
            
        final_size_pct = base_size_pct * confidence_multiplier
        # Format back to percentage string
        recommended_size = f"{int(final_size_pct * 100)}%"
        
        # Calculate levels depending on long (UP) or short (DOWN) direction
        if direction == "UP":
            stop_loss = current_price * (1.0 - self.stop_loss_pct)
            take_profit = current_price * (1.0 + self.take_profit_pct)
        else:
            # Short position levels
            stop_loss = current_price * (1.0 + self.stop_loss_pct)
            take_profit = current_price * (1.0 - self.take_profit_pct)
            
        # Exposure = Position Value (USD)
        exposure = account_size * final_size_pct
        
        # Calculate max loss if stop loss is hit
        max_loss = exposure * self.stop_loss_pct
        
        # Clip max loss to USD limit to prevent oversized risk exposure
        if max_loss > self.max_loss_usd_limit:
            max_loss = self.max_loss_usd_limit
            # Adjust position size down to match the loss limit
            adjusted_exposure = max_loss / self.stop_loss_pct
            final_size_pct = adjusted_exposure / account_size
            recommended_size = f"{round(final_size_pct * 100, 1)}%"
            
        return {
            "recommended_position_size": recommended_size,
            "stop_loss": float(round(stop_loss, 2)),
            "take_profit": float(round(take_profit, 2)),
            "max_loss": float(round(max_loss, 2))
        }
        
    def get_fallback_output(self, payload: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Provides a safe, low-risk default fallback output"""
        prices = payload.get("prices", [100.0])
        current_price = float(prices[-1])
        
        return {
            "recommended_position_size": "1%",
            "stop_loss": float(round(current_price * 0.98, 2)),
            "take_profit": float(round(current_price * 1.02, 2)),
            "max_loss": 50.0,
            "error_fallback": str(error)
        }
