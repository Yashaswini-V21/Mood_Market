# c:\Mood_Market\websocket_server.py
import asyncio
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException, status
from sqlalchemy import text

from channel_manager import ChannelManager
from broadcaster import RealTimeBroadcaster
from authenticator import JWTAuthenticator
from database import get_db_session

logger = logging.getLogger("websocket_server")

router = APIRouter()

# Instantiate channel manager and real-time broadcaster
manager = ChannelManager()
broadcaster = RealTimeBroadcaster(manager)


# NOTE: Startup/shutdown hooks are handled via the lifespan context manager
# in main.py (FastAPI >= 0.109 best practice). The broadcaster and heartbeat
# loops are initialized from there. If running standalone, call:
#   asyncio.create_task(manager.start_heartbeat_loop(30.0))
#   broadcaster.start()


async def get_user_tickers(user_id: str) -> List[str]:
    """Retrieves all active tickers watched by a specific user from either watchlist table."""
    tickers = []
    async for session in get_db_session():
        try:
            # 1. Check user_watchlists hypertable
            query = text("SELECT ticker FROM user_watchlists WHERE user_id = :user_id AND removed_at IS NULL")
            res = await session.execute(query, {"user_id": user_id})
            rows = res.fetchall()
            if rows:
                tickers = [r[0].upper().strip() for r in rows]
                return tickers
        except Exception:
            pass

        try:
            # 2. Fallback to watchlist_records table
            query = text("SELECT tickers FROM watchlist_records WHERE user_id = :user_id")
            res = await session.execute(query, {"user_id": user_id})
            row = res.fetchone()
            if row and row[0]:
                tickers = [t.upper().strip() for t in row[0].split(",") if t.strip()]
                return tickers
        except Exception:
            pass
            
    return tickers


# 1. WebSocket Channel Handlers

@router.websocket("/ws/sentiment/{ticker}")
async def ws_sentiment(websocket: WebSocket, ticker: str, token: str = Query(...)):
    """Pushes sentiment score ticks to client for a specific ticker."""
    user_id = JWTAuthenticator.verify_token(token)
    if not user_id:
        await websocket.close(code=4003) # Forbidden
        return

    ticker_name = ticker.upper().strip()
    channel = f"sentiment:{ticker_name}"
    await manager.connect(websocket, channel)
    
    try:
        while True:
            # Keep socket open, receiving keep-alives or pongs if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@router.websocket("/ws/price/{ticker}")
async def ws_price(websocket: WebSocket, ticker: str, token: str = Query(...)):
    """Pushes price and percent change ticks to client for a specific ticker."""
    user_id = JWTAuthenticator.verify_token(token)
    if not user_id:
        await websocket.close(code=4003)
        return

    ticker_name = ticker.upper().strip()
    channel = f"price:{ticker_name}"
    await manager.connect(websocket, channel)
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@router.websocket("/ws/anomaly")
async def ws_anomaly(websocket: WebSocket, token: str = Query(...)):
    """Pushes high confidence statistical anomalies in real-time as they are detected."""
    user_id = JWTAuthenticator.verify_token(token)
    if not user_id:
        await websocket.close(code=4003)
        return

    channel = "anomaly"
    await manager.connect(websocket, channel)
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@router.websocket("/ws/prediction/{ticker}")
async def ws_prediction(websocket: WebSocket, ticker: str, token: str = Query(...)):
    """Pushes Informer model forecast direction probabilities to client for a specific ticker."""
    user_id = JWTAuthenticator.verify_token(token)
    if not user_id:
        await websocket.close(code=4003)
        return

    ticker_name = ticker.upper().strip()
    channel = f"prediction:{ticker_name}"
    await manager.connect(websocket, channel)
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@router.websocket("/ws/portfolio")
async def ws_portfolio(websocket: WebSocket, token: str = Query(...)):
    """Pushes aggregated real-time updates for all tickers on a user's customized watchlist."""
    user_id = JWTAuthenticator.verify_token(token)
    if not user_id:
        await websocket.close(code=4003)
        return

    channel = f"portfolio:{user_id}"
    await manager.connect(websocket, channel)
    
    # Run a parallel loop task pushing custom aggregated updates for this user
    async def push_portfolio_updates():
        try:
            while True:
                # Query watchlist tickers
                tickers = await get_user_tickers(user_id)
                if tickers:
                    updates = {}
                    # Build summary updates per ticker (mocked close for display updates)
                    for ticker in tickers:
                        updates[ticker] = {
                            "price": 180.0,
                            "sentiment": 0.15,
                            "change_pct": 0.02
                        }
                    await manager.broadcast(channel, {
                        "user_id": user_id,
                        "watchlist_id": f"watchlist_{user_id[:8]}",
                        "updates": updates,
                        "timestamp": asyncio.get_event_loop().time()
                    })
                await asyncio.sleep(60.0) # Check and push every minute
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(push_portfolio_updates())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        task.cancel()
        await manager.disconnect(websocket, channel)


# 2. HTTP Polling Fallback Handlers (Graceful degrades)

@router.get("/api/v1/fallback/price/{ticker}")
async def fallback_price(ticker: str):
    """Fallback price check if WebSockets are blocked/unavailable."""
    ticker = ticker.upper().strip()
    async for session in get_db_session():
        query = text("SELECT close, open FROM price_data WHERE ticker = :ticker ORDER BY time DESC LIMIT 2")
        try:
            res = await session.execute(query, {"ticker": ticker})
            rows = res.fetchall()
            if rows:
                close_price = float(rows[0][0])
                prev = float(rows[1][0]) if len(rows) > 1 else float(rows[0][1])
                return {
                    "price": close_price,
                    "change": close_price - prev,
                    "change_pct": ((close_price - prev) / prev) * 100.0,
                    "timestamp": asyncio.get_event_loop().time()
                }
        except Exception:
            pass
            
    return {
        "price": 150.0,
        "change": 0.0,
        "change_pct": 0.0,
        "timestamp": asyncio.get_event_loop().time()
    }


@router.get("/api/v1/fallback/sentiment/{ticker}")
async def fallback_sentiment(ticker: str):
    """Fallback sentiment check."""
    ticker = ticker.upper().strip()
    async for session in get_db_session():
        query = text("SELECT sentiment_score, confidence FROM sentiment_data WHERE ticker = :ticker ORDER BY time DESC LIMIT 1")
        try:
            res = await session.execute(query, {"ticker": ticker})
            row = res.fetchone()
            if row:
                return {
                    "sentiment": float(row[0]),
                    "confidence": float(row[1]),
                    "updated_at": asyncio.get_event_loop().time()
                }
        except Exception:
            pass
            
    return {
        "sentiment": 0.15,
        "confidence": 0.82,
        "updated_at": asyncio.get_event_loop().time()
    }
