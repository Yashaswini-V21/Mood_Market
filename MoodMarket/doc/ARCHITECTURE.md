# Architecture Guide — Mood Market

> **"Where sentiment meets alpha — before the market moves."**

This document describes the technical architecture of the Mood Market platform: how data flows through the system, how each component is designed, and why key decisions were made.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Repository Layout](#repository-layout)
3. [Data Flow](#data-flow)
4. [Multi-Agent Pipeline (S1–S5)](#multi-agent-pipeline)
5. [ML Stack](#ml-stack)
6. [Backend API](#backend-api)
7. [Real-Time Subsystem](#real-time-subsystem)
8. [Persistence Layer](#persistence-layer)
9. [Caching Strategy](#caching-strategy)
10. [Security Model](#security-model)
11. [Observability](#observability)
12. [Infrastructure](#infrastructure)
13. [Key Design Decisions](#key-design-decisions)

---

## System Overview

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                         External World                               │
 │   Reddit API   │   News API   │   Yahoo Finance   │   Google Trends  │
 └───────┬────────┴──────┬───────┴────────┬──────────┴────────┬─────────┘
         │               │                │                   │
         └───────────────▼────────────────▼───────────────────┘
                   ┌─────────────────────┐
                   │   Celery Workers    │  Background ingestion tasks
                   │  (4 worker threads) │  (beat scheduler, queues)
                   └──────────┬──────────┘
                              │ writes
                   ┌──────────▼──────────┐
                   │   TimescaleDB       │  Time-series primary store
                   │ (PostgreSQL + ext)  │◄─────────────────────────┐
                   └──────────┬──────────┘                          │
                              │ reads                               │
         ┌────────────────────▼────────────────────────┐            │
         │              FastAPI Backend                │            │
         │  ┌──────────────────────────────────────┐  │            │
         │  │  5-Agent Orchestrator (async queue)  │  │  writes    │
         │  │  S1 Sentiment → S2 Technical         │  │────────────┘
         │  │  S3 Forecaster → S4 Risk             │  │
         │  │  S5 Synthesizer                      │  │
         │  └──────────────────────────────────────┘  │
         │                                             │
         │  Redis Cache ◄── Cache Warmer (startup)     │
         │  Prometheus /metrics                        │
         │  JWT WebSocket streams                      │
         └──────────────────────┬──────────────────────┘
                                │ HTTP / WS
                   ┌────────────▼────────────┐
                   │   React + Vite Frontend  │
                   │   TypeScript + Tailwind  │
                   └──────────────────────────┘
```

---

## Repository Layout

```
Mood_Market/
├── README.md                   # Project overview
├── LICENSE                     # License file
├── .gitignore                  # Git exclude patterns
├── .github/
│   └── workflows/
│       ├── test.yml            # Tests + lint + type-check
│       ├── security.yml        # Bandit + Safety + Trivy
│       ├── build.yml           # Docker build + push
│       └── performance.yml     # Locust load test
└── MoodMarket/
    ├── Makefile                # Developer convenience commands
    ├── backend/                # FastAPI application
    │   ├── main.py             # App factory + lifespan
    │   ├── config.py           # Pydantic settings + experiment config
    │   ├── dependencies.py     # DB / Redis / Model DI providers
    │   ├── orchestrator.py     # Multi-agent pipeline coordinator
    │   ├── routes/             # API route handlers
    │   ├── agents/             # (symlinked from ml/agents)
    │   ├── middleware.py       # Logging + rate-limiting middleware
    │   ├── exceptions.py       # Custom exception hierarchy
    │   ├── authenticator.py    # JWT generation + verification
    │   ├── broadcaster.py      # WebSocket broadcast hub
    │   ├── cache.py            # CacheManager (Redis async wrapper)
    │   ├── monitoring.py       # Prometheus custom metrics
    │   ├── migrations/         # SQL migration files
    │   ├── docker-compose.yml  # Local dev stack
    │   └── Dockerfile          # Production container
    ├── ml/                     # Machine learning modules
    │   ├── model.py            # Informer Transformer implementation
    │   ├── inference.py        # InferenceEngine (batch + single)
    │   ├── sentiment_ensemble.py  # FinBERT + DistilBERT ensemble
    │   ├── anomaly_detector.py    # HypeStorm Radar™ 7-method stack
    │   ├── shap_explainer.py      # SHAP feature attribution
    │   ├── train.py / trainer.py  # Training pipeline
    │   ├── agents/             # 5 trading desk agents
    │   │   ├── base_agent.py
    │   │   ├── sentiment_agent.py
    │   │   ├── technical_agent.py
    │   │   ├── forecaster_agent.py
    │   │   ├── risk_manager_agent.py
    │   │   └── synthesizer_agent.py
    │   └── detectors/          # Individual anomaly detectors
    ├── frontend/               # React + Vite SPA
    │   ├── src/
    │   ├── tailwind.config.js
    │   └── Dockerfile
    ├── test/                   # Test suite
    │   ├── conftest.py         # Fixtures, DB/Redis mocks
    │   ├── unit/               # 15 unit test modules
    │   ├── integration/        # 5 integration test modules
    │   └── e2e/                # Cypress + Locust E2E tests
    └── doc/                    # Documentation and assets
        ├── ARCHITECTURE.md     # This file
        ├── CHANGELOG.md        # Version history
        ├── PITCH.md            # Elevator pitch / investor one-pager
        ├── banner.svg          # Repository banner
        ├── demo/
        ├── examples/
        └── notebooks/
```

---

## Data Flow

### Ingestion Path (background)

```
Reddit/News/Price APIs
        │
        ▼  (Celery beat trigger every N minutes)
  Celery Tasks (celery/*)
        │
        ├── raw data validation (processors/data_validator.py)
        ├── deduplication      (processors/deduplicator.py)
        └── enrichment         (processors/enricher.py)
                │
                ▼
         TimescaleDB tables:
           sentiment_records
           price_records
           forecast_records
           anomaly_records
```

### Inference Path (request-time)

```
HTTP GET /api/v1/pipeline/{ticker}
        │
        ▼
  Redis cache check (TTL=300s)
        │ (cache miss)
        ▼
  AgentOrchestrator.execute_pipeline()
        │
        ├─ [S1] SentimentAgent
        │         └─ queries sentiment_records + FinBERT ensemble
        ├─ [S2] TechnicalAgent
        │         └─ RSI / MACD / Bollinger Band calculation
        ├─ [S3] ForecasterAgent
        │         └─ InferenceEngine → Informer Transformer → P(UP)
        ├─ [S4] RiskManagerAgent
        │         └─ Kelly criterion position sizing
        └─ [S5] SynthesizerAgent
                  └─ fuses all signals → final trade recommendation
        │
        ▼
  JSON response + Redis write (TTL=300s)
```

---

## Multi-Agent Pipeline

Each agent inherits from `BaseAgent` (in `ml/agents/base_agent.py`) and communicates via **asyncio queues**:

| Stage | Agent | Key Output |
|-------|-------|-----------|
| S1 | `SentimentAgent` | `sentiment_score`, `confidence`, `source_breakdown` |
| S2 | `TechnicalAgent` | `rsi`, `macd`, `bb_signal`, `trend_strength` |
| S3 | `ForecasterAgent` | `P(UP)`, `confidence_interval`, `timeframe` |
| S4 | `RiskManagerAgent` | `position_size`, `stop_loss`, `take_profit`, `max_loss` |
| S5 | `SynthesizerAgent` | `action`, `conviction`, `rationale`, `composite_score` |

**Timeout handling**: Each agent has a configurable timeout (default 30 s). On timeout, the orchestrator calls `agent.get_fallback_output()` and continues the pipeline — no single agent failure blocks the response.

---

## ML Stack

### Informer Transformer

- **Architecture**: Encoder-Decoder with ProbSparse Self-Attention  
- **Complexity**: O(L log L) vs O(L²) for vanilla attention — scales to long sequences  
- **Input**: 72 timesteps × 8 features (sentiment, price, volume, RSI, MACD, Bollinger Band, Google Trends, Reddit hype)  
- **Output**: P(UP) ∈ [0, 1] + aleatoric uncertainty (softplus)  
- **Loss**: BCE + Huber hybrid with uncertainty regularisation weight  
- **Training**: AdamW, cosine LR schedule, early stopping (patience=15)

### Sentiment Ensemble

```
Input text
    │
    ├─ FinBERT (ProsusAI/finbert)     → financial domain sentiment
    ├─ DistilBERT (distilbert-base)   → general sentiment
    └─ Lexicon fallback               → offline rule-based
            │
            ▼ weighted ensemble average
    sentiment_score ∈ [-1.0, 1.0]
    confidence      ∈ [0.0, 1.0]
```

### HypeStorm Radar™

Seven independent detectors vote; majority + confidence weighting determines `alert_level`:

| # | Detector | Signal |
|---|---------|--------|
| 1 | Z-score | Statistical outlier in sentiment velocity |
| 2 | EWMA | Exponential MA deviation |
| 3 | Isolation Forest | Unsupervised anomaly in feature space |
| 4 | Autoencoder | Reconstruction error spike |
| 5 | Volume Spike | Trading volume > 3σ above rolling mean |
| 6 | Cross-asset Correlation | Unusual correlation breakdown |
| 7 | Social Velocity | Reddit/News post rate acceleration |

---

## Backend API

### Endpoint Map

| Method | Path | Auth | Cache TTL | Description |
|--------|------|------|-----------|-------------|
| GET | `/api/v1/health` | None | — | Service health + component status |
| GET | `/api/v1/sentiment/{ticker}` | Bearer | 300 s | FinBERT+DistilBERT ensemble score |
| POST | `/api/v1/sentiment/predict` | Bearer | — | Analyse custom text |
| GET | `/api/v1/price/forecast/{ticker}` | Bearer | 300 s | Informer 4-hour direction |
| GET | `/api/v1/anomaly/{ticker}` | Bearer | 60 s | HypeStorm Radar™ result |
| GET | `/api/v1/pipeline/{ticker}` | Bearer | 300 s | Full 5-agent bundle |
| GET | `/api/v1/explain/{id}` | Bearer | — | SHAP + Attention Rollout |
| GET/POST | `/api/v1/watchlist` | Bearer | — | Ticker watchlist CRUD |
| GET | `/auth/token` | None | — | Issue demo JWT |
| WS | `/ws/sentiment/{ticker}` | JWT param | — | Live sentiment stream |
| WS | `/ws/price/{ticker}` | JWT param | — | Live price stream |
| WS | `/ws/anomaly/{ticker}` | JWT param | — | Live anomaly alerts |
| GET | `/metrics` | None | — | Prometheus metrics |
| GET | `/docs` | None | — | Swagger UI |
| GET | `/redoc` | None | — | ReDoc UI |

### Middleware Stack (applied in order)

```
Request
  │
  ▼ CORSMiddleware           — origin allowlist
  ▼ RedisRateLimiterMiddleware — 100 req/min per IP/token
  ▼ RequestLoggerMiddleware   — trace ID, latency, structured JSON log
  ▼ Route Handler
  ▼ MoodMarketException Handler
  ▼ Global Exception Handler
Response
```

---

## Real-Time Subsystem

WebSocket connections are managed by `broadcaster.py` and `channel_manager.py`:

- Each ticker gets a **named channel** (e.g. `sentiment:AAPL`)
- On connect, client authenticates via JWT query param
- Backend publishes updates to all subscribers every configurable interval
- Channels are backed by Redis pub/sub for multi-process scaling

---

## Persistence Layer

| Table | Engine | Purpose |
|-------|--------|---------|
| `sentiment_records` | TimescaleDB hypertable | Append-only time-series of sentiment scores |
| `price_records` | TimescaleDB hypertable | OHLCV + technical indicators |
| `forecast_records` | TimescaleDB hypertable | Informer predictions with confidence |
| `anomaly_records` | TimescaleDB hypertable | HypeStorm Radar™ alerts |
| `watchlist_records` | Standard PG table | User ticker watchlists |

**SQLite fallback**: If TimescaleDB is not reachable (dev/CI), `database.py` automatically falls back to `sqlite+aiosqlite:///moodmarket.db` with a SQL translation layer that converts TimescaleDB-specific syntax (hypertables, `time_bucket`, `FIRST`/`LAST`) to SQLite equivalents.

---

## Caching Strategy

```
Request → Redis GET (cache_key)
               │
        ┌──────┴──────┐
      HIT              MISS
        │                │
     Return           Query DB
     cached           or run inference
     JSON                │
                    Redis SET (TTL)
                         │
                      Return JSON
```

- **Cache keys**: `sentiment:{ticker}:{hours}`, `forecast:{ticker}:{cl}`, `anomaly:{ticker}`
- **TTL**: 300 s for sentiment/forecast; 60 s for anomaly alerts
- **Cache warmer**: On startup, `cache_warmer.py` pre-populates the top-50 tickers to eliminate cold-start latency spikes

---

## Security Model

| Layer | Control |
|-------|---------|
| Transport | HTTPS enforced in production (`ENFORCE_HTTPS=true`) |
| Authentication | Bearer JWT (HMAC-SHA256, 2-hour expiry) |
| API key | `API_KEY` env var validated on all data endpoints |
| Rate limiting | 100 req/min per client via Redis sliding window |
| CORS | Wildcard `*` blocked in production; explicit origin list required |
| Secrets | Never committed; `.env.example` documents all required vars |
| Dependency scan | `safety check` + `bandit` run in `security.yml` workflow |
| Container scan | Trivy scans final Docker image on every push |

---

## Observability

| Signal | Tool | Endpoint |
|--------|------|----------|
| Metrics | Prometheus + FastAPI Instrumentator | `/metrics` |
| Dashboards | Grafana | `:3001` |
| Structured logs | Python logging (JSON formatter) | stdout |
| Request tracing | `X-Request-ID` header propagated end-to-end | — |
| Cache hit rate | `cache_stats.py` exposes Redis stats | `/api/v1/health` |
| Task monitoring | Flower (Celery) | `:5555` |
| Load testing | Locust (`ml/benchmarks/locustfile.py`) | — |

---

## Infrastructure

### Docker Compose Services (9 total)

| Service | Image | Port |
|---------|-------|------|
| `postgres` | timescale/timescaledb:latest-pg15 | 5432 |
| `redis` | redis:7-alpine | 6379 |
| `backend` | custom Python 3.11-slim | 8000 |
| `celery_worker` | same as backend | — |
| `celery_beat` | same as backend | — |
| `flower` | same as backend | 5555 |
| `frontend` | Node 20 + Vite | 3000 |
| `kafka` | confluentinc/cp-kafka:7.4.0 | 9092 |
| `prometheus` | prom/prometheus:latest | 9090 |
| `grafana` | grafana/grafana:latest | 3001 |

### One-command startup

```bash
cd MoodMarket && make docker-up
# or
cd MoodMarket/backend && docker compose up --build
```

---

## Key Design Decisions

### Why Informer instead of vanilla Transformer?
Standard self-attention is O(L²) — prohibitively slow for 72-step financial sequences at high-frequency inference. ProbSparse attention reduces this to O(L log L) with <1% accuracy degradation on our benchmark.

### Why TimescaleDB instead of InfluxDB?
TimescaleDB is a PostgreSQL extension — meaning we get full SQL, ACID transactions, and all the ecosystem tooling (asyncpg, SQLAlchemy) without learning a new query language. Hypertables give us automatic time-series partitioning and continuous aggregates.

### Why Redis for caching instead of in-process LRU?
API runs as multiple Uvicorn workers (`--workers 2`). An in-process cache is not shared across workers. Redis provides a single, consistent cache store regardless of how many replicas are running.

### Why Celery for ingestion instead of async background tasks?
FastAPI `BackgroundTasks` are in-process and not fault-tolerant — a restart kills pending work. Celery tasks survive restarts, support retries, priority queues, and distributed scaling.

### Why a 5-agent sequential pipeline instead of parallel?
Each agent's output is a direct input to the next stage (e.g., sentiment score feeds into the Forecaster context). True parallelism would require message passing and re-assembly that adds complexity without latency benefit given the sequential data dependency.
