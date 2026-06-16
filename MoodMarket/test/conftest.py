import os
import pytest
from typing import AsyncGenerator, Generator, Optional
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Set test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["ENV"] = "test"
os.environ["TIMESCALEDB_URI"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URI"] = "redis://localhost:6379/9"
os.environ["REDIS_URL"] = "redis://localhost:6379/9"

from main import app
from dependencies import get_db, get_redis
from config import api_settings


# Create memory database engine
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


import asyncio

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Initializes tables in the memory SQLite database for tests."""
    from sqlalchemy import text
    async def _init():
        async with test_engine.begin() as conn:
            # Create records tables
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS sentiment_records ("
                "id VARCHAR(64) PRIMARY KEY, "
                "ticker VARCHAR(16), "
                "sentiment FLOAT, "
                "confidence FLOAT, "
                "timestamp TIMESTAMP"
                ")"
            ))
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS forecast_records ("
                "id VARCHAR(64) PRIMARY KEY, "
                "ticker VARCHAR(16), "
                "prediction FLOAT, "
                "confidence FLOAT, "
                "direction VARCHAR(8), "
                "timestamp TIMESTAMP"
                ")"
            ))
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS price_records ("
                "id VARCHAR(64) PRIMARY KEY, "
                "ticker VARCHAR(16), "
                "timestamp TIMESTAMP, "
                "open FLOAT, "
                "high FLOAT, "
                "low FLOAT, "
                "close FLOAT, "
                "volume FLOAT, "
                "RSI FLOAT, "
                "MACD FLOAT, "
                "Bollinger_Band FLOAT, "
                "google_trends FLOAT, "
                "reddit_hype FLOAT, "
                "sentiment_score FLOAT"
                ")"
            ))
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS anomaly_records ("
                "id VARCHAR(64) PRIMARY KEY, "
                "ticker VARCHAR(16), "
                "anomaly_detected BOOLEAN, "
                "confidence FLOAT, "
                "alert_level VARCHAR(16), "
                "timestamp TIMESTAMP"
                ")"
            ))
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS watchlist_records ("
                "id VARCHAR(64) PRIMARY KEY, "
                "user_id VARCHAR(64) UNIQUE, "
                "tickers TEXT"
                ")"
            ))
    asyncio.run(_init())
    yield
    asyncio.run(test_engine.dispose())




@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated database session for each test case."""
    async with TestSessionLocal() as session:
        yield session
        # Rollback any changes
        await session.rollback()


class MockRedis:
    """A synchronous/asynchronous helper mock for Redis operations in testing."""
    def __init__(self):
        self.store = {}

    async def get(self, key: str) -> Optional[str]:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int = None) -> bool:
        self.store[key] = value
        return True

    async def delete(self, key: str) -> int:
        if key in self.store:
            del self.store[key]
            return 1
        return 0

    async def flushdb(self) -> bool:
        self.store.clear()
        return True


@pytest.fixture
def mock_redis() -> MockRedis:
    """Fixture to provide a clean mock Redis database."""
    return MockRedis()


@pytest.fixture
def client(mock_redis) -> Generator[TestClient, None, None]:
    """FastAPI TestClient fixture with dependency overrides for database and Redis."""
    # Override database dependency
    async def _get_test_db():
        async with TestSessionLocal() as session:
            yield session
            await session.rollback()

    # Override Redis dependency
    async def _get_test_redis():
        yield mock_redis

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_redis] = _get_test_redis

    with TestClient(app) as test_client:
        test_client.headers.update({"Authorization": f"Bearer {api_settings.api_key}"})
        yield test_client

    # Clean overrides
    app.dependency_overrides.clear()



# clean architecture alignment
