"""
SHAP-based Token Importance Analysis for Sentiment Predictions
Explains model predictions at token level with confidence intervals.
"""

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
import json

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP not available. Install with: pip install shap")

from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

logger = logging.getLogger(__name__)


@dataclass
class TokenImportance:
    """Token importance score with metadata"""
    token: str
    shap_value: float
    position: int
    importance_percentile: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'token': self.token,
            'shap_value': float(self.shap_value),
            'position': int(self.position),
            'importance_percentile': float(self.importance_percentile)
        }


@dataclass
class SHAPExplanation:
    """Complete SHAP explanation for a prediction"""
    text: str
    base_value: float
    prediction_value: float
    model_name: str
    token_importances: List[TokenImportance]
    top_positive_tokens: List[TokenImportance]
    top_negative_tokens: List[TokenImportance]
    confidence_interval: Tuple[float, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'text': self.text,
            'base_value': float(self.base_value),
            'prediction_value': float(self.prediction_value),
            'model_name': self.model_name,
            'token_importances': [t.to_dict() for t in self.token_importances],
            'top_positive_tokens': [t.to_dict() for t in self.top_positive_tokens],
            'top_negative_tokens': [t.to_dict() for t in self.top_negative_tokens],
            'confidence_interval': self.confidence_interval
        }


class TransformerExplainer:
    """SHAP explainer for transformer models"""
    
    def __init__(
        self,
        model_name: str,
        tokenizer_name: str,
        device: str = "cuda",
        top_k: int = 5
    ) -> None:
        """
        Initialize transformer explainer
        
        Args:
            model_name: Transformer model name
            tokenizer_name: Tokenizer name
            device: Device to use
            top_k: Number of top tokens to return
        """
        if not SHAP_AVAILABLE:
            raise ImportError("SHAP is required. Install with: pip install shap")
        
        self.model_name = model_name
        self.device = device
        self.top_k = top_k
        
        logger.info(f"Loading tokenizer and model for SHAP: {model_name}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        
        # Load model
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(device)
        self.model.eval()
        
        # Create pipeline
        self.pipeline = pipeline(
            "sentiment-analysis",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if device == "cuda" else -1
        )
        
        logger.info("✓ Explainer loaded successfully")
    
    def _predict_fn(self, texts: List[str]) -> np.ndarray:
        """
        Prediction function for SHAP
        
        Args:
            texts: List of texts
        
        Returns:
            Prediction scores array
        """
        predictions = []
        
        for text in texts:
            try:
                # Truncate text if needed
                text = text[:512]
                
                # Get prediction
                result = self.pipeline(text, truncation=True)
                
                # Extract positive class score
                scores = result[0]  # List of label scores
                
                # Find positive score
                positive_score = 0.5
                for score_dict in scores:
                    if 'positive' in score_dict['label'].lower() or score_dict['label'] == 'LABEL_1':
                        positive_score = score_dict['score']
                        break
                
                predictions.append(positive_score)
                
            except Exception as e:
                logger.warning(f"Error in prediction for SHAP: {e}")
                predictions.append(0.5)
        
        return np.array(predictions)
    
    def explain(self, text: str, use_background: bool = True) -> SHAPExplanation:
        """
        Explain model prediction using SHAP
        
        Args:
            text: Input text
            use_background: Whether to use background data
        
        Returns:
            SHAPExplanation object
        """
        try:
            logger.info(f"Generating SHAP explanation for text: {text[:60]}...")
            
            # Tokenize text
            tokens = self.tokenizer.tokenize(text)
            
            # Create SHAP explainer (using simple background)
            background = [""]  # Empty string as background
            
            explainer = shap.Explainer(self._predict_fn, background)
            
            # Get SHAP values
            shap_values = explainer([text])
            
            # Extract base value and prediction
            base_value = float(explainer.expected_value)
            prediction_value = float(shap_values.values[0].sum()) + base_value
            
            # Get token attributions
            token_importances = []
            
            if hasattr(shap_values, 'values'):
                token_values = shap_values.values[0]
            else:
                token_values = shap_values[0]
            
            for i, (token, value) in enumerate(zip(tokens, token_values)):
                token_importances.append(
                    TokenImportance(
                        token=token,
                        shap_value=float(value),
                        position=i,
                        importance_percentile=0.0  # Will compute later
                    )
                )
            
            # Compute percentiles
            all_values = np.array([t.shap_value for t in token_importances])
            for token_imp in token_importances:
                percentile = np.percentile(all_values, 
                    np.sum(all_values <= token_imp.shap_value) / len(all_values) * 100
                )
                token_imp.importance_percentile = percentile
            
            # Sort by SHAP value
            token_importances_sorted = sorted(
                token_importances,
                key=lambda x: abs(x.shap_value),
                reverse=True
            )
            
            # Get top positive and negative
            top_positive = [t for t in token_importances_sorted if t.shap_value > 0][:self.top_k]
            top_negative = [t for t in token_importances_sorted if t.shap_value < 0][:self.top_k]
            
            # Compute confidence interval (using bootstrap)
            ci_low, ci_high = self._compute_confidence_interval(text)
            
            explanation = SHAPExplanation(
                text=text,
                base_value=base_value,
                prediction_value=prediction_value,
                model_name=self.model_name,
                token_importances=token_importances,
                top_positive_tokens=top_positive,
                top_negative_tokens=top_negative,
                confidence_interval=(ci_low, ci_high)
            )
            
            logger.info(f"✓ SHAP explanation generated successfully")
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating SHAP explanation: {e}")
            raise
    
    def _compute_confidence_interval(
        self,
        text: str,
        n_bootstrap: int = 50,
        confidence_level: float = 0.95
    ) -> Tuple[float, float]:
        """
        Compute confidence interval using bootstrap resampling
        
        Args:
            text: Input text
            n_bootstrap: Number of bootstrap samples
            confidence_level: Confidence level
        
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        predictions = []
        
        # Add noise and resample
        tokens = self.tokenizer.tokenize(text)
        
        for _ in range(n_bootstrap):
            # Random dropout of tokens
            if len(tokens) > 2:
                n_keep = np.random.randint(len(tokens) // 2, len(tokens))
                indices = np.random.choice(len(tokens), n_keep, replace=False)
                resampled_tokens = [tokens[i] for i in sorted(indices)]
                resampled_text = self.tokenizer.convert_tokens_to_string(resampled_tokens)
            else:
                resampled_text = text
            
            pred = self._predict_fn([resampled_text])[0]
            predictions.append(pred)
        
        # Compute percentiles
        alpha = (1 - confidence_level) / 2
        lower = np.percentile(predictions, alpha * 100)
        upper = np.percentile(predictions, (1 - alpha) * 100)
        
        return float(lower), float(upper)
    
    def batch_explain(
        self,
        texts: List[str],
        progress_bar: bool = True
    ) -> List[SHAPExplanation]:
        """
        Explain batch of texts
        
        Args:
            texts: List of texts
            progress_bar: Whether to show progress
        
        Returns:
            List of explanations
        """
        explanations = []
        
        for i, text in enumerate(texts):
            if progress_bar and (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(texts)} texts")
            
            try:
                explanation = self.explain(text)
                explanations.append(explanation)
            except Exception as e:
                logger.error(f"Error explaining text {i}: {e}")
        
        return explanations
    
    def visualize_tokens(self, explanation: SHAPExplanation) -> Dict[str, Any]:
        """
        Create visualization data for token importances
        
        Args:
            explanation: SHAP explanation
        
        Returns:
            Visualization data structure
        """
        visualization_data = {
            "text": explanation.text,
            "model": explanation.model_name,
            "tokens": [
                {
                    "token": t.token,
                    "shap_value": t.shap_value,
                    "position": t.position,
                    "color": "green" if t.shap_value > 0 else "red",
                    "opacity": min(1.0, abs(t.shap_value))
                }
                for t in explanation.token_importances
            ],
            "top_positive": [t.to_dict() for t in explanation.top_positive_tokens],
            "top_negative": [t.to_dict() for t in explanation.top_negative_tokens],
            "prediction_value": explanation.prediction_value,
            "confidence_interval": explanation.confidence_interval
        }
        
        return visualization_data


class EnsembleExplainer:
    """SHAP explainer for ensemble models"""
    
    def __init__(
        self,
        models: Dict[str, str],
        tokenizers: Dict[str, str],
        device: str = "cuda"
    ) -> None:
        """
        Initialize ensemble explainer
        
        Args:
            models: Model names {name: model_id}
            tokenizers: Tokenizer names {name: tokenizer_id}
            device: Device to use
        """
        self.explainers = {}
        
        for model_name, model_id in models.items():
            try:
                tokenizer_id = tokenizers.get(model_name, model_id)
                explainer = TransformerExplainer(model_id, tokenizer_id, device)
                self.explainers[model_name] = explainer
            except Exception as e:
                logger.error(f"Failed to load explainer for {model_name}: {e}")
    
    def explain_ensemble(self, text: str) -> Dict[str, SHAPExplanation]:
        """
        Explain prediction from all models in ensemble
        
        Args:
            text: Input text
        
        Returns:
            Dictionary of explanations {model_name: explanation}
        """
        explanations = {}
        
        for model_name, explainer in self.explainers.items():
            try:
                explanation = explainer.explain(text)
                explanations[model_name] = explanation
            except Exception as e:
                logger.error(f"Error explaining with {model_name}: {e}")
        
        return explanations
    
    def compare_explanations(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        Compare explanations across ensemble models
        
        Args:
            text: Input text
        
        Returns:
            Comparison data
        """
        explanations = self.explain_ensemble(text)
        
        comparison = {
            "text": text,
            "explanations": {
                name: exp.to_dict() for name, exp in explanations.items()
            },
            "agreement": self._compute_agreement(explanations),
            "token_agreement": self._compute_token_agreement(explanations)
        }
        
        return comparison
    
    def _compute_agreement(
        self,
        explanations: Dict[str, SHAPExplanation]
    ) -> float:
        """
        Compute prediction agreement between models
        
        Args:
            explanations: Model explanations
        
        Returns:
            Agreement score (0-1)
        """
        if len(explanations) < 2:
            return 1.0
        
        predictions = np.array([exp.prediction_value for exp in explanations.values()])
        
        # Compute correlation
        if len(predictions) == 2:
            correlation = abs(np.corrcoef(predictions[0], predictions[1])[0, 1])
        else:
            correlation = np.corrcoef(predictions)[0, 1]
        
        return float(max(0, correlation))
    
    def _compute_token_agreement(
        self,
        explanations: Dict[str, SHAPExplanation]
    ) -> float:
        """
        Compute agreement on important tokens
        
        Args:
            explanations: Model explanations
        
        Returns:
            Agreement score (0-1)
        """
        if len(explanations) < 2:
            return 1.0
        
        # Get top tokens from each model
        top_tokens_sets = []
        for explanation in explanations.values():
            top_tokens = set()
            
            for token_imp in explanation.top_positive_tokens[:5]:
                top_tokens.add(token_imp.token)
            
            for token_imp in explanation.top_negative_tokens[:5]:
                top_tokens.add(token_imp.token)
            
            top_tokens_sets.append(top_tokens)
        
        # Compute intersection
        if not top_tokens_sets:
            return 0.0
        
        intersection = set.intersection(*top_tokens_sets)
        union = set.union(*top_tokens_sets)
        
        if not union:
            return 0.0
        
        return float(len(intersection) / len(union))


# Example usage
if __name__ == "__main__":
    if SHAP_AVAILABLE:
        # Create explainer
        explainer = TransformerExplainer(
            model_name="ProsusAI/finbert",
            tokenizer_name="ProsusAI/finbert"
        )
        
        # Test text
        test_text = "Apple stock price surged 15% today due to strong earnings."
        
        # Generate explanation
        explanation = explainer.explain(test_text)
        
        # Print results
        logger.info(f"Text: {explanation.text}")
        logger.info(f"Prediction: {explanation.prediction_value:.4f}")
        logger.info(f"Confidence Interval: {explanation.confidence_interval}")
        logger.info(f"\nTop Positive Tokens:")
        for token in explanation.top_positive_tokens:
            logger.info(f"  {token.token}: {token.shap_value:.4f}")
        
        logger.info(f"\nTop Negative Tokens:")
        for token in explanation.top_negative_tokens:
            logger.info(f"  {token.token}: {token.shap_value:.4f}")
        
        # Visualize
        viz = explainer.visualize_tokens(explanation)
        logger.info(f"\nVisualization: {json.dumps(viz, indent=2)}")
    else:
        logger.error("SHAP not available")
