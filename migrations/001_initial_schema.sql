-- c:\Mood_Market\migrations\001_initial_schema.sql
-- TimescaleDB initial schema setup

-- Enable TimescaleDB extension if not already enabled
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 1. Table Definitions

-- Sentiment Data (hypertable)
CREATE TABLE IF NOT EXISTS sentiment_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    sentiment_score DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    source VARCHAR(32) NOT NULL, -- reddit, news, twitter, etc.
    text_sample TEXT,
    model_version VARCHAR(32) NOT NULL,
    CONSTRAINT chk_sentiment CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),
    CONSTRAINT chk_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

-- Price Data (hypertable)
CREATE TABLE IF NOT EXISTS price_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    vwap DOUBLE PRECISION NOT NULL,
    CONSTRAINT chk_prices CHECK (open > 0 AND high > 0 AND low > 0 AND close > 0 AND volume >= 0)
);

-- Technical Indicators (hypertable)
CREATE TABLE IF NOT EXISTS technical_indicators (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    rsi DOUBLE PRECISION NOT NULL,
    macd DOUBLE PRECISION NOT NULL,
    bb_upper DOUBLE PRECISION NOT NULL,
    bb_lower DOUBLE PRECISION NOT NULL,
    bb_middle DOUBLE PRECISION NOT NULL,
    volume_profile JSONB,
    CONSTRAINT chk_rsi CHECK (rsi >= 0.0 AND rsi <= 100.0)
);

-- Predictions (hypertable)
CREATE TABLE IF NOT EXISTS predictions (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    predicted_direction VARCHAR(8) NOT NULL, -- UP or DOWN
    predicted_price DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    actual_outcome VARCHAR(8), -- UP, DOWN, or NULL
    model_used VARCHAR(64) NOT NULL
);

-- Anomalies (hypertable)
CREATE TABLE IF NOT EXISTS anomalies (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    anomaly_type VARCHAR(32) NOT NULL, -- hype_storm, crash, volatility_spike, etc.
    confidence DOUBLE PRECISION NOT NULL,
    explanation TEXT
);

-- User Watchlists (regular table)
CREATE TABLE IF NOT EXISTS user_watchlists (
    user_id VARCHAR(64) NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    removed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id, ticker)
);

-- API Logs (hypertable)
CREATE TABLE IF NOT EXISTS api_logs (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    endpoint VARCHAR(128) NOT NULL,
    status_code INTEGER NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    user_id VARCHAR(64)
);

-- 2. Enable Hypertables (Partitioning by time in 1-day chunks)
SELECT create_hypertable('sentiment_data', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
SELECT create_hypertable('price_data', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
SELECT create_hypertable('technical_indicators', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
SELECT create_hypertable('predictions', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
SELECT create_hypertable('anomalies', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
SELECT create_hypertable('api_logs', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

-- 3. Indexes Setup

-- Hypertables primary indexes (time, ticker) for time-series range queries
CREATE INDEX IF NOT EXISTS idx_sentiment_time_ticker ON sentiment_data (time DESC, ticker);
CREATE INDEX IF NOT EXISTS idx_price_time_ticker ON price_data (time DESC, ticker);
CREATE INDEX IF NOT EXISTS idx_indicators_time_ticker ON technical_indicators (time DESC, ticker);
CREATE INDEX IF NOT EXISTS idx_predictions_time_ticker ON predictions (time DESC, ticker);
CREATE INDEX IF NOT EXISTS idx_anomalies_time_ticker ON anomalies (time DESC, ticker);
CREATE INDEX IF NOT EXISTS idx_api_logs_time ON api_logs (time DESC);

-- Secondary indexes (ticker, time) for per-stock analytics
CREATE INDEX IF NOT EXISTS idx_sentiment_ticker_time ON sentiment_data (ticker, time DESC);
CREATE INDEX IF NOT EXISTS idx_price_ticker_time ON price_data (ticker, time DESC);
CREATE INDEX IF NOT EXISTS idx_indicators_ticker_time ON technical_indicators (ticker, time DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_ticker_time ON predictions (ticker, time DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_ticker_time ON anomalies (ticker, time DESC);

-- Partial index for high confidence anomalies
CREATE INDEX IF NOT EXISTS idx_anomalies_high_conf ON anomalies (ticker, time DESC) WHERE confidence >= 0.90;

-- 4. Materialized Views (TimescaleDB Continuous Aggregates)

-- Daily sentiment averages per ticker
CREATE MATERIALIZED VIEW IF NOT EXISTS sentiment_daily_avg
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 day', time) AS bucket,
       ticker,
       AVG(sentiment_score) AS avg_sentiment,
       AVG(confidence) AS avg_confidence,
       COUNT(*) AS total_samples
FROM sentiment_data
GROUP BY bucket, ticker;

-- Hourly price ranges
CREATE MATERIALIZED VIEW IF NOT EXISTS price_hourly_range
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 hour', time) AS bucket,
       ticker,
       FIRST(open, time) AS open,
       MAX(high) AS high,
       MIN(low) AS low,
       LAST(close, time) AS close,
       SUM(volume) AS volume
FROM price_data
GROUP BY bucket, ticker;

-- Weekly returns
CREATE MATERIALIZED VIEW IF NOT EXISTS weekly_returns
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '7 days', time) AS bucket,
       ticker,
       (LAST(close, time) - FIRST(open, time)) / FIRST(open, time) AS weekly_return_pct
FROM price_data
GROUP BY bucket, ticker;

-- 5. Data Compression Policies (Automatic after 30 days)
ALTER TABLE sentiment_data SET (timescaledb.compress, timescaledb.compress_segmentby = 'ticker', timescaledb.compress_orderby = 'time DESC');
ALTER TABLE price_data SET (timescaledb.compress, timescaledb.compress_segmentby = 'ticker', timescaledb.compress_orderby = 'time DESC');
ALTER TABLE technical_indicators SET (timescaledb.compress, timescaledb.compress_segmentby = 'ticker', timescaledb.compress_orderby = 'time DESC');
ALTER TABLE predictions SET (timescaledb.compress, timescaledb.compress_segmentby = 'ticker', timescaledb.compress_orderby = 'time DESC');
ALTER TABLE anomalies SET (timescaledb.compress, timescaledb.compress_segmentby = 'ticker', timescaledb.compress_orderby = 'time DESC');
ALTER TABLE api_logs SET (timescaledb.compress, timescaledb.compress_orderby = 'time DESC');

SELECT add_compression_policy('sentiment_data', INTERVAL '30 days');
SELECT add_compression_policy('price_data', INTERVAL '30 days');
SELECT add_compression_policy('technical_indicators', INTERVAL '30 days');
SELECT add_compression_policy('predictions', INTERVAL '30 days');
SELECT add_compression_policy('anomalies', INTERVAL '30 days');
SELECT add_compression_policy('api_logs', INTERVAL '30 days');

-- 6. Retention Policies (Automatic raw data drop after 2 years)
SELECT add_retention_policy('sentiment_data', INTERVAL '2 years');
SELECT add_retention_policy('price_data', INTERVAL '2 years');
SELECT add_retention_policy('technical_indicators', INTERVAL '2 years');
SELECT add_retention_policy('predictions', INTERVAL '2 years');
SELECT add_retention_policy('anomalies', INTERVAL '2 years');
SELECT add_retention_policy('api_logs', INTERVAL '2 years');
