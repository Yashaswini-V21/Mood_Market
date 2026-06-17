"""
MoodMarket Demo Replay Server

Replays pre-recorded market data at configurable speed through a WebSocket
connection, simulating the full MoodMarket experience without requiring
any external APIs, databases, or Redis.

Usage:
    python demo/demo_server.py                  # 10x speed
    python demo/demo_server.py --speed 1        # Real-time
    python demo/demo_server.py --speed 50       # 50x speed (fast demo)

Open http://localhost:8765 in your browser for the demo dashboard.
"""

import asyncio
import json
import math
import random
import time
import argparse
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

logger = logging.getLogger("demo_server")

# ============================================================================
# SYNTHETIC DATA GENERATORS
# ============================================================================

# Simulates a realistic 1-hour trading session for 3 popular tickers
TICKERS = ["AAPL", "TSLA", "GME"]

TICKER_PROFILES = {
    "AAPL": {"base_price": 192.50, "volatility": 0.003, "base_sentiment": 0.65, "trend": 0.0002},
    "TSLA": {"base_price": 248.30, "volatility": 0.008, "base_sentiment": 0.45, "trend": -0.0001},
    "GME":  {"base_price": 28.40,  "volatility": 0.025, "base_sentiment": 0.30, "trend": 0.0005},
}

# GME will trigger a hype storm at ~40 minutes into the replay
GME_HYPE_START = 40  # minutes into the session


def generate_price_tick(ticker: str, step: int, total_steps: int) -> Dict[str, Any]:
    """Generate a realistic price tick with Brownian motion + trend."""
    profile = TICKER_PROFILES[ticker]
    t = step / total_steps

    # Brownian motion with drift
    drift = profile["trend"] * step
    noise = random.gauss(0, profile["volatility"])

    # GME special: price spike during hype storm
    hype_factor = 0
    if ticker == "GME" and step >= GME_HYPE_START * 4:  # 4 ticks per minute
        elapsed_hype = (step - GME_HYPE_START * 4) / (total_steps - GME_HYPE_START * 4 + 1)
        hype_factor = 0.15 * math.sin(elapsed_hype * math.pi) * random.uniform(0.8, 1.2)

    price = profile["base_price"] * (1 + drift + noise + hype_factor)
    open_price = price * (1 + random.gauss(0, 0.001))
    high_price = max(price, open_price) * (1 + abs(random.gauss(0, 0.002)))
    low_price = min(price, open_price) * (1 - abs(random.gauss(0, 0.002)))

    return {
        "type": "price",
        "ticker": ticker,
        "data": {
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(price, 2),
            "volume": int(random.gauss(50000, 15000) * (1 + hype_factor * 10)),
            "change_pct": round((price / profile["base_price"] - 1) * 100, 3),
        },
    }


def generate_sentiment_tick(ticker: str, step: int, total_steps: int) -> Dict[str, Any]:
    """Generate sentiment score with gradual drift and event-based jumps."""
    profile = TICKER_PROFILES[ticker]
    base = profile["base_sentiment"]

    noise = random.gauss(0, 0.05)
    drift = 0.1 * math.sin(2 * math.pi * step / total_steps)

    # GME hype: sentiment spikes ahead of price
    hype_boost = 0
    if ticker == "GME" and step >= (GME_HYPE_START - 5) * 4:
        elapsed = (step - (GME_HYPE_START - 5) * 4) / 20
        hype_boost = min(0.4, 0.4 * elapsed)

    score = max(-1.0, min(1.0, base + noise + drift + hype_boost))
    confidence = max(0.5, min(0.99, 0.75 + random.gauss(0, 0.08)))

    sources = {
        "reddit": round(score + random.gauss(0, 0.1), 3),
        "twitter": round(score + random.gauss(0, 0.08), 3),
        "news": round(score + random.gauss(0, 0.05), 3),
    }

    return {
        "type": "sentiment",
        "ticker": ticker,
        "data": {
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "label": "bullish" if score > 0.2 else ("bearish" if score < -0.2 else "neutral"),
            "sources": sources,
            "reddit_mentions": int(random.gauss(120, 40) * (1 + hype_boost * 5)),
            "twitter_mentions": int(random.gauss(250, 80) * (1 + hype_boost * 3)),
        },
    }


def generate_anomaly_tick(ticker: str, step: int, total_steps: int) -> Dict[str, Any]:
    """Generate anomaly detection status — GME triggers HYPE_STORM."""
    is_gme_hype = ticker == "GME" and step >= GME_HYPE_START * 4

    if is_gme_hype:
        elapsed = (step - GME_HYPE_START * 4) / 20
        confidence = min(0.97, 0.6 + 0.37 * elapsed)
        methods = ["zscore", "isolation_forest", "ewma", "autoencoder"]
        if elapsed > 0.5:
            methods.append("adaptive_ewma")
            methods.append("multivariate_zscore")
        alert = "HYPE_STORM" if elapsed > 0.3 else "ELEVATED"
    else:
        confidence = round(random.uniform(0.1, 0.35), 3)
        methods = []
        alert = "NORMAL"

    return {
        "type": "anomaly",
        "ticker": ticker,
        "data": {
            "anomaly_detected": is_gme_hype,
            "confidence": round(confidence, 3),
            "alert_level": alert,
            "methods_triggered": methods,
            "ensemble_score": round(confidence * len(methods) / 7, 3),
        },
    }


def generate_prediction_tick(ticker: str, step: int, total_steps: int) -> Dict[str, Any]:
    """Generate Informer model prediction."""
    profile = TICKER_PROFILES[ticker]
    trend_signal = profile["trend"] * 1000  # amplify for probability

    # GME during hype: strong UP signal
    hype_signal = 0
    if ticker == "GME" and step >= GME_HYPE_START * 4:
        hype_signal = 0.3

    raw_prob = 0.5 + trend_signal + random.gauss(0, 0.08) + hype_signal
    prob = max(0.05, min(0.95, raw_prob))
    direction = "UP" if prob > 0.5 else "DOWN"

    return {
        "type": "prediction",
        "ticker": ticker,
        "data": {
            "direction": direction,
            "probability": round(prob, 3),
            "confidence_interval": [round(prob - 0.12, 3), round(prob + 0.12, 3)],
            "model": "informer_v1",
            "horizon_hours": 4,
            "uncertainty": round(abs(random.gauss(0.08, 0.03)), 4),
        },
    }


def generate_full_timeline(duration_minutes: int = 60, ticks_per_minute: int = 4) -> List[Dict[str, Any]]:
    """Generate the full replay timeline with all event types."""
    total_steps = duration_minutes * ticks_per_minute
    timeline = []

    for step in range(total_steps):
        timestamp = datetime.now(timezone.utc) + timedelta(seconds=step * (60 / ticks_per_minute))

        for ticker in TICKERS:
            # Price tick every step
            tick = generate_price_tick(ticker, step, total_steps)
            tick["timestamp"] = timestamp.isoformat()
            tick["step"] = step
            timeline.append(tick)

            # Sentiment every 2 steps
            if step % 2 == 0:
                tick = generate_sentiment_tick(ticker, step, total_steps)
                tick["timestamp"] = timestamp.isoformat()
                tick["step"] = step
                timeline.append(tick)

            # Anomaly every 4 steps
            if step % 4 == 0:
                tick = generate_anomaly_tick(ticker, step, total_steps)
                tick["timestamp"] = timestamp.isoformat()
                tick["step"] = step
                timeline.append(tick)

            # Prediction every 8 steps
            if step % 8 == 0:
                tick = generate_prediction_tick(ticker, step, total_steps)
                tick["timestamp"] = timestamp.isoformat()
                tick["step"] = step
                timeline.append(tick)

    return timeline


# ============================================================================
# WEBSOCKET SERVER
# ============================================================================

async def replay_handler(writer, speed: float, timeline: List[Dict[str, Any]]):
    """Send timeline events to a connected WebSocket client."""
    import websockets
    try:
        logger.info(f"Client connected. Replaying {len(timeline)} events at {speed}x speed...")

        # Group events by step
        from itertools import groupby
        events_by_step = []
        for step, group in groupby(timeline, key=lambda x: x["step"]):
            events_by_step.append(list(group))

        interval = (60 / 4) / speed  # seconds between steps at given speed

        for step_events in events_by_step:
            for event in step_events:
                try:
                    await writer.send(json.dumps(event))
                except Exception:
                    return

            await asyncio.sleep(interval)

        # Send completion signal
        await writer.send(json.dumps({"type": "demo_complete", "message": "Replay finished!"}))
        logger.info("Demo replay completed successfully.")

    except Exception as e:
        logger.info(f"Client disconnected: {e}")


# ============================================================================
# DEMO DASHBOARD HTML
# ============================================================================

DEMO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MoodMarket — Live Demo</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #0a0a0f;
            color: #e2e8f0;
            min-height: 100vh;
            overflow-x: hidden;
        }
        .header {
            background: linear-gradient(135deg, #1a0a2e 0%, #2d1b69 50%, #6366f1 100%);
            padding: 24px 32px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .header::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: radial-gradient(circle at 30% 50%, rgba(99, 102, 241, 0.3), transparent 60%);
        }
        .header h1 {
            font-size: 28px;
            font-weight: 800;
            color: white;
            position: relative;
            z-index: 1;
        }
        .header p {
            font-size: 13px;
            color: rgba(255,255,255,0.7);
            margin-top: 4px;
            position: relative;
            z-index: 1;
        }
        .live-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(34, 197, 94, 0.2);
            border: 1px solid rgba(34, 197, 94, 0.4);
            color: #22c55e;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            margin-top: 8px;
            position: relative;
            z-index: 1;
        }
        .live-dot {
            width: 6px; height: 6px;
            background: #22c55e;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.3); }
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            padding: 20px 24px;
            max-width: 1200px;
            margin: 0 auto;
        }
        .card {
            background: rgba(30, 30, 45, 0.8);
            border: 1px solid rgba(99, 102, 241, 0.15);
            border-radius: 12px;
            padding: 16px;
            backdrop-filter: blur(10px);
            transition: border-color 0.3s, transform 0.2s;
        }
        .card:hover {
            border-color: rgba(99, 102, 241, 0.4);
            transform: translateY(-2px);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .ticker-name {
            font-size: 18px;
            font-weight: 700;
            color: white;
        }
        .price {
            font-family: 'JetBrains Mono', monospace;
            font-size: 24px;
            font-weight: 700;
            color: white;
        }
        .change {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            font-weight: 600;
        }
        .up { color: #22c55e; }
        .down { color: #ef4444; }
        .neutral { color: #94a3b8; }
        .metric-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-top: 1px solid rgba(255,255,255,0.05);
        }
        .metric-label {
            font-size: 11px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            font-weight: 600;
        }
        .alert-banner {
            background: linear-gradient(90deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05));
            border: 1px solid rgba(239, 68, 68, 0.4);
            border-radius: 8px;
            padding: 12px 16px;
            margin: 0 24px 16px;
            max-width: 1152px;
            margin-left: auto;
            margin-right: auto;
            display: none;
            animation: slideIn 0.5s ease-out;
        }
        @keyframes slideIn {
            from { transform: translateY(-20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .alert-banner.active { display: flex; align-items: center; gap: 12px; }
        .alert-icon { font-size: 20px; }
        .alert-text { font-size: 13px; font-weight: 600; color: #fca5a5; }
        .alert-detail { font-size: 11px; color: #94a3b8; margin-top: 2px; }
        .event-log {
            max-width: 1152px;
            margin: 0 auto;
            padding: 0 24px 24px;
        }
        .event-log h3 {
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 8px;
        }
        .log-container {
            background: rgba(15, 15, 25, 0.9);
            border: 1px solid rgba(99, 102, 241, 0.1);
            border-radius: 8px;
            padding: 12px;
            max-height: 200px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            line-height: 1.6;
        }
        .log-entry { color: #64748b; }
        .log-entry.anomaly { color: #f97316; }
        .log-entry.hype { color: #ef4444; font-weight: 600; }
        .log-entry.prediction { color: #8b5cf6; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📈 MoodMarket — Live Demo</h1>
        <p>AI-Powered Financial Sentiment & Forecasting Platform</p>
        <div class="live-badge"><div class="live-dot"></div>REPLAYING MARKET SESSION</div>
    </div>

    <div id="alert-banner" class="alert-banner">
        <div class="alert-icon">🚨</div>
        <div>
            <div class="alert-text" id="alert-text">HYPE STORM DETECTED</div>
            <div class="alert-detail" id="alert-detail"></div>
        </div>
    </div>

    <div class="grid" id="ticker-grid"></div>

    <div class="event-log">
        <h3>📡 Event Stream</h3>
        <div class="log-container" id="log"></div>
    </div>

    <script>
        const tickers = {};
        const ws = new WebSocket('ws://localhost:' + (window.location.port ? parseInt(window.location.port) + 1 : 8766) + '/ws');

        function createCard(ticker) {
            const card = document.createElement('div');
            card.className = 'card';
            card.id = `card-${ticker}`;
            card.innerHTML = `
                <div class="card-header">
                    <span class="ticker-name">${ticker}</span>
                    <span class="price" id="price-${ticker}">—</span>
                </div>
                <div class="change" id="change-${ticker}">—</div>
                <div class="metric-row"><span class="metric-label">Sentiment</span><span class="metric-value" id="sent-${ticker}">—</span></div>
                <div class="metric-row"><span class="metric-label">Confidence</span><span class="metric-value" id="conf-${ticker}">—</span></div>
                <div class="metric-row"><span class="metric-label">Reddit Mentions</span><span class="metric-value" id="reddit-${ticker}">—</span></div>
                <div class="metric-row"><span class="metric-label">Forecast</span><span class="metric-value" id="forecast-${ticker}">—</span></div>
                <div class="metric-row"><span class="metric-label">Anomaly</span><span class="metric-value" id="anomaly-${ticker}">—</span></div>
            `;
            document.getElementById('ticker-grid').appendChild(card);
        }

        ['AAPL', 'TSLA', 'GME'].forEach(createCard);

        function addLog(msg, cls = '') {
            const el = document.getElementById('log');
            const ts = new Date().toLocaleTimeString();
            el.innerHTML = `<div class="log-entry ${cls}">[${ts}] ${msg}</div>` + el.innerHTML;
            if (el.children.length > 100) el.removeChild(el.lastChild);
        }

        ws.onmessage = function(evt) {
            const d = JSON.parse(evt.data);
            if (d.type === 'demo_complete') {
                addLog('✅ Demo replay completed!', 'prediction');
                return;
            }
            const t = d.ticker;

            if (d.type === 'price') {
                document.getElementById(`price-${t}`).textContent = `$${d.data.close.toFixed(2)}`;
                const chEl = document.getElementById(`change-${t}`);
                const pct = d.data.change_pct;
                chEl.textContent = `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
                chEl.className = `change ${pct >= 0 ? 'up' : 'down'}`;
            }

            if (d.type === 'sentiment') {
                const sentEl = document.getElementById(`sent-${t}`);
                sentEl.textContent = `${d.data.score > 0 ? '+' : ''}${d.data.score.toFixed(2)} (${d.data.label})`;
                sentEl.className = `metric-value ${d.data.score > 0.2 ? 'up' : d.data.score < -0.2 ? 'down' : 'neutral'}`;
                document.getElementById(`conf-${t}`).textContent = `${(d.data.confidence * 100).toFixed(0)}%`;
                document.getElementById(`reddit-${t}`).textContent = d.data.reddit_mentions;
            }

            if (d.type === 'anomaly') {
                const aEl = document.getElementById(`anomaly-${t}`);
                aEl.textContent = d.data.alert_level;
                aEl.className = `metric-value ${d.data.alert_level === 'HYPE_STORM' ? 'down' : d.data.alert_level === 'ELEVATED' ? 'neutral' : 'up'}`;
                if (d.data.alert_level === 'HYPE_STORM') {
                    const banner = document.getElementById('alert-banner');
                    banner.className = 'alert-banner active';
                    document.getElementById('alert-text').textContent = `🚨 HYPE STORM — ${t}`;
                    document.getElementById('alert-detail').textContent = `Confidence: ${(d.data.confidence * 100).toFixed(0)}% | Methods: ${d.data.methods_triggered.join(', ')}`;
                    addLog(`HYPE STORM on ${t}! Confidence: ${(d.data.confidence*100).toFixed(0)}% — ${d.data.methods_triggered.length} detectors triggered`, 'hype');
                } else if (d.data.alert_level === 'ELEVATED') {
                    addLog(`⚠️ ELEVATED anomaly on ${t} — ${d.data.methods_triggered.join(', ')}`, 'anomaly');
                }
            }

            if (d.type === 'prediction') {
                const fEl = document.getElementById(`forecast-${t}`);
                fEl.textContent = `${d.data.direction} ${d.data.direction === 'UP' ? '↑' : '↓'} ${(d.data.probability * 100).toFixed(0)}%`;
                fEl.className = `metric-value ${d.data.direction === 'UP' ? 'up' : 'down'}`;
                addLog(`🔮 ${t} prediction: ${d.data.direction} ${(d.data.probability*100).toFixed(0)}% (±${(d.data.uncertainty*100).toFixed(1)}%)`, 'prediction');
            }
        };

        ws.onopen = () => addLog('Connected to MoodMarket demo server');
        ws.onclose = () => addLog('Disconnected from demo server');
    </script>
</body>
</html>"""


# ============================================================================
# MAIN
# ============================================================================

import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

class DemoHTTPHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logging HTTP requests to keep terminal clean
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(DEMO_HTML.encode())
        else:
            self.send_error(404, "File not found")

def start_http_server(port):
    server = HTTPServer(("localhost", port), DemoHTTPHandler)
    server.serve_forever()


async def main():
    parser = argparse.ArgumentParser(description="MoodMarket Demo Replay Server")
    parser.add_argument("--speed", type=float, default=10.0, help="Replay speed multiplier (default: 10x)")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port (default: 8765)")
    parser.add_argument("--duration", type=int, default=60, help="Session duration in minutes (default: 60)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    # Pre-generate timeline
    logger.info(f"Generating {args.duration}-minute market session timeline...")
    timeline = generate_full_timeline(duration_minutes=args.duration)
    logger.info(f"Generated {len(timeline)} events across {len(TICKERS)} tickers.")

    # Start HTTP server on args.port in a background daemon thread
    logger.info(f"Starting HTTP server on http://localhost:{args.port} ...")
    http_thread = threading.Thread(target=start_http_server, args=(args.port,), daemon=True)
    http_thread.start()

    try:
        import websockets
        from websockets.asyncio.server import serve as ws_serve
    except ImportError:
        # Fallback for older websockets versions
        import websockets

    async def handler(websocket):
        await replay_handler(websocket, args.speed, timeline)

    # Start WebSocket server on args.port + 1
    ws_port = args.port + 1
    logger.info(f"Starting WebSocket server on ws://localhost:{ws_port}/ws ...")
    try:
        server = await ws_serve(handler, "localhost", ws_port)
    except Exception:
        # Fallback for different websockets API versions
        server = await websockets.serve(handler, "localhost", ws_port)

    logger.info(f"")
    logger.info(f"  ╔══════════════════════════════════════════════╗")
    logger.info(f"  ║   🚀 MoodMarket Demo Server                 ║")
    logger.info(f"  ║   Dashboard:  http://localhost:{args.port}         ║")
    logger.info(f"  ║   WebSocket:  ws://localhost:{ws_port}/ws        ║")
    logger.info(f"  ║   Speed:      {args.speed}x                          ║")
    logger.info(f"  ║   Duration:   {args.duration} minutes ({len(timeline)} events)    ║")
    logger.info(f"  ╚══════════════════════════════════════════════╝")
    logger.info(f"")
    logger.info(f"  Open http://localhost:{args.port} in your browser!")
    logger.info(f"  Press Ctrl+C to stop.\n")

    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())

# clean architecture alignment
