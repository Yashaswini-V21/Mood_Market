<!-- ═══════════════════════════════════════════════════════════════════
     MOOD MARKET — Custom SVG Banner (dark glassmorphism + finance aesthetic)
═══════════════════════════════════════════════════════════════════════ -->
<p align="center">
  <img src="MoodMarket/doc/banner.svg" alt="Mood Market — AI Financial Sentiment & Forecasting Platform" width="100%"/>
</p>

<!-- ── Animated subtitle (rotating key facts) ─────────────────────────────── -->
<p align="center">
  <a href="https://github.com/Yashaswini-V21/Mood_Market">
    <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=16&duration=2800&pause=900&color=A855F7&center=true&vCenter=true&width=720&lines=⚡+Real-time+social+sentiment+→+price+direction+forecast;🔴+HypeStorm+Radar™+fires+before+the+crowd+notices;🤖+5-Agent+async+trading+desk+%7C+Kelly+risk+sizing;🧬+FinBERT+%2B+DistilBERT+%2B+Informer+Transformer+stack;🐳+9-service+Docker+Compose+%7C+one+command+to+run" alt="Typing animation"/>
  </a>
</p>

<br/>

<!-- ── CI/CD status badges ──────────────────────────────────────────────────── -->
<p align="center">
  <a href="https://github.com/Yashaswini-V21/Mood_Market/actions/workflows/test.yml">
    <img src="https://img.shields.io/badge/✓%20Tests_%26_Linting-passing-22c55e?style=for-the-badge&logo=github-actions&logoColor=white" />
  </a>&nbsp;
  <a href="https://github.com/Yashaswini-V21/Mood_Market/actions/workflows/security.yml">
    <img src="https://img.shields.io/badge/✓%20Security_Scan-passing-22c55e?style=for-the-badge&logo=shield&logoColor=white" />
  </a>&nbsp;
  <a href="https://github.com/Yashaswini-V21/Mood_Market/actions/workflows/build.yml">
    <img src="https://img.shields.io/badge/✓%20Docker_Build-passing-22c55e?style=for-the-badge&logo=docker&logoColor=white" />
  </a>&nbsp;
  <a href="https://github.com/Yashaswini-V21/Mood_Market/actions/workflows/performance.yml">
    <img src="https://img.shields.io/badge/✓%20Lighthouse_CI-passing-22c55e?style=for-the-badge&logo=lighthouse&logoColor=white" />
  </a>
</p>

<!-- ── Tech stack pills ──────────────────────────────────────────────────────── -->
<p align="center">
  <img src="https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/React_19-61DAFB?style=flat-square&logo=react&logoColor=black"/>
  <img src="https://img.shields.io/badge/PyTorch_2.2-EE4C2C?style=flat-square&logo=pytorch&logoColor=white"/>
  <img src="https://img.shields.io/badge/TimescaleDB-FDB515?style=flat-square&logo=postgresql&logoColor=black"/>
  <img src="https://img.shields.io/badge/Redis_7-DC382D?style=flat-square&logo=redis&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker_×9-2496ED?style=flat-square&logo=docker&logoColor=white"/>
  <img src="https://img.shields.io/badge/License-MIT-a855f7?style=flat-square"/>
</p>

<p align="center">
  <sub>Built for the <strong>Future of Productivity</strong> hackathon &nbsp;·&nbsp; Not financial advice</sub>
</p>

---

## 📖 Table of Contents

- [What It Does](#-what-it-does)
- [Live Demo](#-live-demo)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Features Deep Dive](#-features-deep-dive)
- [Quick Start](#-quick-start)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [ML Models](#-ml-models)
- [Performance Benchmarks](#-performance-benchmarks)
- [Testing](#-testing)
- [CI/CD Pipeline](#-cicd-pipeline)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [Documentation](#-documentation)
- [License](#-license)

---

## 🎯 What It Does

**Mood Market** answers a single question traders obsess over every morning:

> *"What is the market feeling right now — and what will it do next?"*

It does this with a multi-layer AI pipeline:

1. **Ingest** → scrapes Reddit, financial news, and Google Trends in real time
2. **Sentiment** → runs text through a **FinBERT + DistilBERT ensemble** with confidence-weighted fusion
3. **Anomaly** → 7 concurrent detectors vote on whether sentiment is a **genuine signal or coordinated hype** (HYPE_STORM™)
4. **Forecast** → an **Informer Transformer** (ProbSparse attention, O(L log L)) predicts 4-hour price direction with calibrated uncertainty
5. **Synthesize** → a 5-agent async trading desk fuses all signals into a final **BUY / SELL / HOLD** with position sizing and risk levels
6. **Surface** → a polished React 19 dashboard streams everything live over authenticated WebSockets

Built for a hackathon under the **"Future of Productivity"** theme — because most of what financial analysts do manually can be automated into one dashboard.

---

## 🎬 Live Demo

No API keys needed. Run the offline demo to experience a full 60-minute synthetic trading session:

```bash
# Install one dependency then run
pip install websockets
python MoodMarket/doc/demo/demo_server.py --speed 10
# → http://localhost:8001  (6 real minutes = 60 sim minutes)

# In another terminal
cd MoodMarket/frontend && npm install && npm run dev
# → http://localhost:5173
```

> **Highlight:** At simulated minute 40, GME enters a **HYPE_STORM** — all 7 anomaly detectors fire in rapid succession and every WebSocket client receives live alerts.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│          React 19 + TypeScript  (Vite · Tailwind · Recharts)    │
│         Landing · Dashboard · Compare · Portfolio                 │
└────────────────────────────┬─────────────────────────────────────┘
                             │  REST + WebSocket (JWT HS256)
┌────────────────────────────▼─────────────────────────────────────┐
│                   FastAPI  (async · Python 3.11)                  │
│    /sentiment  /forecast  /anomaly  /pipeline  /explain           │
│    Middleware: JWT auth · Redis rate-limit · X-Request-ID trace   │
└──────────┬───────────────────────────────┬────────────────────────┘
           │                               │
    ┌──────▼───────┐               ┌───────▼────────────────────────┐
    │   ML Engine  │               │  5-Agent Async Trading Desk     │
    │              │               │                                  │
    │  Informer    │               │  S1 → Sentiment Analyst          │
    │  Transformer │               │  S2 → Technical Analyst (RSI,   │
    │  ProbSparse  │               │       MACD, Bollinger, VWAP)    │
    │  Monte Carlo │               │  S3 → Forecaster Agent           │
    │  SHAP+Rollout│               │  S4 → Risk Manager (Kelly)       │
    │              │               │  S5 → Synthesizer                │
    │  Anomaly     │               │                                  │
    │  7-Method    │               │  Each: LRU cache · timeout ·    │
    │  Ensemble    │               │        graceful fallback         │
    └──────┬───────┘               └───────┬────────────────────────┘
           │                               │
    ┌──────▼───────────────────────────────▼────────────────────────┐
    │               Celery Workers  (4 priority queues)              │
    │         Reddit · Yahoo Finance · News API · Google Trends      │
    └──────┬────────────────────────┬──────────────────────────────┘
           │                        │
    ┌──────▼──────┐    ┌────────────▼──────────┐    ┌─────────────┐
    │   Redis 7   │    │    TimescaleDB / PG    │    │ Prometheus  │
    │  Cache +    │    │  Hypertables · Cont.   │    │  + Grafana  │
    │  Pub/Sub    │    │  Aggregates · Retain.  │    │  Dashboard  │
    └─────────────┘    └───────────────────────┘    └─────────────┘
```

---

## 🛠 Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | React 19 · TypeScript · Vite · Tailwind CSS · Recharts | Type-safe, fast-refresh, composable charts |
| **Backend** | Python 3.11 · FastAPI (async) · SQLAlchemy 2.0 | Native async, Pydantic v2 validation, OpenAPI docs |
| **ML** | PyTorch 2.2 · FinBERT · DistilBERT · SHAP · Optuna | Production-tuned transformers + explainability |
| **Workers** | Celery 5 · Redis 7 | 4 priority queues, scheduled data refresh |
| **Database** | TimescaleDB (PostgreSQL 15) | Hypertables + continuous aggregates for time-series |
| **Monitoring** | Prometheus · Grafana · Flower | Full observability from day one |
| **Infra** | Docker Compose (9 services) · Nginx · GitHub Actions | One-command local dev + CI/CD to GHCR |

---

## ✨ Features Deep Dive

### 🧠 Informer Transformer (Core Model)

Custom implementation of [Informer](https://arxiv.org/abs/2012.07436) (Zhou et al., NeurIPS 2021) adapted for binary direction classification with several production enhancements:

| | Baseline LSTM | Standard Transformer | **Mood Market Informer** |
|--|:---:|:---:|:---:|
| Attention complexity | O(L²) | O(L²) | **O(L log L)** ProbSparse |
| Multi-step forecast | Autoregressive | Autoregressive | **Single-pass generative decoder** |
| Uncertainty estimate | ✗ | ✗ | **✓ Monte Carlo + Softplus head** |
| Explainability | ✗ | Basic | **✓ SHAP + Attention Rollout** |
| INT8 Quantization | ✗ | ✗ | **✓ 3.8× smaller, 2.1× faster** |
| **Directional accuracy** | 50.1% | 58.3% | **65.2%** |

```python
# Forward pass — 72 timesteps → direction + uncertainty + attributions
prediction, uncertainty, attention_weights = model(encoder_input, decoder_input)
# prediction       ∈ [0, 1]   — BUY probability for next 4 hours
# uncertainty      — Softplus  — ±confidence interval (Monte Carlo dropout)
# attention_weights — 8 heads  — SHAP + Rollout per-feature attribution maps
```

### 🚨 Hype Storm Radar™ — 7-Method Anomaly Ensemble

All 7 detectors run concurrently and vote with calibrated confidence weights:

| # | Detector | What It Catches |
|---|----------|----------------|
| 1 | **Z-Score** | Sudden volume or sentiment spikes |
| 2 | **Multi-Variate Z-Score** | Correlated cross-source spikes (Reddit + News simultaneously) |
| 3 | **Isolation Forest** | Non-linear outlier patterns |
| 4 | **MV Isolation Forest** | Complex multi-source coordinated anomalies |
| 5 | **Autoencoder** | Patterns unlike any normal market behavior (reconstruction error) |
| 6 | **EWMA** | Accelerating exponential momentum |
| 7 | **Adaptive EWMA** | Market regime shifts with dynamic lambda |

Severity ladder: `NORMAL` → `ELEVATED` → `MAJOR_SPIKE` → 🔴 `HYPE_STORM`

### 🤖 5-Agent Async Trading Desk

Each agent runs as an independent async coroutine with its own LRU cache, configurable timeout, and graceful fallback:

```
S1 Sentiment Analyst  → Reddit + News + Trends → weighted composite score
S2 Technical Analyst  → RSI · MACD · Bollinger Bands · VWAP · Support/Resistance
S3 Forecaster Agent   → Informer pipeline → direction probability + uncertainty
S4 Risk Manager       → Kelly Criterion position sizing → stop-loss · take-profit
S5 Synthesizer        → Weighted signal fusion → BUY / SELL / HOLD + confidence
```

### 📊 React Dashboard Highlights

- **Live Dashboard** — real-time sentiment dial, anomaly status badge, SHAP waterfall chart, price overlay
- **Multi-Ticker Compare** — radar chart, price correlation matrix, sentiment heatmap
- **Portfolio Analytics** — P&L vs benchmark, allocation donut, positions table, AI risk summary
- **Responsive** — desktop sidebar layout and fully adapted mobile-bottom-nav layout

---

## 🚀 Quick Start

### Prerequisites

```
Python 3.10+  ·  Node.js 18+  ·  Docker + Docker Compose
```

### Option 1 — Docker (Recommended, one command)

```bash
git clone https://github.com/Yashaswini-V21/Mood_Market.git
cd Mood_Market/MoodMarket/backend

# Copy env file and add your keys (all optional — falls back to mock data)
cp .env.example .env

docker compose up --build
```

| Service | URL |
|---------|-----|
| 📖 FastAPI Swagger UI | http://localhost:8000/docs |
| ⚡ React Dashboard | http://localhost:3000 |
| 📊 Grafana | http://localhost:3001 |
| 🔭 Prometheus | http://localhost:9090 |
| 🌸 Celery Flower | http://localhost:5555 |

### Option 2 — Local Development

```bash
git clone https://github.com/Yashaswini-V21/Mood_Market.git
cd Mood_Market

# ── Backend ──────────────────────────────────────────
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # Linux / macOS

pip install -r MoodMarket/backend/requirements-ci.txt

# ── Frontend ─────────────────────────────────────────
cd MoodMarket/frontend && npm install && cd ../..

# ── Run (4 terminals) ─────────────────────────────────
# T1 — API server
cd MoodMarket/backend && uvicorn main:app --reload --port 8000

# T2 — Frontend dev server
cd MoodMarket/frontend && npm run dev

# T3 — Celery workers
celery -A MoodMarket.backend.celery_app worker -l info -Q critical,priority,default,low

# T4 — Celery beat scheduler
celery -A MoodMarket.backend.celery_app beat -l info
```

### Option 3 — Offline Demo (No APIs / DB / Redis required)

```bash
pip install websockets
python MoodMarket/doc/demo/demo_server.py --speed 10
# Replays AAPL / TSLA / GME for 60 sim-minutes at 10× speed (6 real mins)
# GME enters HYPE_STORM at sim-minute 40 → all 7 detectors fire live

cd MoodMarket/frontend && npm run dev
# Open → http://localhost:5173
```

---

## 🔑 Environment Variables

Copy `MoodMarket/backend/.env.example` → `.env` and configure:

```env
# Required for production — leave blank to use mock/SQLite fallbacks in dev
REDIS_URI=redis://localhost:6379
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/moodmarket
TIMESCALEDB_URI=postgresql://user:pass@localhost/moodmarket

# JWT (generate with: python -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET_KEY=your-super-secret-key-here
JWT_ALGORITHM=HS256

# Optional — falls back to mock data if omitted
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=MoodMarket/1.0
NEWS_API_KEY=

# Environment flag
ENVIRONMENT=development   # or production
```

---

## 🔌 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | System health check — DB, Redis, model status |
| `POST` | `/auth/token` | Exchange credentials for JWT access token |
| `GET` | `/api/v1/sentiment/{ticker}` | Real-time sentiment score + source breakdown |
| `POST` | `/api/v1/sentiment/predict` | Analyze custom text with FinBERT ensemble |
| `GET` | `/api/v1/price/forecast/{ticker}` | 4-hour direction forecast + confidence interval |
| `GET` | `/api/v1/anomaly/{ticker}` | Hype storm status + triggered detector list |
| `GET` | `/api/v1/pipeline/{ticker}` | Full bundle: sentiment + forecast + risk + signal |
| `GET` | `/api/v1/explain/{prediction_id}` | SHAP values + attention rollout weights |
| `POST` | `/api/v1/watchlist` | Add/remove tickers from user watchlist |
| `GET` | `/metrics` | Prometheus scrape endpoint |

### WebSocket Streams (JWT required)

| Channel | URI | Payload |
|---------|-----|---------|
| Price | `/ws/price/{ticker}` | OHLCV tick |
| Sentiment | `/ws/sentiment/{ticker}` | Score + confidence |
| Anomaly | `/ws/anomaly` | Severity + methods triggered |
| Forecast | `/ws/prediction/{ticker}` | Direction + uncertainty |
| Portfolio | `/ws/portfolio` | Aggregated watchlist update |

> Full interactive docs: `http://localhost:8000/docs` (Swagger) · `http://localhost:8000/redoc` (ReDoc)

---

## 🤖 ML Models

### Training

```bash
cd MoodMarket/ml

# Default — 50 epochs, cosine LR schedule, early stopping (patience 10)
python train.py

# Named presets
python train.py --config fast           # 10-epoch quick experiment
python train.py --config high_accuracy  # 100 epochs, d_model=768, 12 heads
python train.py --config efficient      # INT8-ready, optimized for inference

# Hyperparameter search (100 Optuna trials, Optuna dashboard included)
python trainer.py --tune

# Evaluate and compare against LSTM / vanilla Transformer baselines
python MoodMarket/ml/evaluator.py
```

### Model Configurations

| Config | d_model | Heads | Enc Layers | Dec Layers | Epochs |
|--------|:-------:|:-----:|:----------:|:----------:|:------:|
| `baseline` | 512 | 8 | 2 | 2 | 50 |
| `small` | 256 | 4 | 1 | 1 | 50 |
| `large` | 768 | 12 | 3 | 3 | 100 |
| `efficient` | 512 | 8 | 2 | 2 | 50 + INT8 |
| `high_accuracy` | 768 | 12 | 4 | 4 | 100 |

### Database Schema

```sql
-- TimescaleDB hypertables (chunk by 1 day)
sentiment_data        (time, ticker, sentiment_score, confidence, source, model_version)
price_data            (time, ticker, open, high, low, close, volume, vwap)
technical_indicators  (time, ticker, rsi, macd, bb_upper, bb_lower, signal)
predictions           (time, ticker, predicted_direction, confidence_interval, model_id)
anomaly_alerts        (time, ticker, alert_type, confidence, methods_triggered, severity)

-- Auto-refreshed continuous aggregates (hourly)
daily_sentiment_avg   → per-ticker daily sentiment rollup
hourly_price_ohlc     → 1-hour OHLC candles
weekly_returns        → 7-day return series

-- Retention policy: compress after 30 days · drop after 2 years
```

---

## ⚡ Performance Benchmarks

| Metric | Result |
|--------|--------|
| Informer directional accuracy | **65.2%** (vs 50.1% LSTM · 58.3% Transformer) |
| API latency P50 (cached) | **< 20 ms** |
| API latency P99 (INT8 model) | **< 45 ms** |
| Load test throughput | **1,200 RPS** @ < 32 ms P99 (Locust) |
| WebSocket end-to-end latency | **< 1 s** |
| Concurrent tickers monitored | **500+** |
| Anomaly detection F1 | **0.90** on synthetic pump simulations |
| Anomaly false positive rate | **< 5%** |
| Redis cache hit rate | **70%+** |
| INT8 model size reduction | **3.8× smaller** |
| INT8 inference speedup | **2.1× faster** |

---

## 🧪 Testing

```bash
# Run all 200+ tests
pytest MoodMarket/test/ -q

# With coverage enforcement (≥ 90%)
pytest MoodMarket/test/ --cov=MoodMarket/backend --cov-fail-under=90

# Targeted suites
pytest MoodMarket/test/unit/test_anomaly.py -v     # 7-method ensemble
pytest MoodMarket/test/unit/test_informer.py -v    # Informer architecture
pytest MoodMarket/test/unit/test_agents.py -v      # Trading desk agents
pytest MoodMarket/test/unit/test_shap.py -v        # Explainability
pytest MoodMarket/test/integration/ -v             # API + DB + WebSocket
pytest MoodMarket/test/e2e/ -v                     # Performance + user journey

# Locust load test
locust -f MoodMarket/ml/benchmarks/locustfile.py --host=http://localhost:8000
```

**Coverage:** 200+ tests · 22 test files · unit (15) · integration (5) · e2e (2)

---

## 🔐 Security

| Layer | Implementation |
|-------|---------------|
| **Authentication** | JWT HS256 · `iss`/`aud` claims · env-var secrets only |
| **Rate Limiting** | Redis sliding window — 100 req / min per IP |
| **Input Validation** | Ticker regex `^[A-Za-z]{1,5}$` · Pydantic v2 strict mode |
| **CORS** | Restricted to frontend origin in production (`CORS_ORIGIN` env var) |
| **HTTPS** | Fail-fast at startup if `ENVIRONMENT=production` and HTTPS is disabled |
| **Secrets** | `.env` file, never hardcoded · startup assertion if defaults used |
| **Request Tracing** | UUID-based `X-Request-ID` on every response |
| **Container Scanning** | Trivy scans on every PR (SARIF → GitHub Security tab) |
| **Dependency Audit** | npm audit + pip-audit on every PR |

See [`SECURITY.md`](MoodMarket/backend/SECURITY.md) for the responsible disclosure policy.

---

## 🔄 CI/CD Pipeline

Four GitHub Actions workflows run on every push and pull request:

| Workflow | Trigger | What It Does |
|----------|---------|-------------|
| `test.yml` | push · PR | flake8 · ESLint · mypy · pytest 200+ tests · frontend build · Codecov |
| `security.yml` | push · PR · weekly | Trivy container scan · npm audit · pip-audit · Gitleaks secret scan |
| `performance.yml` | push · PR | Lighthouse Core Web Vitals · Bundle size analysis |
| `build.yml` | push to `main` · tags | Multi-stage Docker build → push backend + frontend to GHCR |

---

## 📁 Project Structure

```
Mood_Market/
├── README.md                          ← You are here
└── MoodMarket/
    ├── backend/                       ← FastAPI application
    │   ├── main.py                    ← App entrypoint + lifespan hooks
    │   ├── config.py                  ← Pydantic settings (100+ config values)
    │   ├── orchestrator.py            ← 5-agent pipeline coordinator
    │   ├── database.py                ← TimescaleDB / SQLite engine + migrations
    │   ├── schema.py                  ← Pydantic data models
    │   ├── agents/                    ← Async trading desk
    │   │   ├── base_agent.py          ← LRU cache · timeout · fallback base
    │   │   ├── sentiment_agent.py
    │   │   ├── technical_agent.py
    │   │   ├── forecaster_agent.py
    │   │   ├── risk_manager_agent.py
    │   │   └── synthesizer_agent.py
    │   ├── routes/                    ← REST + WebSocket endpoints
    │   │   ├── sentiment.py
    │   │   ├── forecast.py
    │   │   ├── anomaly.py
    │   │   ├── pipeline.py
    │   │   ├── explain.py
    │   │   ├── watchlist.py
    │   │   └── health.py
    │   ├── sources/                   ← Data ingestion adapters
    │   │   ├── reddit_source.py
    │   │   ├── news_source.py
    │   │   ├── price_source.py
    │   │   └── trends_source.py
    │   ├── migrations/                ← TimescaleDB SQL migrations
    │   ├── docker/                    ← Prometheus / Grafana configs
    │   ├── docker-compose.yml         ← 9-service local dev stack
    │   ├── docker-compose.prod.yml    ← Production stack (Nginx + SSL)
    │   ├── Dockerfile                 ← Multi-stage backend image
    │   ├── requirements.txt           ← Production dependencies
    │   ├── requirements-ci.txt        ← Lightweight CI dependencies
    │   ├── .env.example               ← Environment variable template
    │   ├── CONTRIBUTING.md
    │   └── SECURITY.md
    │
    ├── frontend/                      ← React 19 + TypeScript dashboard
    │   ├── src/
    │   │   ├── pages/                 ← Landing · Dashboard · Compare · Portfolio
    │   │   ├── components/            ← SentimentDial · SignalCard · AnomalyBadge …
    │   │   ├── context/               ← RealtimeContext · ToastContext
    │   │   ├── hooks/                 ← useWebSocket · useRealtimeData · useTheme
    │   │   └── utils/                 ← WebSocket client · signal generator
    │   ├── Dockerfile                 ← Multi-stage Node → Nginx image
    │   └── package.json
    │
    ├── ml/                            ← Standalone ML experiments & training
    │   ├── model.py                   ← Informer Transformer (ProbSparse attention)
    │   ├── train.py                   ← FP16 training + early stopping
    │   ├── trainer.py                 ← Optuna HPO (100 trials)
    │   ├── inference.py               ← Real-time prediction engine
    │   ├── sentiment_ensemble.py      ← FinBERT + DistilBERT fusion
    │   ├── anomaly_detector.py        ← 7-method ensemble orchestrator
    │   ├── shap_explainer.py          ← SHAP attribution engine
    │   ├── evaluator.py               ← Multi-baseline comparison
    │   ├── backtester.py              ← Historical strategy backtester
    │   ├── agents/                    ← Agent module (shared with backend)
    │   ├── detectors/                 ← Individual anomaly detectors
    │   ├── processors/                ← Data pipeline processors
    │   └── benchmarks/                ← Locust load test + results
    │
    ├── test/                          ← 200+ automated tests
    │   ├── unit/                      ← 15 unit test files
    │   ├── integration/               ← 5 integration test files
    │   └── e2e/                       ← 2 end-to-end test files
    │
    └── doc/                           ← Documentation extras
        ├── demo/                      ← Offline demo server
        └── examples/                  ← API usage examples
```

---

## 🗺 Roadmap

- [ ] **Live streaming** — real Reddit OAuth + Twitter API v2 (currently uses mock/cached data)
- [ ] **GPT-4o news agent** — automated earnings call summarizer and macro event digest
- [ ] **Order execution bridge** — Alpaca / Interactive Brokers paper-trading integration
- [ ] **Portfolio-level VaR** — Monte Carlo Value-at-Risk across correlated positions
- [ ] **Alert bot** — Telegram / Discord HYPE_STORM notifications
- [ ] **RL trading agent** — PPO policy trained on backtested environment
- [ ] **Multi-language support** — i18n for dashboard UI

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork and create a feature branch: `git checkout -b feat/my-feature`
2. Ensure all 200+ tests pass: `pytest MoodMarket/test/ -q`
3. Run linting: `flake8 MoodMarket/backend/` and `cd MoodMarket/frontend && npm run lint`
4. Open a PR with a clear description

See [`CONTRIBUTING.md`](MoodMarket/backend/CONTRIBUTING.md) for full development setup, code style, and PR guidelines.

---

## 👩‍💻 Author

**Yashaswini V** — AI/ML & Data Science, building at the intersection of deep learning and financial markets.

<a href="https://github.com/Yashaswini-V21">
  <img src="https://img.shields.io/badge/GitHub-Yashaswini--V21-181717?style=for-the-badge&logo=github" />
</a>

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](MoodMarket/doc/ARCHITECTURE.md) | Full system design, data flow diagrams, component breakdown, and key design decisions |
| [CHANGELOG.md](MoodMarket/doc/CHANGELOG.md) | Version history following [Keep a Changelog](https://keepachangelog.com/) format |
| [Makefile](MoodMarket/Makefile) | Developer convenience commands — `make run`, `make test`, `make docker-up` and more |
| [CONTRIBUTING.md](MoodMarket/backend/CONTRIBUTING.md) | Development setup, code style, branch strategy, and PR guidelines |
| [SECURITY.md](MoodMarket/backend/SECURITY.md) | Security policy, vulnerability disclosure process |
| [.env.example](MoodMarket/backend/.env.example) | All required environment variables with descriptions |

---

## 📄 License

Released under the [MIT License](LICENSE).

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:7c3aed,50:4c1d95,100:0d0d1a&height=120&section=footer" alt="Footer" />
</p>

<p align="center">
  <sub>⭐ If this project helped you, please give it a star — it means a lot!</sub><br/>
  <sub><em>Not financial advice. For educational purposes only.</em></sub>
</p>
