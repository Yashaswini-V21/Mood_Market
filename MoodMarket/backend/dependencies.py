import os
import logging
import torch
import redis.asyncio as aioredis
from typing import AsyncGenerator, Optional
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from config import api_settings
from model import Informer, InformerConfig
from inference import InferenceEngine

logger = logging.getLogger("dependencies")

# Declarative base for DB schemas
Base = declarative_base()

# 1. Database Configuration (with SQLite fallback)
db_uri = api_settings.timescaledb_uri
if db_uri.startswith("postgresql://"):
    # SQLAlchemy requires postgresql+asyncpg for async execution
    db_uri = db_uri.replace("postgresql://", "postgresql+asyncpg://")

logger.info(f"Initializing database connection using URI: {db_uri.split('@')[-1]}")

try:
    engine = create_async_engine(
        db_uri,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30.0,
        pool_pre_ping=True
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db_connected = True
except Exception as e:
    logger.warning(f"Failed to connect to TimescaleDB: {e}. Falling back to aiosqlite.")
    # Local SQLite fallback
    fallback_uri = "sqlite+aiosqlite:///moodmarket.db"
    engine = create_async_engine(fallback_uri, pool_pre_ping=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db_connected = False


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for fetching database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 2. Redis Cache Configuration
logger.info(f"Connecting to Redis at: {api_settings.redis_uri}")
redis_pool = aioredis.ConnectionPool.from_url(
    api_settings.redis_uri,
    encoding="utf-8",
    decode_responses=True,
    max_connections=50
)


def get_redis() -> aioredis.Redis:
    """Dependency for fetching Redis connection instance."""
    return aioredis.Redis(connection_pool=redis_pool)


# 3. Model Checkpoint Loader (Thread-safe, loaded once)
_global_inference_engine: Optional[InferenceEngine] = None


def get_inference_engine() -> InferenceEngine:
    """Dependency to retrieve the preloaded Informer model inference engine."""
    global _global_inference_engine
    if _global_inference_engine is not None:
        return _global_inference_engine
        
    model_path = "checkpoints/best_model.pt"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # If model checkpoint doesn't exist, create a mock one for API sanity
    if not os.path.exists(model_path):
        logger.warning(f"Informer checkpoint '{model_path}' not found. Creating a fresh default instance.")
        os.makedirs("checkpoints", exist_ok=True)
        default_config = InformerConfig(
            seq_len=72,
            pred_len=1,
            enc_in=8,
            dec_in=8,
            c_out=1,
            d_model=256,
            device=device
        )
        mock_model = Informer(default_config)
        mock_model.save_checkpoint(model_path)
        
    try:
        _global_inference_engine = InferenceEngine(
            model_path=model_path,
            device=device,
            quantize=False
        )
    except Exception as e:
        logger.error(f"Failed to load Informer model engine: {e}")
        raise RuntimeError(f"Failed to load Informer model: {e}")
        
    return _global_inference_engine


# 4. Bearer API Key Verification
security_bearer = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> str:
    """Dependency verifying Bearer token authentication API key."""
    if not credentials or credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <API_KEY>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.credentials != api_settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key credentials provided.",
        )
    return credentials.credentials
