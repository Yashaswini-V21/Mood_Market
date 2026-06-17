# Changelog

All notable changes to **Mood Market** are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Planned
- Real-time Reddit WebSocket ingestion with Kafka consumer group
- ONNX export for Informer model (faster CPU inference)
- Grafana dashboard provisioning with pre-built panels
- Dark/light theme toggle in React frontend
- Helm chart for Kubernetes deployment

---

## [1.1.0] — 2026-06-17

### Added
- **ARCHITECTURE.md** — Deep technical guide covering system design, data flow, and component interactions
- **CHANGELOG.md** — This file; standardised versioning history
- **Makefile** — Developer convenience commands (`make run`, `make test`, `make lint`, `make docker-up`)
- `redis_connected` field added to `/api/v1/health` endpoint and `HealthResponse` schema
- Abstract `LogoMark` mini trendline icon in `banner.svg` for premium repo branding

### Fixed
- **`orchestrator.py`**: Removed conflicting `logging.basicConfig()` call that was overriding the structured JSON formatter configured by `setup_logging()` in `main.py`
- **`exceptions.py`** and **`middleware.py`**: Replaced deprecated `datetime.utcnow()` with timezone-aware `datetime.now(timezone.utc)` (Python 3.12+ deprecation)
- **`docker-compose.yml`**: Removed deprecated `version: '3.9'` key (Docker Compose v2 spec)
- **`models.py`**: `HealthResponse` Pydantic schema now includes `redis_connected` field — previously the health route returned it but the model silently stripped it from the serialised response
- Removed 103 boilerplate `# clean architecture alignment` trailing comments across all source files

### Changed
- `banner.svg` refreshed: split-colour title (`MOOD` in vibrant magenta→purple gradient, `MARKET` in solid white), mini glowing trendline logo mark centred above the text, subtle grid background texture at 2.5% opacity

---

## [1.0.0] — 2026-06-16

### Added
- **Multi-Agent Trading Desk**: 5-agent async pipeline — `SentimentAgent` → `TechnicalAgent` → `ForecasterAgent` → `RiskManagerAgent` → `SynthesizerAgent`
- **Informer Transformer** (ProbSparse O(L log L) attention) trained on 100 k synthetic samples; 4-hour direction + uncertainty head
- **FinBERT + DistilBERT** sentiment ensemble with lexicon fallback when GPU is unavailable
- **HypeStorm Radar™** 7-method anomaly detection stack: Z-score, EWMA, Isolation Forest, Autoencoder, volume spike, cross-asset correlation, social velocity
- **SHAP + Attention Rollout** explainability endpoint (`GET /api/v1/explain/{id}`)
- **JWT-authenticated WebSocket** streams for live sentiment, price, and anomaly feeds
- **Redis cache** (TTL=300s) on all hot-path API endpoints; cache warmer pre-loads top-50 tickers on startup
- **Prometheus `/metrics`** + Grafana dashboard integration
- **Celery** task queue (4 workers) + Beat scheduler for background ingestion
- **TimescaleDB** primary store with SQLite aiosqlite fallback for CI/dev
- **React + Vite + TypeScript** frontend with Tailwind CSS
- CI/CD: 4 GitHub Actions workflows (`test.yml`, `security.yml`, `build.yml`, `performance.yml`)
- Docker Compose 9-service stack (Postgres, Redis, Backend, Worker, Beat, Flower, Frontend, Kafka, Prometheus, Grafana)
- Monorepo reorganised into `MoodMarket/{backend,frontend,ml,test,doc}` layout

### Infrastructure
- `Dockerfile` (backend) uses Python 3.11-slim with multi-stage layer caching
- `.coveragerc` configured for 80%+ coverage gate
- `pyproject.toml` defines project metadata, linting, and mypy settings
- `requirements-ci.txt` strips heavy PyTorch/transformer wheels for fast CI installs
