# c:\Mood_Market\broadcaster.py
import asyncio
import logging
import random
from datetime import datetime
from typing import List

from channel_manager import ChannelManager
from database import get_db_session
from sqlalchemy import text

logger = logging.getLogger("broadcaster")


class RealTimeBroadcaster:
    """Orchestrates periodic scheduled data pushes and real-time event-driven alerts."""
    
    def __init__(self, manager: ChannelManager, tickers: List[str] = None):
        self.manager = manager
        self.tickers = [t.upper().strip() for t in (tickers or ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"])]
        self.tasks: List[asyncio.Task] = []

    def start(self):
        """Launches all background broadcast loops inside the running event loop."""
        self.tasks.append(asyncio.create_task(self._price_loop()))
        self.tasks.append(asyncio.create_task(self._sentiment_loop()))
        self.tasks.append(asyncio.create_task(self._prediction_loop()))
        logger.info("RealTimeBroadcaster background update routines started.")

    def stop(self):
        """Cancels all active background loops."""
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()
        logger.info("RealTimeBroadcaster background update routines stopped.")

    async def trigger_anomaly_alert(self, ticker: str, anomaly_type: str, confidence: float, explanation: str = None):
        """Event-driven alert pushed immediately to all anomaly channel subscribers."""
        alert_payload = {
            "ticker": ticker.upper(),
            "anomaly_type": anomaly_type,
            "confidence": float(confidence),
            "explanation": explanation or "Statistical spike detected.",
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.manager.broadcast("anomaly", alert_payload)

    async def _price_loop(self):
        """Pushes price updates every 1 minute (frequency: 60s)."""
        while True:
            # Sleep 60 seconds (or speed up for testing if needed)
            await asyncio.sleep(60.0)
            for ticker in self.tickers:
                # Query database for latest price candle
                close_price = 150.0
                change = 0.0
                change_pct = 0.0
                
                async for session in get_db_session():
                    try:
                        query = text(
                            "SELECT close, open FROM price_data WHERE ticker = :ticker "
                            "ORDER BY time DESC LIMIT 2"
                        )
                        res = await session.execute(query, {"ticker": ticker})
                        rows = res.fetchall()
                        if rows:
                            close_price = float(rows[0][0])
                            # Calculate change from previous close
                            prev = float(rows[1][0]) if len(rows) > 1 else float(rows[0][1])
                            change = close_price - prev
                            change_pct = (change / prev) * 100.0 if prev > 0 else 0.0
                    except Exception as e:
                        logger.warning(f"Could not retrieve price updates from db for {ticker}: {e}. Generating ticks.")
                        # Mock ticks fallback for visual dashboard demo
                        change = random.normalvariate(0.0, 1.0)
                        close_price = max(10.0, 180.0 + change)
                        change_pct = (change / 180.0) * 100.0
                
                payload = {
                    "price": round(close_price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 4),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await self.manager.broadcast(f"price:{ticker}", payload)

    async def _sentiment_loop(self):
        """Pushes sentiment updates every 5 minutes (frequency: 300s)."""
        while True:
            await asyncio.sleep(300.0)
            for ticker in self.tickers:
                sentiment = 0.15
                confidence = 0.82
                
                async for session in get_db_session():
                    try:
                        query = text(
                            "SELECT sentiment_score, confidence FROM sentiment_data WHERE ticker = :ticker "
                            "ORDER BY time DESC LIMIT 1"
                        )
                        res = await session.execute(query, {"ticker": ticker})
                        row = res.fetchone()
                        if row:
                            sentiment = float(row[0])
                            confidence = float(row[1])
                    except Exception as e:
                        logger.warning(f"Could not retrieve sentiment updates from db for {ticker}: {e}")
                        sentiment = random.uniform(-0.5, 0.7)
                        confidence = random.uniform(0.6, 0.95)
                        
                payload = {
                    "sentiment": round(sentiment, 4),
                    "confidence": round(confidence, 4),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                await self.manager.broadcast(f"sentiment:{ticker}", payload)

    async def _prediction_loop(self):
        """Pushes price predictions every 15 minutes (frequency: 900s)."""
        while True:
            await asyncio.sleep(900.0)
            for ticker in self.tickers:
                prob = 0.55
                confidence = 0.05
                direction = "UP"
                
                async for session in get_db_session():
                    try:
                        query = text(
                            "SELECT predicted_price, confidence, predicted_direction FROM predictions "
                            "WHERE ticker = :ticker ORDER BY time DESC LIMIT 1"
                        )
                        res = await session.execute(query, {"ticker": ticker})
                        row = res.fetchone()
                        if row:
                            prob = float(row[0])
                            confidence = float(row[1])
                            direction = str(row[2])
                    except Exception as e:
                        logger.warning(f"Could not retrieve prediction updates from db for {ticker}: {e}")
                        prob = random.uniform(0.3, 0.8)
                        confidence = random.uniform(0.02, 0.10)
                        direction = "UP" if prob > 0.5 else "DOWN"
                        
                payload = {
                    "prediction": round(prob, 4),
                    "confidence": round(confidence, 4),
                    "direction": direction.upper()
                }
                
                await self.manager.broadcast(f"prediction:{ticker}", payload)
