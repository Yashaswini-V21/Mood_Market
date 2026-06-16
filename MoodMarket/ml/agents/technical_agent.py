import numpy as np
import logging
from typing import Dict, Any, List
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class TechnicalAgent(BaseAgent):
    """
    Technical Analyst Agent
    
    Inputs: Price series, volume series
    Task: Calculate indicators (RSI, MACD, Bollinger Bands, support/resistance)
    Outputs: rsi, macd_signal, support, resistance, strength, confirmation, technical_signal
    """
    
    def __init__(self, config: Dict[str, Any], cache_ttl: int = 300):
        super().__init__("technical_analyst", config, cache_ttl)
        self.rsi_period = config.get("rsi", {}).get("period", 14)
        self.rsi_overbought = config.get("rsi", {}).get("overbought", 70.0)
        self.rsi_oversold = config.get("rsi", {}).get("oversold", 30.0)
        
        self.macd_fast = config.get("macd", {}).get("fast_period", 12)
        self.macd_slow = config.get("macd", {}).get("slow_period", 26)
        self.macd_signal = config.get("macd", {}).get("signal_period", 9)
        
        self.bb_period = config.get("bollinger_bands", {}).get("period", 20)
        self.bb_std = config.get("bollinger_bands", {}).get("std_dev", 2.0)
        
        self.sr_window = config.get("support_resistance", {}).get("window", 20)
        
    def get_relevant_input_keys(self) -> list:
        return ["prices", "volumes"]
        
    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return [float(np.mean(prices))] * len(prices)
            
        ema = []
        multiplier = 2 / (period + 1)
        
        # Start with SMA for first element
        sma = sum(prices[:period]) / period
        ema.append(sma)
        
        for price in prices[period:]:
            next_ema = (price - ema[-1]) * multiplier + ema[-1]
            ema.append(next_ema)
            
        # Pad front with SMA to match original list length
        padding = [sma] * (len(prices) - len(ema))
        return padding + ema

    def _calculate_rsi(self, prices: List[float]) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < self.rsi_period + 1:
            return 50.0  # Default neutral RSI
            
        deltas = np.diff(prices)
        seed = deltas[:self.rsi_period]
        up = seed[seed >= 0].sum() / self.rsi_period
        down = -seed[seed < 0].sum() / self.rsi_period
        
        if down == 0:
            return 100.0
        
        rs = up / down
        rsi = np.zeros(len(prices))
        rsi[:self.rsi_period] = 100.0 - (100.0 / (1.0 + rs))
        
        for i in range(self.rsi_period, len(prices) - 1):
            delta = deltas[i]
            if delta > 0:
                upval = delta
                downval = 0.0
            else:
                upval = 0.0
                downval = -delta
                
            up = (up * (self.rsi_period - 1) + upval) / self.rsi_period
            down = (down * (self.rsi_period - 1) + downval) / self.rsi_period
            
            if down == 0:
                rsi[i + 1] = 100.0
            else:
                rs = up / down
                rsi[i + 1] = 100.0 - (100.0 / (1.0 + rs))
                
        return float(rsi[-1])

    def _calculate_macd(self, prices: List[float]) -> tuple:
        """Calculate MACD line, signal line and crossover status"""
        if len(prices) < self.macd_slow + self.macd_signal:
            return 0.0, 0.0, "NEUTRAL"
            
        ema_fast = self._calculate_ema(prices, self.macd_fast)
        ema_slow = self._calculate_ema(prices, self.macd_slow)
        
        macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
        signal_line = self._calculate_ema(macd_line, self.macd_signal)
        
        curr_macd = macd_line[-1]
        curr_sig = signal_line[-1]
        prev_macd = macd_line[-2]
        prev_sig = signal_line[-2]
        
        # Detect Crossover
        if prev_macd <= prev_sig and curr_macd > curr_sig:
            signal_status = "BULLISH_CROSSOVER"
        elif prev_macd >= prev_sig and curr_macd < curr_sig:
            signal_status = "BEARISH_CROSSOVER"
        elif curr_macd > curr_sig:
            signal_status = "BULLISH"
        elif curr_macd < curr_sig:
            signal_status = "BEARISH"
        else:
            signal_status = "NEUTRAL"
            
        return curr_macd, curr_sig, signal_status

    def _calculate_bollinger_bands(self, prices: List[float]) -> tuple:
        """Calculate Bollinger Bands"""
        if len(prices) < self.bb_period:
            return float(prices[-1]), float(prices[-1]), float(prices[-1])
            
        recent_prices = prices[-self.bb_period:]
        sma = float(np.mean(recent_prices))
        std = float(np.std(recent_prices))
        
        upper_band = sma + self.bb_std * std
        lower_band = sma - self.bb_std * std
        
        return lower_band, sma, upper_band

    def _calculate_support_resistance(self, prices: List[float]) -> tuple:
        """Identify local support and resistance lines"""
        if len(prices) < self.sr_window:
            return float(min(prices)), float(max(prices))
            
        recent_prices = prices[-self.sr_window:]
        support = float(np.min(recent_prices))
        resistance = float(np.max(recent_prices))
        
        # Adjust if support and resistance are identical
        if support == resistance:
            support = support * 0.99
            resistance = resistance * 1.01
            
        return support, resistance

    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prices = payload.get("prices", [])
        volumes = payload.get("volumes", [])
        
        # Convert types safely
        if isinstance(prices, np.ndarray):
            prices = prices.tolist()
        if isinstance(volumes, np.ndarray):
            volumes = volumes.tolist()
            
        if not prices:
            self.logger.warning("No price series found in technical analyst payload.")
            return self.get_fallback_output(payload, ValueError("Missing prices"))
            
        current_price = prices[-1]
        
        # 1. RSI
        rsi_val = self._calculate_rsi(prices)
        
        # 2. MACD
        macd_val, macd_sig, macd_signal_status = self._calculate_macd(prices)
        
        # 3. Bollinger Bands
        bb_lower, bb_mid, bb_upper = self._calculate_bollinger_bands(prices)
        
        # 4. Support and Resistance
        support, resistance = self._calculate_support_resistance(prices)
        
        # 5. Core decision rules
        # Determine signals
        signals = []
        if rsi_val < self.rsi_oversold:
            signals.append("BULLISH_RSI")
        elif rsi_val > self.rsi_overbought:
            signals.append("BEARISH_RSI")
            
        if "BULLISH" in macd_signal_status:
            signals.append("BULLISH_MACD")
        elif "BEARISH" in macd_signal_status:
            signals.append("BEARISH_MACD")
            
        if current_price < bb_lower:
            signals.append("BULLISH_OVERSOLD_BB")
        elif current_price > bb_upper:
            signals.append("BEARISH_OVERBOUGHT_BB")
            
        # Strength logic
        bullish_indicators = sum(1 for s in signals if "BULLISH" in s)
        bearish_indicators = sum(1 for s in signals if "BEARISH" in s)
        
        if bullish_indicators > bearish_indicators:
            technical_signal = "BUY"
            strength = "STRONG" if bullish_indicators >= 2 else "WEAK"
        elif bearish_indicators > bullish_indicators:
            technical_signal = "SELL"
            strength = "STRONG" if bearish_indicators >= 2 else "WEAK"
        else:
            technical_signal = "HOLD"
            strength = "NEUTRAL"
            
        # Confirmation flag
        # Confirmed if current price trend aligns with technical indicators
        # e.g., MACD crossover agrees with technical signal
        confirmation = "NEUTRAL"
        if technical_signal == "BUY":
            if "CROSSOVER" in macd_signal_status:
                confirmation = "CONFIRMED"
            else:
                confirmation = "UNCONFIRMED"
        elif technical_signal == "SELL":
            if "CROSSOVER" in macd_signal_status:
                confirmation = "CONFIRMED"
            else:
                confirmation = "UNCONFIRMED"
                
        return {
            "rsi": float(round(rsi_val, 2)),
            "macd_signal": macd_signal_status,
            "support": float(round(support, 2)),
            "resistance": float(round(resistance, 2)),
            "strength": strength,
            "confirmation": confirmation,
            "technical_signal": technical_signal,
            "bollinger_bands": {
                "lower": float(round(bb_lower, 2)),
                "mid": float(round(bb_mid, 2)),
                "upper": float(round(bb_upper, 2))
            }
        }
        
    def get_fallback_output(self, payload: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Neutral baseline technical analyst fallback"""
        last_price = 100.0
        if payload.get("prices"):
            last_price = float(payload.get("prices")[-1])
            
        return {
            "rsi": 50.0,
            "macd_signal": "NEUTRAL",
            "support": float(round(last_price * 0.95, 2)),
            "resistance": float(round(last_price * 1.05, 2)),
            "strength": "NEUTRAL",
            "confirmation": "NEUTRAL",
            "technical_signal": "HOLD",
            "bollinger_bands": {
                "lower": float(round(last_price * 0.95, 2)),
                "mid": float(round(last_price, 2)),
                "upper": float(round(last_price * 1.05, 2))
            },
            "error_fallback": str(error)
        }

# clean architecture alignment
