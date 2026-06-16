import numpy as np
import pandas as pd
from typing import Dict, Any, List, Union, Optional


class AttentionInterpreter:
    """
    Translates raw attention weights and feature sequences into human-readable,
    event-annotated attention distributions for traders.
    """
    def __init__(self, feature_columns: List[str]):
        self.feature_columns = feature_columns
        
    def _detect_events(self, step_features: np.ndarray, prev_features: Optional[np.ndarray]) -> str:
        """
        Analyzes feature levels and shifts to characterize the time step.
        """
        # Feature columns:
        # [sentiment_score, close, volume, RSI, MACD, Bollinger_Band, google_trends, reddit_hype]
        sentiment = step_features[0]
        price = step_features[1]
        volume = step_features[2]
        rsi = step_features[3]
        google = step_features[6]
        reddit = step_features[7]
        
        events = []
        
        # 1. Price shift
        if prev_features is not None:
            prev_price = prev_features[1]
            price_change = (price - prev_price) / (prev_price + 1e-8)
            if price_change > 0.015:
                events.append("Price surge")
            elif price_change < -0.015:
                events.append("Price dip")
                
        # 2. RSI level
        if rsi > 70:
            events.append("Overbought level")
        elif rsi < 30:
            events.append("Oversold level")
            
        # 3. Volume
        if prev_features is not None:
            prev_volume = prev_features[2]
            if volume > prev_volume * 1.8:
                events.append("Volume spike")
                
        # 4. Sentiment and hype
        if sentiment > 0.4:
            if reddit > 0.6:
                events.append("Reddit hype storm")
            else:
                events.append("Strong bullish sentiment")
        elif sentiment < -0.4:
            events.append("Strong bearish sentiment")
            
        if google > 75:
            events.append("Google search surge")
            
        if not events:
            return "Stable trading baseline"
            
        return " - ".join(events)

    def interpret(
        self,
        attention_weights: np.ndarray,
        timestamps: List[Union[str, pd.Timestamp]],
        features: np.ndarray,
        query_time: str
    ) -> Dict[str, Any]:
        """
        Compiles attention weights, timestamps, and features into a structured analysis.
        
        Args:
            attention_weights: 1D array of attention weights of length seq_len.
            timestamps: List of timestamps corresponding to each step.
            features: 2D feature matrix of shape (seq_len, 8).
            query_time: Description of the current prediction time.
            
        Returns:
            Dict: JSON-compatible attention explanation dictionary.
        """
        assert len(attention_weights) == len(timestamps) == len(features), \
            f"Mismatched lengths: weights ({len(attention_weights)}), times ({len(timestamps)}), features ({len(features)})"
            
        distribution = []
        for i in range(len(attention_weights)):
            weight = float(attention_weights[i])
            t = timestamps[i]
            time_str = t.strftime("%I:%M %p") if hasattr(t, "strftime") else str(t)
            
            step_feats = features[i]
            prev_feats = features[i-1] if i > 0 else None
            
            description = self._detect_events(step_feats, prev_feats)
            
            distribution.append({
                "time": time_str,
                "weight": round(weight, 4),
                "description": description
            })
            
        # Sort by weight descending for highlighting key moments
        sorted_highlights = sorted(distribution, key=lambda x: x["weight"], reverse=True)
        
        return {
            "query_time": f"{query_time} (predicting next 4h)",
            "attention_distribution": distribution,
            "top_attended_events": sorted_highlights[:5]
        }

# clean architecture alignment
