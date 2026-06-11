<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a2e,50:16213e,100:0f3460&height=200&section=header&text=Mood%20Market&fontSize=70&fontColor=e94560&animation=fadeIn&fontAlignY=38&desc=Where%20Sentiment%20Meets%20Alpha&descAlignY=58&descSize=20&descColor=a8b2d8" width="100%"/>

<br/>

<p>
  <a href="https://github.com/Yashaswini-V21/Mood_Market/stargazers">
    <img src="https://img.shields.io/github/stars/Yashaswini-V21/Mood_Market?style=for-the-badge&logo=github&color=e94560&labelColor=1a1a2e" alt="Stars"/>
  </a>
  <a href="https://github.com/Yashaswini-V21/Mood_Market/network/members">
    <img src="https://img.shields.io/github/forks/Yashaswini-V21/Mood_Market?style=for-the-badge&logo=github&color=0f3460&labelColor=1a1a2e" alt="Forks"/>
  </a>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a2e"/>
  <img src="https://img.shields.io/badge/PyTorch-2.2+-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white&labelColor=1a1a2e"/>
  <img src="https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white&labelColor=1a1a2e"/>
  <img src="https://img.shields.io/badge/Redis-7.0+-DC382D?style=for-the-badge&logo=redis&logoColor=white&labelColor=1a1a2e"/>
  <img src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge&labelColor=1a1a2e"/>
</p>

<br/>

> **"The market moves on emotion. We decode it."**
>
> *Mood Market* is an enterprise-grade AI trading intelligence platform that fuses real-time social sentiment signals — Reddit threads, Twitter hype, Google Trends — with deep learning price forecasting to give traders an **unfair edge** before the crowd catches on.

<br/>

```
╔══════════════════════════════════════════════════════════════════╗
║  📡 Live Sentiment  →  🧠 Informer Model  →  🚨 Hype Alerts     ║
║  Reddit | Twitter | News  →  65%+ Accuracy  →  <30ms Latency   ║
╚══════════════════════════════════════════════════════════════════╝
```

</div>

---

## ✨ What Makes Mood Market Different

| Feature | Ordinary Trading Bot | 🚀 Mood Market |
|---|---|---|
| **Signal Source** | Price data only | Price + Reddit + Twitter + Google Trends |
| **Model** | Simple LSTM | Informer with ProbSparse Attention |
| **Complexity** | O(L²) attention | O(L log L) — 5× faster on long sequences |
| **Explainability** | None | Full SHAP + Attention heat maps |
| **Anomaly Detection** | Threshold rules | 7-method ensemble (Z-Score, IF, Autoencoder, EWMA…) |
| **Real-time** | Polling | WebSocket push @ sub-second latency |
| **Caching** | None | Multi-layer Redis — 70%+ hit rate |
| **Agents** | Single script | 5-agent async desk (Analyst → Risk → Synthesizer) |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MOOD MARKET                              │
│                                                                 │
│   📱 Dashboard / Clients                                        │
│        │  WebSocket (JWT auth)  │  REST API                    │
│        ▼                        ▼                               │
│   ┌─────────────┐        ┌──────────────┐                       │
│   │  FastAPI    │◄──────►│ Redis Cache  │ ← 70%+ hit rate      │
│   │  Server     │        │  Layer       │                       │
│   └──────┬──────┘        └──────────────┘                       │
│          │                                                      │
│          ▼  Celery Priority Queues                              │
│   ┌──────────────────────────────────────────┐                  │
│   │  critical → priority → default → low    │                  │
│   └──────┬───────────┬───────────┬───────────┘                  │
│          │           │           │                              │
│          ▼           ▼           ▼                              │
│   ┌────────┐  ┌─────────────┐  ┌──────────────┐                │
│   │ Reddit │  │  Informer   │  │   Anomaly    │                │
│   │Twitter │  │  Forecaster │  │   Detector   │                │
│   │ News   │  │  (ProbSparse│  │  (7-method   │                │
│   │Scraper │  │  Attention) │  │   ensemble)  │                │
│   └────────┘  └─────────────┘  └──────────────┘                │
│          │           │                                          │
│          ▼           ▼                                          │
│   ┌──────────────────────────────┐                              │
│   │  TimescaleDB Hypertables     │ ← 1-day chunks, 2yr retain  │
│   │  + SQLite Fallback           │                              │
│   └──────────────────────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Core Intelligence Stack

### 1️⃣ Informer — ProbSparse Attention Forecaster

> Predicts price direction probability for the next 4 hours with confidence intervals

```python
# 72 timesteps in → direction probability + uncertainty out
prediction, uncertainty, attention_weights = model(encoder_input, decoder_input)
# prediction ∈ [0,1]  |  uncertainty → confidence interval  |  attn → explainability
```

**Why Informer over LSTM?**
- Standard Transformer: O(L²) memory → bottleneck on 72-step sequences
- **Informer ProbSparse**: O(L log L) → selects only the most informative queries
- Built-in uncertainty quantification → Monte Carlo dropout at inference

---

### 2️⃣ Multi-Agent Trading Desk

Five async AI agents working in concert, like a real hedge fund:

```
📰 Sentiment Analyst  →  reads Reddit/news/Twitter, scores sentiment
📊 Technical Analyst  →  computes RSI, MACD, Bollinger Bands
🔮 Forecaster Agent   →  runs Informer model, outputs probability
🛡️  Risk Manager      →  calculates position size, stop-loss, targets
✍️  Synthesizer Desk  →  merges all signals → final actionable decision
```

---

### 3️⃣ Hype Storm Anomaly Detector

Detects coordinated social media pumps **before** price moves:

| Detector | Method | Signal |
|---|---|---|
| Z-Score | Statistical baseline | Sudden volume σ spike |
| Multi-Var Z-Score | Cross-channel correlation | Reddit + Twitter spike together |
| Isolation Forest | ML outlier detection | Non-linear anomaly |
| Autoencoder | Deep reconstruction error | Pattern unlike "normal" |
| EWMA | Volatility tracking | Accelerating hype wave |
| Adaptive EWMA | Regime-aware | Detects regime shifts |
| Ensemble Vote | Weighted 7-method | Final alert confidence |

**Alert levels:** `NORMAL` → `ELEVATED` → `HYPE_STORM` 🚨

---

### 4️⃣ Real-time WebSocket Engine

```
/ws/price      → live price feed, <1s latency
/ws/sentiment  → live sentiment score stream
/ws/anomaly    → hype storm alerts, pushed instantly
```

JWT-authenticated, group-based pub/sub with keep-alive heartbeats.

---

## 📂 Project Structure

```
Mood_Market/
│
├── 🤖 agents/                  # Async multi-agent trading desk
│   ├── sentiment_agent.py      # Social signal scorer
│   ├── technical_agent.py      # RSI, MACD, BB indicators
│   ├── forecaster_agent.py     # Informer inference wrapper
│   ├── risk_manager_agent.py   # Position sizing & stops
│   └── synthesizer_agent.py    # Decision aggregator
│
├── 🧩 detectors/               # Anomaly detection suite
│   ├── zscore_detector.py      # Statistical baseline
│   ├── isolation_forest_detector.py
│   ├── autoencoder_detector.py
│   └── ewma_detector.py        # Volatility regime detector
│
├── 🌐 routes/                  # FastAPI REST endpoints
│   ├── sentiment.py            # GET /sentiment/{ticker}
│   ├── forecast.py             # GET /price/forecast/{ticker}
│   ├── anomaly.py              # GET /anomaly/{ticker}
│   ├── pipeline.py             # GET /pipeline/{ticker}
│   └── explain.py              # SHAP + attention plots
│
├── ⚙️  celery/                 # Background task pipeline
│   └── tasks/
│       ├── ingestion_tasks.py  # Reddit, Twitter, news scrapers
│       ├── analysis_tasks.py   # Sentiment + anomaly workers
│       ├── prediction_tasks.py # Informer inference queue
│       └── maintenance_tasks.py# Cleanup, compression
│
├── 🧪 tests/                   # 14-file test suite
│   ├── test_anomaly.py         # 26 detector tests
│   ├── test_cache.py           # Redis fallback, stats, TTL
│   ├── test_informer.py        # 12 model + inference tests
│   ├── test_sentiment.py       # Drift, cache, monitoring
│   ├── test_shap.py            # Explainability coverage
│   └── ...                     # +9 more test files
│
├── 📖 examples/                # Runnable usage demos
│   ├── examples.py             # Informer inference demos
│   └── examples_anomaly.py     # GME squeeze, DOGE pump sims
│
├── 🗄️  migrations/             # TimescaleDB schema
│   └── 001_initial_schema.sql  # Hypertables + compression
│
├── 🐳 docker/                  # Container configs
│   └── docker-compose.yml      # Full local stack
│
├── model.py                    # Informer architecture
├── trainer.py                  # FP16 training + Optuna tuning
├── inference.py                # Real-time prediction engine
├── anomaly_detector.py         # Orchestrator for 7 detectors
├── sentiment_ensemble.py       # Multi-model sentiment fusion
├── visualization.py            # SHAP plots + attention maps
├── cache.py                    # Redis cache manager
├── websocket_server.py         # Live data broadcaster
├── database.py                 # TimescaleDB + SQLite fallback
├── config.yaml                 # Hyperparameter config
└── requirements.txt
```

---

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.10+  |  Redis 7+  |  (Optional) PostgreSQL + TimescaleDB
```

### 1. Clone & Install
```bash
git clone https://github.com/Yashaswini-V21/Mood_Market.git
cd Mood_Market
python -m venv venv && source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Redis URL, DB connection, API keys
```

### 3. Launch Full Stack (Docker)
```bash
docker-compose up --build
# API   → http://localhost:8000
# Docs  → http://localhost:8000/docs
# Flower→ http://localhost:5555
```

### 4. Or run locally
```bash
# Terminal 1 – API server
python main.py

# Terminal 2 – Celery workers
celery -A celery_app worker --loglevel=info -Q critical,priority,default,low

# Terminal 3 – Task scheduler
celery -A celery_app beat --loglevel=info
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/sentiment/{ticker}` | Latest sentiment score |
| `POST` | `/api/v1/sentiment/predict` | Analyze custom text |
| `GET` | `/api/v1/price/forecast/{ticker}` | 4-hour price direction |
| `GET` | `/api/v1/anomaly/{ticker}` | Hype storm status |
| `GET` | `/api/v1/pipeline/{ticker}` | Full analysis bundle |
| `GET` | `/api/v1/explain/{ticker}` | SHAP + attention viz |
| `WS` | `/ws/price` | Live price stream |
| `WS` | `/ws/sentiment` | Live sentiment stream |
| `WS` | `/ws/anomaly` | Live anomaly alerts |

**Interactive docs:** `http://localhost:8000/docs`

---

## 🧪 Running Tests

```bash
# Full suite (143 tests across 14 files)
python -m pytest --tb=short -q

# Individual suites
python tests/test_anomaly.py    # Anomaly detector (26 tests)
python tests/test_cache.py      # Redis cache (8 tests)
python tests/test_sentiment.py  # Sentiment pipeline
python tests/test_informer.py   # Informer model (12 tests)
```

---

## 📊 Model Performance

| Metric | LSTM Baseline | 🚀 Informer |
|---|---|---|
| Directional Accuracy | 50.1% | **65%+** (trained) |
| P50 Latency | 11.6ms | 20.2ms |
| P99 Latency | 49ms | 45ms after INT8 |
| False Positive Rate | — | **<5%** anomaly FPR |
| Anomaly Detection Latency | — | **<30ms** per stock |
| Max Stocks Supported | — | **500** concurrent |
| INT8 Size Reduction | 3.9× | **3.8×** |
| Explainability | ❌ | ✅ SHAP + Attention |

---

## 🛠️ Training Your Own Model

```bash
# Train with default config (100 epochs, early stopping)
python train.py

# Override epochs
python train.py --epochs 50

# Run Optuna hyperparameter tuning (10 trials)
python train.py --tune

# Benchmark Informer vs LSTM
python benchmark.py
```

Config at [`config.yaml`](config.yaml) — tweak `d_model`, `n_heads`, `factor`, `dropout`.

---

## 🗃️ Database Schema (TimescaleDB)

```sql
-- Hypertables with 1-day chunks for ultra-fast time-range queries
sentiment_data       → (time, ticker, sentiment_score, confidence, source)
price_data           → (time, ticker, open, high, low, close, volume, vwap)
technical_indicators → (time, ticker, rsi, macd, bb_upper, bb_lower)
predictions          → (time, ticker, predicted_direction, confidence_interval)
anomaly_alerts       → (time, ticker, alert_type, confidence, methods_triggered)

-- Continuous Aggregates (materialized, auto-refreshed)
daily_sentiment_avg  → per-ticker daily sentiment summary
hourly_price_ohlc    → 1-hour candle rollups

-- Auto-compression after 30 days | Auto-drop after 2 years
```

---

## 🔮 Roadmap

- [ ] 🌍 Live Reddit & Twitter API integration
- [ ] 📱 React dashboard with real-time charts
- [ ] 🤖 GPT-4 powered news summarizer agent
- [ ] 🏦 Alpaca / Interactive Brokers order execution
- [ ] 📈 Portfolio-level risk analytics
- [ ] 🔔 Telegram / Discord alert bot integration
- [ ] 🧬 Reinforcement learning trading agent

---

## 👩‍💻 Author

<div align="center">

**Yashaswini V**

[![GitHub](https://img.shields.io/badge/GitHub-Yashaswini--V21-181717?style=for-the-badge&logo=github&labelColor=1a1a2e)](https://github.com/Yashaswini-V21)

*Building at the intersection of AI and financial markets*

</div>

---

## 📜 License

```
MIT License — free for academic and commercial use.
Built with 💙 and a lot of caffeine.
```

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a2e,50:16213e,100:0f3460&height=100&section=footer" width="100%"/>

⭐ **Star this repo if Mood Market gave you alpha!** ⭐

</div>
