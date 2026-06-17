# MoodMarket — Project Overview

> A summary of what this project does, how it works, and how to run it.
> Built for the **"Future of Productivity"** hackathon track.

---

## What it does

MoodMarket monitors social sentiment across Reddit, Twitter, and news sources for hundreds of stocks simultaneously, runs the signals through an NLP ensemble, and feeds them into a custom Informer Transformer to predict short-term price direction. The platform also detects coordinated hype events ("Hype Storms") using a 7-method anomaly ensemble before the price movement happens.

The goal: replace the hours of manual research a trader does every morning with a single dashboard.

---

## Problem → Solution

| Without MoodMarket | With MoodMarket |
|-------------------|-----------------|
| Manually scan Reddit/Twitter/news every morning | AI ingests and scores 500+ tickers in real-time |
| Calculate RSI, MACD, Bollinger manually | Technical agent computes all signals automatically |
| Guess whether hype is organic or coordinated | 7-method ensemble flags it in <30ms |
| Black-box ML — no idea why it says BUY | SHAP + attention rollout explains every prediction |
| Separate tools for price, sentiment, risk | One dashboard: sentiment + forecast + risk + signal |

---

## Technical summary

**ML / Deep Learning**
- Custom [Informer Transformer](https://arxiv.org/abs/2012.07436) (ProbSparse self-attention, O(L log L) complexity)
- Single-pass generative decoder — no autoregressive error compounding
- Monte Carlo dropout uncertainty quantification + Softplus uncertainty head
- FinBERT + DistilBERT confidence-weighted sentiment fusion
- SHAP deep attribution, attention rollout, ECE calibration
- INT8 dynamic quantization (3.8× size reduction), FP16 training, Optuna hyperparameter search

**Backend**
- Async FastAPI, SQLAlchemy 2.0 async, Redis multi-layer cache
- Celery workers (4 priority queues: critical / priority / default / low)
- TimescaleDB hypertables with continuous aggregates and retention policies
- JWT authentication, Redis rate limiting, Pydantic v2 validation

**Frontend**
- React 19 + TypeScript + Vite + Tailwind CSS
- Real-time WebSocket feeds for price, sentiment, anomaly, forecast
- Recharts-based radar, area, and pie charts
- Animated landing page with particle canvas and glassmorphism

**DevOps**
- Docker Compose (9 services), GitHub Actions CI/CD (3 workflows)
- Prometheus + Grafana monitoring, Trivy/CodeQL security scans
- 200+ automated tests across unit, integration, and e2e layers

---

## Key numbers

| Metric | Value |
|--------|-------|
| Directional accuracy | 65.2% (vs 50.1% LSTM baseline) |
| API P50 latency | <20ms |
| Anomaly false positive rate | <5% |
| Anomaly detection latency | <30ms per stock |
| Load test | 1200 RPS, <32ms P99 |
| Stocks monitored | 500+ concurrent |
| Test coverage | 90%+ |

---

## Running the demo (no setup needed)

```bash
pip install websockets
python MoodMarket/demo/demo_server.py --speed 10
# synthetic 60-minute trading session at 10× speed (6 minutes)
# → http://localhost:8001

cd MoodMarket/frontend && npm install && npm run dev
# → http://localhost:5173
```

The demo simulates AAPL, TSLA, and GME. At the 40-minute mark, GME enters a HYPE_STORM and all 7 anomaly detectors fire in sequence — you can watch the alert severity escalate in real-time.

---

## Full setup

See the [README](README.md) for Docker Compose, local dev, and environment variable setup.

---

## Author

**Yashaswini V** · [GitHub](https://github.com/Yashaswini-V21)
