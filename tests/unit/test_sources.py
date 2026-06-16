import unittest
import sys
import os

# Adjust path to import from parent folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.reddit_source import RedditSourceClient
from sources.news_source import NewsSourceClient
from sources.price_source import PriceSourceClient
from sources.trends_source import GoogleTrendsSourceClient


class TestSources(unittest.TestCase):
    """
    Unit tests for the external data ingestion wrappers (Reddit, News, Price, Google Trends).
    Verifies retrieval APIs and simulated/mock data generators.
    """

    def test_reddit_source_fetching(self):
        """Test Reddit client fetches hot posts and structures them correctly"""
        client = RedditSourceClient()
        posts = client.fetch_posts("wallstreetbets", limit=10)
        self.assertEqual(len(posts), 10)
        self.assertEqual(posts[0]["subreddit"], "wallstreetbets")
        self.assertIn("title", posts[0])
        self.assertIn("score", posts[0])
        self.assertIn("timestamp", posts[0])

    def test_news_source_fetching(self):
        """Test News client parses articles and resolves entity ticker"""
        client = NewsSourceClient()
        articles = client.fetch_articles("AAPL", ["Apple", "iPhone"], limit=5)
        self.assertEqual(len(articles), 5)
        self.assertEqual(articles[0]["ticker"], "AAPL")
        self.assertIn("title", articles[0])
        self.assertIn("published_at", articles[0])
        self.assertIn("source", articles[0])

    def test_price_source_fetching(self):
        """Test Price client returns OHLCV financial price candles"""
        client = PriceSourceClient()
        candles = client.fetch_price_history("MSFT", interval="15m", period="1d")
        self.assertTrue(len(candles) > 0)
        self.assertEqual(candles[0]["ticker"], "MSFT")
        self.assertIn("close", candles[0])
        self.assertIn("volume", candles[0])
        self.assertIn("timestamp", candles[0])

    def test_google_trends_fetching(self):
        """Test Google Trends client retrieves interest levels"""
        client = GoogleTrendsSourceClient()
        trends = client.fetch_trends("NVDA", timeframe="now 7-d")
        self.assertTrue(len(trends) > 0)
        self.assertEqual(trends[0]["ticker"], "NVDA")
        self.assertIn("interest", trends[0])
        self.assertTrue(0.0 <= trends[0]["interest"] <= 100.0)


if __name__ == "__main__":
    unittest.main()
