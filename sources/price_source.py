import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger("sources.price")


class PriceSourceClient:
    """Wrapper around yfinance to pull historical price intervals."""
    
    def __init__(self):
        pass

    def fetch_price_history(self, ticker: str, interval: str = "15m", period: str = "5d") -> List[Dict[str, Any]]:
        """
        Fetches candle intervals for a stock ticker from Yahoo Finance.
        Exposed keys: [timestamp, open, high, low, close, volume]
        """
        ticker = ticker.upper().strip()
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"yfinance returned empty DataFrame for {ticker}. Generating simulated candles.")
                return self._generate_simulated_candles(ticker, interval, 100)
                
            candles = []
            for timestamp, row in df.iterrows():
                candles.append({
                    "id": f"price_{ticker}_{int(timestamp.timestamp())}",
                    "ticker": ticker,
                    "timestamp": timestamp.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"])
                })
            return candles
        except Exception as e:
            logger.warning(f"yfinance download failed for {ticker}: {e}. Falling back to simulated candles.")
            return self._generate_simulated_candles(ticker, interval, 100)

    def _generate_simulated_candles(self, ticker: str, interval: str, count: int) -> List[Dict[str, Any]]:
        """Generates realistic stock price intervals via a geometric Brownian motion random walk."""
        np.random.seed(42)
        prices = [150.0]
        for _ in range(count):
            change = np.random.normal(0.0002, 0.005)
            prices.append(prices[-1] * (1.0 + change))
            
        candles = []
        base_time = datetime.utcnow() - timedelta(minutes=count * 15)
        for i in range(count):
            p = prices[i]
            o = p * (1 + np.random.normal(0, 0.001))
            h = max(p, o) * (1 + abs(np.random.normal(0, 0.002)))
            l = min(p, o) * (1 - abs(np.random.normal(0, 0.002)))
            v = int(np.random.lognormal(12, 0.5))
            
            candle_time = base_time + timedelta(minutes=i * 15)
            candles.append({
                "id": f"sim_price_{ticker}_{int(candle_time.timestamp())}",
                "ticker": ticker,
                "timestamp": candle_time.isoformat(),
                "open": o,
                "high": h,
                "low": l,
                "close": p,
                "volume": float(v)
            })
        return candles
