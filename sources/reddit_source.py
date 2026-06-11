import logging
import time
from typing import List, Dict, Any
from datetime import datetime

from config import api_settings

logger = logging.getLogger("sources.reddit")


class RedditSourceClient:
    """Wrapper around PRAW for fetching posts from financial subreddits."""
    
    def __init__(self):
        self.client_id = api_settings.reddit_client_id
        self.client_secret = api_settings.reddit_client_secret
        self.user_agent = api_settings.reddit_user_agent
        self.is_mock = (self.client_id == "mock_reddit_client_id" or "mock" in self.client_id)

    def fetch_posts(self, subreddit_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetches top hot posts from a given subreddit.
        If credentials are mock, returns simulated stock-talk posts.
        """
        if self.is_mock:
            logger.info(f"Using mock data for subreddit '{subreddit_name}'")
            return self._generate_mock_posts(subreddit_name, limit)

        try:
            import praw
            reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            subreddit = reddit.subreddit(subreddit_name)
            
            posts = []
            for submission in subreddit.hot(limit=limit):
                posts.append({
                    "id": f"reddit_{submission.id}",
                    "title": submission.title,
                    "text": submission.selftext,
                    "subreddit": subreddit_name,
                    "score": int(submission.score),
                    "created_utc": float(submission.created_utc),
                    "timestamp": datetime.utcfromtimestamp(submission.created_utc).isoformat()
                })
            return posts
        except Exception as e:
            logger.warning(f"Reddit PRAW execution failed: {e}. Falling back to mock generator.")
            return self._generate_mock_posts(subreddit_name, limit)

    def _generate_mock_posts(self, subreddit: str, limit: int) -> List[Dict[str, Any]]:
        import random
        stock_sentences = [
            "Apple is showing incredibly strong buy patterns on MACD right now.",
            "Is anyone holding Tesla shares through the regulator checks? Sell or hold?",
            "Nvidia profit margins surge. Beats every single consensus estimate!",
            "CPI figures could crash tech stocks next week, prepare for bearish downturn.",
            "AMD launch represents huge competition. Buying more leaps today.",
            "Is WallStreetBets bullish on Apple for the record quarter?",
            "Regulatory fines face Google on search monopoly. This is a severe drop."
        ]
        
        posts = []
        for i in range(limit):
            post_id = f"mock_reddit_{subreddit}_{int(time.time())}_{i}"
            title = random.choice(stock_sentences)
            score = random.randint(10, 1500)
            posts.append({
                "id": post_id,
                "title": title,
                "text": "Self post text detail. Long position is standard here.",
                "subreddit": subreddit,
                "score": score,
                "created_utc": time.time() - (i * 60),
                "timestamp": datetime.utcnow().isoformat()
            })
        return posts
