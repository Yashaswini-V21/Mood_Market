"""
Production-grade Sentiment Analysis Ensemble Pipeline
Combines FinBERT and DistilBERT with confidence-weighted voting,
caching, and async support for financial text analysis.
"""

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import asyncio
from pathlib import Path
import logging
from collections import deque
from functools import lru_cache
import hashlib
import json

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    pipeline,
    TextClassificationPipeline
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Dataclass for sentiment analysis results"""
    text: str
    sentiment_score: float  # -1.0 to +1.0
    confidence: float  # 0 to 1
    label: str  # "positive", "negative", "neutral"
    individual_scores: Dict[str, float]  # {"finbert": float, "distilbert": float}
    model_confidences: Dict[str, float]  # {"finbert": float, "distilbert": float}
    timestamp: datetime
    tokens_importance: Optional[List[Tuple[str, float]]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class SentimentCache:
    """LRU cache with TTL for sentiment predictions"""
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        """
        Args:
            max_size: Maximum cache size
            ttl_seconds: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[SentimentResult, datetime]] = {}
        self.access_times: deque = deque(maxlen=max_size)
    
    def _hash_text(self, text: str) -> str:
        """Create hash of text for caching"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def get(self, text: str) -> Optional[SentimentResult]:
        """
        Get cached result if exists and not expired
        
        Args:
            text: Input text
        
        Returns:
            Cached result or None
        """
        cache_key = self._hash_text(text)
        
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            
            # Check if expired
            if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                return result
            else:
                # Remove expired entry
                del self.cache[cache_key]
        
        return None
    
    def put(self, text: str, result: SentimentResult) -> None:
        """
        Store result in cache
        
        Args:
            text: Input text
            result: Analysis result
        """
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        cache_key = self._hash_text(text)
        self.cache[cache_key] = (result, datetime.now())
        self.access_times.append(cache_key)
    
    def clear(self) -> None:
        """Clear cache"""
        self.cache.clear()
        self.access_times.clear()
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds
        }


class SentimentEnsemble:
    """
    Ensemble sentiment analyzer combining FinBERT and DistilBERT
    with confidence-weighted voting and caching.
    """
    
    def __init__(
        self,
        finbert_model: str = "ProsusAI/finbert",
        distilbert_model: str = "distilbert-base-uncased-finetuned-financial",
        weights: Optional[Dict[str, float]] = None,
        confidence_threshold: float = 0.7,
        cache_enabled: bool = True,
        device: Optional[str] = None,
        batch_size: int = 32
    ) -> None:
        """
        Initialize sentiment ensemble
        
        Args:
            finbert_model: FinBERT model ID
            distilbert_model: DistilBERT model ID
            weights: Model weights for voting {model_name: weight}
            confidence_threshold: Minimum confidence for prediction
            cache_enabled: Whether to use caching
            device: "cuda" or "cpu"
            batch_size: Batch size for inference
        """
        self.finbert_model_id = finbert_model
        self.distilbert_model_id = distilbert_model
        self.confidence_threshold = confidence_threshold
        self.batch_size = batch_size
        
        # Determine device
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        
        logger.info(f"Using device: {self.device}")
        
        # Default weights (FinBERT typically more accurate for financial text)
        self.weights = weights or {
            "finbert": 0.6,
            "distilbert": 0.4
        }
        
        # Normalize weights
        total_weight = sum(self.weights.values())
        self.weights = {k: v / total_weight for k, v in self.weights.items()}
        
        # Initialize cache
        self.cache = SentimentCache(max_size=10000, ttl_seconds=3600) if cache_enabled else None
        
        # Model pipelines
        self.finbert_pipeline = None
        self.distilbert_pipeline = None
        
        # Load models
        self._load_models()
        
        # Performance tracking
        self.inference_times: deque = deque(maxlen=1000)
        self.disagreement_count = 0
        self.total_predictions = 0
    
    def _load_models(self) -> None:
        """Load transformer models"""
        try:
            logger.info(f"Loading FinBERT from {self.finbert_model_id}...")
            tokenizer_finbert = AutoTokenizer.from_pretrained(self.finbert_model_id)
            model_finbert = AutoModelForSequenceClassification.from_pretrained(
                self.finbert_model_id,
                device_map=self.device
            )
            
            self.finbert_pipeline = pipeline(
                "sentiment-analysis",
                model=model_finbert,
                tokenizer=tokenizer_finbert,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True
            )
            logger.info("✓ FinBERT loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}")
            raise
        
        try:
            logger.info(f"Loading DistilBERT from {self.distilbert_model_id}...")
            tokenizer_distil = AutoTokenizer.from_pretrained(self.distilbert_model_id)
            model_distil = AutoModelForSequenceClassification.from_pretrained(
                self.distilbert_model_id,
                device_map=self.device
            )
            
            self.distilbert_pipeline = pipeline(
                "sentiment-analysis",
                model=model_distil,
                tokenizer=tokenizer_distil,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True
            )
            logger.info("✓ DistilBERT loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load DistilBERT: {e}")
            logger.warning("Continuing with FinBERT only (degraded mode)")
            self.distilbert_pipeline = None
    
    def _label_to_score(self, label: str, scores: Dict[str, float]) -> Tuple[float, str]:
        """
        Convert label and scores to -1.0 to 1.0 sentiment score
        
        Args:
            label: Sentiment label
            scores: Score dict from model
        
        Returns:
            Tuple of (sentiment_score, normalized_label)
        """
        # FinBERT uses: negative, neutral, positive
        # DistilBERT uses: LABEL_0 (negative), LABEL_1 (positive)
        
        if "negative" in label.lower() or label == "LABEL_0":
            return -1.0, "negative"
        elif "positive" in label.lower() or label == "LABEL_1":
            return 1.0, "positive"
        else:
            return 0.0, "neutral"
    
    def _get_confidence(self, scores: List[Dict[str, float]]) -> Tuple[float, str]:
        """
        Get max confidence and corresponding label
        
        Args:
            scores: List of score dicts from model
        
        Returns:
            Tuple of (confidence, label)
        """
        max_score = max(scores, key=lambda x: x['score'])
        return max_score['score'], max_score['label']
    
    def analyze_single(self, text: str, use_shap: bool = False) -> SentimentResult:
        """
        Analyze single text
        
        Args:
            text: Input text
            use_shap: Whether to compute SHAP values
        
        Returns:
            SentimentResult object
        """
        # Check cache
        if self.cache is not None:
            cached_result = self.cache.get(text)
            if cached_result is not None:
                logger.debug(f"Cache hit for text: {text[:50]}...")
                return cached_result
        
        # Run inference
        import time
        start_time = time.time()
        
        try:
            # Get FinBERT predictions
            finbert_scores = self.finbert_pipeline(
                text,
                truncation=True,
                max_length=512
            )[0]
            
            finbert_confidence, finbert_label = self._get_confidence(finbert_scores)
            finbert_score, _ = self._label_to_score(finbert_label, {})
            
            # Initialize with FinBERT
            ensemble_scores = {
                "finbert": finbert_score
            }
            model_confidences = {
                "finbert": finbert_confidence
            }
            
            # Get DistilBERT predictions if available
            if self.distilbert_pipeline is not None:
                try:
                    distilbert_scores = self.distilbert_pipeline(
                        text,
                        truncation=True,
                        max_length=512
                    )[0]
                    
                    distilbert_confidence, distilbert_label = self._get_confidence(distilbert_scores)
                    distilbert_score, _ = self._label_to_score(distilbert_label, {})
                    
                    ensemble_scores["distilbert"] = distilbert_score
                    model_confidences["distilbert"] = distilbert_confidence
                    
                except Exception as e:
                    logger.warning(f"DistilBERT inference failed: {e}. Using FinBERT only.")
            
            # Compute ensemble prediction with confidence weighting
            weighted_score = sum(
                ensemble_scores[model] * self.weights[model]
                for model in ensemble_scores
            )
            
            # Compute ensemble confidence (average of individual confidences)
            ensemble_confidence = np.mean(list(model_confidences.values()))
            
            # Determine label
            if weighted_score > 0.3:
                label = "positive"
            elif weighted_score < -0.3:
                label = "negative"
            else:
                label = "neutral"
            
            # Check for model disagreement
            if len(ensemble_scores) > 1:
                scores_list = list(ensemble_scores.values())
                if np.std(scores_list) > 0.5:
                    self.disagreement_count += 1
                    logger.debug(f"Model disagreement detected: {ensemble_scores}")
            
            # Inference time
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            self.total_predictions += 1
            
            # Create result
            result = SentimentResult(
                text=text,
                sentiment_score=float(weighted_score),
                confidence=float(ensemble_confidence),
                label=label,
                individual_scores=ensemble_scores,
                model_confidences=model_confidences,
                timestamp=datetime.now(),
                metadata={
                    "inference_time_ms": inference_time * 1000,
                    "model_count": len(ensemble_scores),
                    "disagreement": len(ensemble_scores) > 1 and np.std(list(ensemble_scores.values())) > 0.5
                }
            )
            
            # Cache result
            if self.cache is not None:
                self.cache.put(text, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            raise
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        Analyze batch of texts
        
        Args:
            texts: List of input texts
        
        Returns:
            List of SentimentResult objects
        """
        results = []
        
        for text in texts:
            try:
                result = self.analyze_single(text)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing text in batch: {e}")
                # Return error result
                results.append(SentimentResult(
                    text=text,
                    sentiment_score=0.0,
                    confidence=0.0,
                    label="error",
                    individual_scores={},
                    model_confidences={},
                    timestamp=datetime.now(),
                    metadata={"error": str(e)}
                ))
        
        return results
    
    async def analyze_batch_async(self, texts: List[str]) -> List[SentimentResult]:
        """
        Analyze batch of texts asynchronously
        
        Args:
            texts: List of input texts
        
        Returns:
            List of SentimentResult objects
        """
        loop = asyncio.get_event_loop()
        
        tasks = [
            loop.run_in_executor(None, self.analyze_single, text)
            for text in texts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in async analysis: {result}")
                final_results.append(SentimentResult(
                    text=texts[i],
                    sentiment_score=0.0,
                    confidence=0.0,
                    label="error",
                    individual_scores={},
                    model_confidences={},
                    timestamp=datetime.now(),
                    metadata={"error": str(result)}
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def filter_by_confidence(
        self,
        results: List[SentimentResult],
        threshold: Optional[float] = None
    ) -> List[SentimentResult]:
        """
        Filter results by confidence threshold
        
        Args:
            results: List of results
            threshold: Confidence threshold (uses self.confidence_threshold if None)
        
        Returns:
            Filtered results
        """
        if threshold is None:
            threshold = self.confidence_threshold
        
        filtered = [r for r in results if r.confidence >= threshold]
        logger.info(f"Filtered {len(results)} results by confidence {threshold}: {len(filtered)} passed")
        
        return filtered
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics
        
        Returns:
            Statistics dictionary
        """
        inference_times = list(self.inference_times)
        
        return {
            "total_predictions": self.total_predictions,
            "disagreement_count": self.disagreement_count,
            "disagreement_rate": (
                self.disagreement_count / max(self.total_predictions, 1) * 100
            ),
            "avg_inference_time_ms": (
                np.mean(inference_times) * 1000 if inference_times else 0
            ),
            "max_inference_time_ms": (
                np.max(inference_times) * 1000 if inference_times else 0
            ),
            "min_inference_time_ms": (
                np.min(inference_times) * 1000 if inference_times else 0
            ),
            "cache_stats": self.cache.stats() if self.cache else None,
            "model_weights": self.weights
        }
    
    def to_json(self, result: SentimentResult) -> str:
        """
        Convert result to JSON
        
        Args:
            result: SentimentResult object
        
        Returns:
            JSON string
        """
        return json.dumps(result.to_dict(), indent=2, default=str)


def create_ensemble(
    cache_enabled: bool = True,
    device: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None
) -> SentimentEnsemble:
    """
    Factory function to create sentiment ensemble
    
    Args:
        cache_enabled: Whether to enable caching
        device: Device to use
        weights: Model weights
    
    Returns:
        SentimentEnsemble instance
    """
    return SentimentEnsemble(
        cache_enabled=cache_enabled,
        device=device,
        weights=weights
    )


# Example usage
if __name__ == "__main__":
    # Create ensemble
    ensemble = create_ensemble()
    
    # Test texts
    test_texts = [
        "Apple stock price surged 15% today due to strong earnings report.",
        "Tesla faces regulatory challenges and potential fines.",
        "Microsoft announces new AI partnership with OpenAI.",
        "Market crashes following unexpected interest rate hike.",
        "Netflix subscribers exceed expectations this quarter."
    ]
    
    # Analyze texts
    logger.info("Analyzing test texts...")
    results = ensemble.analyze_batch(test_texts)
    
    # Print results
    for result in results:
        logger.info(
            f"Text: {result.text[:60]}...\n"
            f"  Score: {result.sentiment_score:.3f}\n"
            f"  Confidence: {result.confidence:.3f}\n"
            f"  Label: {result.label}\n"
            f"  Models: {result.individual_scores}"
        )
    
    # Print statistics
    stats = ensemble.get_statistics()
    logger.info(f"\nStatistics: {json.dumps(stats, indent=2)}")
