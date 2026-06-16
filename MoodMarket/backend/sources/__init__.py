"""
Data Sources Package — External API Client Wrappers.

Each source client encapsulates connectivity to an external data provider
(Reddit, News APIs, Yahoo Finance, Google Trends) with automatic fallback
to realistic mock/simulated data when live credentials are unavailable.

Modules:
    reddit_source: Fetches posts from financial subreddits via PRAW.
    news_source: Fetches articles from NewsAPI with ticker-based queries.
    price_source: Pulls OHLCV candles from Yahoo Finance via yfinance.
    trends_source: Retrieves Google Trends interest scores via pytrends.
"""

from sources.reddit_source import RedditSourceClient
from sources.news_source import NewsSourceClient
from sources.price_source import PriceSourceClient
from sources.trends_source import GoogleTrendsSourceClient

__all__ = [
    "RedditSourceClient",
    "NewsSourceClient",
    "PriceSourceClient",
    "GoogleTrendsSourceClient",
]

# clean architecture alignment
