"""
Data Processors Package — Ingestion Pipeline Middleware.

Provides validation, deduplication, and enrichment stages that sit between
raw data fetched from external sources and final database persistence.

Modules:
    data_validator: Pydantic-based schema validation for Reddit posts,
        news articles, price candles, and Google Trends records.
    deduplicator: Redis-backed (with in-memory fallback) duplicate
        detection using ``SET NX`` for idempotent ingestion.
    enricher: Technical indicator calculator (RSI, MACD, Bollinger
        Bands width) that enriches raw price candle records.
"""

from processors.data_validator import DataValidator
from processors.deduplicator import Deduplicator
from processors.enricher import TechnicalIndicatorEnricher

__all__ = [
    "DataValidator",
    "Deduplicator",
    "TechnicalIndicatorEnricher",
]
