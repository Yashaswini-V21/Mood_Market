# 🎬 MoodMarket Demo Replay System

> **See the full platform in action without any external APIs, databases, or Redis.**

## Quick Start

```bash
# Install websockets (only dependency)
pip install websockets

# Run at 10x speed (6 minutes for a 60-minute session)
python demo/demo_server.py

# Open in browser
# → http://localhost:8765
```

## What You'll See

The demo replays a synthetic 60-minute trading session for **AAPL, TSLA, and GME**:

1. **Minutes 0–35:** Normal market activity — prices fluctuate, sentiment scores update, predictions cycle between UP/DOWN
2. **Minutes 35–40:** GME sentiment begins spiking on Reddit (hype building)
3. **Minutes 40–60:** 🚨 **HYPE STORM DETECTED** — anomaly detectors fire in sequence:
   - Z-Score catches the volume spike
   - Isolation Forest flags the non-linear pattern
   - EWMA detects accelerating momentum
   - Autoencoder reconstruction error jumps
   - Adaptive EWMA confirms regime shift
   - GME price surges 15%+ with the hype

## Options

```bash
python demo/demo_server.py --speed 1     # Real-time (60 minutes)
python demo/demo_server.py --speed 50    # Ultra-fast (72 seconds)
python demo/demo_server.py --speed 10    # Default (6 minutes)
python demo/demo_server.py --port 9000   # Custom port
python demo/demo_server.py --duration 30 # Shorter session
```

## For Evaluators

This demo showcases:
- ✅ Real-time WebSocket data streaming
- ✅ Multi-ticker parallel monitoring
- ✅ 7-method anomaly ensemble detection
- ✅ Social sentiment tracking (Reddit, Twitter, News)
- ✅ Informer model directional predictions
- ✅ Hype Storm alert system with graduated severity
- ✅ All without requiring any external services
