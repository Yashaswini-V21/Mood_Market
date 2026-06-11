import logging
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta

from config import api_settings

logger = logging.getLogger("sources.news")


class NewsSourceClient:
    """Wrapper around NewsAPI for fetching articles containing financial keywords."""
    
    def __init__(self):
        self.api_key = api_settings.news_api_key
        self.is_mock = (self.api_key == "mock_news_api_key" or "mock" in self.api_key)

    def fetch_articles(self, ticker: str, keywords: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Queries NewsAPI for stock articles.
        If credentials are mock, returns simulated financial news text.
        """
        if self.is_mock:
            logger.info(f"Using mock data for News API ticker '{ticker}'")
            return self._generate_mock_articles(ticker, limit)

        try:
            from newsapi import NewsApiClient
            newsapi_client = NewsApiClient(api_key=self.api_key)
            
            # Combine ticker with keywords
            query_str = f"{ticker} AND ({' OR '.join(keywords)})"
            
            # Query last 3 days
            from_date = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
            
            response = newsapi_client.get_everything(
                q=query_str,
                from_param=from_date,
                sort_by="relevance",
                page_size=limit
            )
            
            articles = []
            if response.get("status") == "ok":
                for item in response.get("articles", []):
                    title = item.get("title", "")
                    desc = item.get("description", "")
                    content = item.get("content", "")
                    url = item.get("url", "")
                    # Generate unique ID based on URL
                    import hashlib
                    url_hash = hashlib.md5(url.encode()).hexdigest()
                    
                    articles.append({
                        "id": f"news_{url_hash}",
                        "title": title,
                        "description": desc,
                        "text": f"{title}. {desc}. {content}",
                        "url": url,
                        "source": item.get("source", {}).get("name", "Unknown"),
                        "published_at": item.get("publishedAt", datetime.utcnow().isoformat()),
                        "ticker": ticker
                    })
            return articles
        except Exception as e:
            logger.warning(f"NewsAPI query failed: {e}. Falling back to mock generator.")
            return self._generate_mock_articles(ticker, limit)

    def _generate_mock_articles(self, ticker: str, limit: int) -> List[Dict[str, Any]]:
        import random
        headlines = [
            f"Analysts raise price targets for {ticker} following upbeat quarterly margins.",
            f"Major institutional players buy more {ticker} equity ahead of analyst meeting.",
            f"Stocks watch: {ticker} faces supply chain constraints in Asian tech sectors.",
            f"Regulatory headwinds increase for {ticker} search and advertising divisions.",
            f"Merger talks confirmed: {ticker} acquiring major competitor in record deal.",
            f"Dividend hike announced by {ticker} board of directors.",
            f"Market analyst rates {ticker} as strong sell due to high valuations."
        ]
        
        articles = []
        for i in range(limit):
            import hashlib
            url = f"https://finance.yahoo.com/news/mock-{ticker.lower()}-{i}.html"
            url_hash = hashlib.md5(url.encode()).hexdigest()
            
            title = random.choice(headlines)
            desc = "Financial market indexes fluctuate as analysts revise earnings projections."
            articles.append({
                "id": f"mock_news_{url_hash}",
                "title": title,
                "description": desc,
                "text": f"{title}. {desc} Summary of news details.",
                "url": url,
                "source": "Yahoo Finance",
                "published_at": (datetime.utcnow() - timedelta(minutes=i*10)).isoformat(),
                "ticker": ticker
            })
        return articles
