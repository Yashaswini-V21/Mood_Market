import pandas as pd
import numpy as np
from typing import List, Dict, Any

class TechnicalIndicatorEnricher:
    """Calculates technical indicators (RSI, MACD, Bollinger Bands width) for price candles."""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index (RSI) calculation using simple moving average of gains/losses."""
        if len(prices) < period:
            return pd.Series(50.0, index=prices.index)
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)

    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
        """Moving Average Convergence Divergence (MACD) line calculation (12 EMA - 26 EMA)."""
        if len(prices) < slow:
            return pd.Series(0.0, index=prices.index)
            
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        return macd_line.fillna(0.0)

    @staticmethod
    def calculate_bollinger_bands_width(prices: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.Series:
        """Bollinger Bands Width calculation ((Upper Band - Lower Band) / SMA)."""
        if len(prices) < period:
            return pd.Series(0.0, index=prices.index)
            
        sma = prices.rolling(window=period).mean()
        rstd = prices.rolling(window=period).std()
        upper_band = sma + (num_std * rstd)
        lower_band = sma - (num_std * rstd)
        width = (upper_band - lower_band) / (sma + 1e-9)
        return width.fillna(0.0)

    def enrich_candles(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes a list of candle dictionaries (sorted chronologically).
        Calculates indicators and injects them under keys 'RSI', 'MACD', and 'Bollinger_Band'.
        """
        if not candles:
            return []
            
        df = pd.DataFrame(candles)
        # Ensure chronological order
        df['parsed_time'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('parsed_time').reset_index(drop=True)
        
        close_prices = df['close']
        
        # Enrich
        df['RSI'] = self.calculate_rsi(close_prices)
        df['MACD'] = self.calculate_macd(close_prices)
        df['Bollinger_Band'] = self.calculate_bollinger_bands_width(close_prices)
        
        # Remove helper columns and cast NaN
        df = df.drop(columns=['parsed_time'])
        df = df.fillna({
            "RSI": 50.0,
            "MACD": 0.0,
            "Bollinger_Band": 0.0
        })
        
        return df.to_dict(orient='records')

# clean architecture alignment
