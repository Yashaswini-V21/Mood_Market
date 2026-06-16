import logging
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger("sources.trends")


class GoogleTrendsSourceClient:
    """Wrapper around pytrends for fetching Google Trends interest scores."""
    
    def __init__(self):
        # We can configure if it is mock
        # Pytrends connects to Google, which is frequently rate-limited (429).
        # We will use pytrends, but if it fails/rate-limits, we fall back to mock trends.
        self.is_mock = False

    def fetch_trends(self, ticker: str, timeframe: str = "now 7-d", geo: str = "") -> List[Dict[str, Any]]:
        """
        Queries pytrends for ticker search interest.
        If it fails or gets rate limited, returns simulated trends.
        """
        ticker = ticker.upper().strip()
        try:
            from pytrends.request import TrendReq
            # pytrends has rate limits, so we add a timeout and retries
            pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25), retries=2, backoff_factor=0.5)
            pytrends.build_payload([ticker], cat=0, timeframe=timeframe, geo=geo, gprop='')
            df = pytrends.interest_over_time()
            
            if df.empty or ticker not in df.columns:
                logger.warning(f"pytrends returned empty or missing column for {ticker}. Generating simulated trends.")
                return self._generate_simulated_trends(ticker, 100)
                
            trends = []
            for timestamp, row in df.iterrows():
                # Google Trends index is usually 0 to 100
                val = float(row[ticker])
                trends.append({
                    "id": f"trends_{ticker}_{int(timestamp.timestamp())}",
                    "ticker": ticker,
                    "timestamp": timestamp.isoformat(),
                    "interest": val
                })
            return trends
        except Exception as e:
            logger.warning(f"pytrends query failed for {ticker}: {e}. Falling back to simulated trends.")
            return self._generate_simulated_trends(ticker, 100)

    def _generate_simulated_trends(self, ticker: str, count: int) -> List[Dict[str, Any]]:
        import random
        import numpy as np
        # Generate trend with some autocorrelation and noise
        np.random.seed(42)
        base_interest = 50.0
        interest_values = []
        for _ in range(count):
            change = np.random.normal(0, 3)
            base_interest = max(0.0, min(100.0, base_interest + change))
            interest_values.append(base_interest)
            
        trends = []
        base_time = datetime.utcnow() - timedelta(hours=count)
        for i in range(count):
            trend_time = base_time + timedelta(hours=i)
            # Add a random spike for fun (hype storms)
            val = interest_values[i]
            if random.random() < 0.05:
                val = min(100.0, val + random.randint(20, 40))
                
            trends.append({
                "id": f"sim_trends_{ticker}_{int(trend_time.timestamp())}",
                "ticker": ticker,
                "timestamp": trend_time.isoformat(),
                "interest": float(val)
            })
        return trends

# clean architecture alignment
