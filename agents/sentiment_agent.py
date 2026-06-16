import logging
import sys
import asyncio
from typing import Dict, Any, List
from agents.base_agent import BaseAgent

# Add root directory to path if needed for imports
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sentiment_ensemble import create_ensemble, SentimentEnsemble
    HAS_ENSEMBLE = True
except ImportError:
    HAS_ENSEMBLE = False

logger = logging.getLogger(__name__)

class SentimentAgent(BaseAgent):
    """
    Sentiment Analyst Agent
    
    Inputs: Reddit posts, news articles, tweets
    Task: Extract sentiment, identify key themes, determine social momentum
    Outputs: sentiment, confidence, key_topics, social_momentum
    """
    
    def __init__(self, config: Dict[str, Any], cache_ttl: int = 300):
        super().__init__("sentiment_analyst", config, cache_ttl)
        self.ensemble = None
        
        # Set up fallback lexicon from config or use standard defaults
        self.positive_words = set(config.get("lexicon", {}).get("positive", [
            "surge", "gain", "profit", "bullish", "growth", "buy", "upbeat", "record", 
            "beats", "innovation", "outperform", "success", "green", "climb", "high"
        ]))
        self.negative_words = set(config.get("lexicon", {}).get("negative", [
            "crash", "loss", "decline", "bearish", "drop", "sell", "regulatory", "disappoint", 
            "down", "investigate", "lawsuit", "fines", "red", "sink", "low", "fail"
        ]))
        self.neutral_words = set(config.get("lexicon", {}).get("neutral", [
            "hold", "flat", "market", "stock", "price", "quarter", "report", "earnings", 
            "meeting", "company", "shareholder", "update"
        ]))
        
        # Candidate topics to search for in text
        self.candidate_topics = ["earnings", "innovation", "competition", "regulatory", 
                                 "merger", "dividend", "debt", "macro", "supply_chain", 
                                 "valuation", "growth", "launch", "product"]
    
    def _lazy_load_ensemble(self):
        """Lazily load the Deep Learning SentimentEnsemble when requested and if available."""
        if self.ensemble is not None:
            return
            
        if HAS_ENSEMBLE and self.config.get("ensemble_enabled", True):
            try:
                # Get device from config
                device = self.config.get("device", "cpu")
                self.ensemble = create_ensemble(cache_enabled=True, device=device)
                self.logger.info("SentimentEnsemble loaded successfully inside SentimentAgent.")
            except Exception as e:
                self.logger.warning(
                    f"Could not load Deep Learning SentimentEnsemble: {e}. "
                    "Falling back to Lexicon-based sentiment scoring."
                )
                self.ensemble = None
        else:
            self.logger.info("SentimentEnsemble is disabled or not found. Using Lexicon sentiment fallback.")
    
    def get_relevant_input_keys(self) -> list:
        return ["reddit_posts", "news_articles", "tweets"]
    
    def _lexicon_analyze(self, texts: List[str]) -> Dict[str, Any]:
        """Perform simple lexicon-based financial sentiment scoring (offline fallback)"""
        total_score = 0.0
        total_words_checked = 0
        topic_counts = {t: 0 for t in self.candidate_topics}
        
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                continue
            
            words = text.lower().replace(",", " ").replace(".", " ").replace("!", " ").replace("?", " ").split()
            pos_count = 0
            neg_count = 0
            
            for word in words:
                if word in self.positive_words:
                    pos_count += 1
                elif word in self.negative_words:
                    neg_count += 1
                
                # Simple topic detection
                for topic in self.candidate_topics:
                    if topic in word:
                        topic_counts[topic] += 1
            
            # Sentence sentiment score
            denom = pos_count + neg_count
            if denom > 0:
                sentence_score = (pos_count - neg_count) / denom
                total_score += sentence_score
                total_words_checked += denom
        
        # Average score
        n_texts = len(texts)
        sentiment = total_score / max(n_texts, 1)
        sentiment = max(-1.0, min(1.0, sentiment))  # bound it
        
        # Calculate confidence
        # Confidence increases with the volume of relevant sentiment keywords checked
        confidence = min(0.5 + (total_words_checked / 20.0), 0.9)
        
        # Top topics
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        key_topics = [t[0] for t in sorted_topics[:3] if t[1] > 0]
        if not key_topics:
            key_topics = ["general", "market"]
            
        # Social momentum
        if sentiment > 0.15:
            social_momentum = "BULLISH"
        elif sentiment < -0.15:
            social_momentum = "BEARISH"
        else:
            social_momentum = "NEUTRAL"
            
        return {
            "sentiment": float(round(sentiment, 2)),
            "confidence": float(round(confidence, 2)),
            "key_topics": key_topics,
            "social_momentum": social_momentum
        }
    
    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Collect all texts
        reddit = payload.get("reddit_posts", [])
        news = payload.get("news_articles", [])
        tweets = payload.get("tweets", [])
        
        all_texts = []
        for src in [reddit, news, tweets]:
            if isinstance(src, list):
                all_texts.extend(src)
            elif isinstance(src, str):
                all_texts.append(src)
        
        if not all_texts:
            self.logger.warning("No texts found in input payload for sentiment analysis.")
            return self.get_fallback_output(payload, ValueError("Empty text inputs"))
        
        # Try Deep Learning Ensemble
        self._lazy_load_ensemble()
        if self.ensemble is not None:
            try:
                # SentimentEnsemble runs synchronous, execute in thread pool to be async-friendly
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(None, self.ensemble.analyze_batch, all_texts)
                
                # Aggregate results
                scores = [r.sentiment_score for r in results if r.label != "error"]
                confidences = [r.confidence for r in results if r.label != "error"]
                
                if scores:
                    mean_score = sum(scores) / len(scores)
                    mean_conf = sum(confidences) / len(confidences)
                    
                    if mean_score > 0.15:
                        social_momentum = "BULLISH"
                    elif mean_score < -0.15:
                        social_momentum = "BEARISH"
                    else:
                        social_momentum = "NEUTRAL"
                    
                    # Compute key topics via frequency count from words
                    topic_counts = {t: 0 for t in self.candidate_topics}
                    for text in all_texts:
                        for word in text.lower().split():
                            for topic in self.candidate_topics:
                                if topic in word:
                                    topic_counts[topic] += 1
                    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
                    key_topics = [t[0] for t in sorted_topics[:3] if t[1] > 0]
                    if not key_topics:
                        key_topics = ["general"]
                    
                    return {
                        "sentiment": float(round(mean_score, 2)),
                        "confidence": float(round(mean_conf, 2)),
                        "key_topics": key_topics,
                        "social_momentum": social_momentum
                    }
            except Exception as e:
                self.logger.warning(f"Ensemble processing failed: {e}. Falling back to lexicon analysis.")
        
        # Lexicon analyzer fallback (offline / error fallback)
        return self._lexicon_analyze(all_texts)
        
    def get_fallback_output(self, payload: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Provides a safe, neutral fallback if processing fails completely"""
        return {
            "sentiment": 0.0,
            "confidence": 0.5,
            "key_topics": ["market"],
            "social_momentum": "NEUTRAL",
            "error_fallback": str(error)
        }
