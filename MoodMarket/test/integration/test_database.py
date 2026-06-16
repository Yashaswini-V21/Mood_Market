# c:\Mood_Market\tests\test_schema.py
import os
import sys
import asyncio
from datetime import datetime, timedelta
import unittest

# Add project root directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import engine, run_all_migrations, get_db_session
from schema import (
    SentimentDataModel,
    PriceDataModel,
    TechnicalIndicatorModel,
    AnomalyModel,
    PredictionModel
)
from queries import (
    insert_sentiment,
    insert_price,
    insert_indicator,
    insert_prediction,
    insert_anomaly,
    insert_api_log,
    get_historical_prices,
    get_daily_sentiment_averages,
    get_hourly_price_ranges,
    get_weekly_returns,
    query_anomalies_by_type
)


class TestDatabaseSchemaAndQueries(unittest.IsolatedAsyncioTestCase):
    """Verifies TimescaleDB migrations execution, constraint structures, and range queries."""

    async def asyncSetUp(self):
        # 1. Run migrations to initialize schema (Postgres or SQLite fallback)
        await run_all_migrations()
        # 2. Clean tables to guarantee test case isolation
        from sqlalchemy import text
        async for session in get_db_session():
            await session.execute(text("DELETE FROM price_data"))
            await session.execute(text("DELETE FROM sentiment_data"))
            await session.commit()


        
    async def test_insert_and_query_price(self):
        now = datetime.utcnow()
        # Create a valid price model
        price_model = PriceDataModel(
            time=now,
            ticker="AAPL",
            open=175.50,
            high=176.20,
            low=174.80,
            close=175.90,
            volume=5000000.0,
            vwap=175.60
        )
        
        async for session in get_db_session():
            await insert_price(session, price_model)
            
        # Retrieve and verify
        async for session in get_db_session():
            prices = await get_historical_prices(
                session,
                ticker="AAPL",
                start_time=now - timedelta(minutes=5),
                end_time=now + timedelta(minutes=5)
            )
            self.assertEqual(len(prices), 1)
            self.assertEqual(prices[0]["ticker"], "AAPL")
            self.assertEqual(prices[0]["close"], 175.90)

    async def test_insert_and_query_sentiment(self):
        now = datetime.utcnow()
        sentiment_model = SentimentDataModel(
            time=now,
            ticker="MSFT",
            sentiment_score=0.85,
            confidence=0.92,
            source="reddit",
            text_sample="Microsoft surges following high Azure quarterly earnings guidance.",
            model_version="v1.0"
        )
        
        async for session in get_db_session():
            await insert_sentiment(session, sentiment_model)
            
        # We also want to verify that the daily average view aggregates sentiment records.
        # Note: continuous aggregates or SQLite normal views aggregate correctly.
        async for session in get_db_session():
            averages = await get_daily_sentiment_averages(
                session,
                ticker="MSFT",
                start_time=now - timedelta(days=1),
                end_time=now + timedelta(days=1)
            )
            self.assertEqual(len(averages), 1)
            self.assertEqual(averages[0]["ticker"], "MSFT")
            self.assertEqual(averages[0]["avg_sentiment"], 0.85)

    def test_schema_constraints_validation(self):
        # Pydantic constraint: sentiment out of range
        with self.assertRaises(ValueError):
            SentimentDataModel(
                time=datetime.utcnow(),
                ticker="GOOGL",
                sentiment_score=2.5, # Out of range (-1 to 1)
                confidence=0.8,
                source="news",
                model_version="v1"
            )

        # Pydantic constraint: high price less than low price
        with self.assertRaises(ValueError):
            PriceDataModel(
                time=datetime.utcnow(),
                ticker="AMZN",
                open=100.0,
                high=95.0, # High is less than open
                low=90.0,
                close=98.0,
                volume=1000.0,
                vwap=96.0
            )


if __name__ == "__main__":
    unittest.main()

# clean architecture alignment
