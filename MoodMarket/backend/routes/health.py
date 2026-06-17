from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from typing import Dict, Any

from models import HealthResponse
from dependencies import get_db, get_redis, get_inference_engine

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    engine = Depends(get_inference_engine)
) -> Dict[str, Any]:
    """
    Checks the connectivity of database pools, cache systems, and local ML models.
    """
    db_connected = False
    try:
        # Check database execution
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False
        
    redis_connected = False
    try:
        # Check redis cache execution
        await redis.ping()
        redis_connected = True
    except Exception:
        redis_connected = False

    models_loaded = False
    try:
        # Verify ML Informer model state loading
        if engine.model is not None:
            models_loaded = True
    except Exception:
        models_loaded = False
        
    status = "healthy" if (db_connected and redis_connected and models_loaded) else "degraded"

    return {
        "status": status,
        "models_loaded": models_loaded,
        "db_connected": db_connected,
        "redis_connected": redis_connected,
    }


@router.get("/auth/token")
async def get_auth_token() -> Dict[str, str]:
    """
    Generates a valid JWT token signed with the secret for WebSocket authentication.
    """
    from authenticator import JWTAuthenticator
    token = JWTAuthenticator.generate_token("dashboard_user", expires_in_minutes=120)
    return {"token": token}
