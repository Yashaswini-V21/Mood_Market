import unittest
import os
import sys
import torch
import numpy as np
import pandas as pd

# Adjust path to import from parent folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import Informer, InformerConfig
from attention_extractor import AttentionExtractor
from attention_interpreter import AttentionInterpreter


class TestAttentionExplainability(unittest.TestCase):
    def setUp(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Mini configuration for testing
        self.config = InformerConfig(
            seq_len=16,
            pred_len=1,
            enc_in=8,
            dec_in=8,
            c_out=1,
            d_model=32,
            n_heads=2,
            n_encoder_layers=1,
            n_decoder_layers=1,
            d_ff=64,
            dropout=0.05,
            factor=2,
            device=self.device
        )
        self.model = Informer(self.config)
        self.extractor = AttentionExtractor(self.model)
        self.interpreter = AttentionInterpreter(
            feature_columns=[
                "sentiment_score", "close", "volume", "RSI", "MACD", 
                "Bollinger_Band", "google_trends", "reddit_hype"
            ]
        )

    def test_attention_extraction_and_pooling(self):
        """Test extraction shapes, layer/head pooling, and 1D importance mapping."""
        # Setup dummy batch of inputs
        batch_size = 2
        enc_in = torch.randn(batch_size, self.config.seq_len, self.config.enc_in).to(self.device)
        dec_in = torch.randn(batch_size, self.config.pred_len, self.config.dec_in).to(self.device)
        
        # Forward pass
        _, _, attn_weights = self.model(enc_in, dec_in)
        
        # Extract 2D matrix
        matrix = self.extractor.extract_encoder_attention(
            attn_weights,
            batch_idx=0,
            layer_aggregation="mean",
            head_aggregation="mean"
        )
        
        self.assertEqual(matrix.shape, (self.config.seq_len, self.config.seq_len))
        
        # Aggregate 1D step importance
        importance_last = self.extractor.get_step_importance(matrix, method="last_step")
        importance_mean = self.extractor.get_step_importance(matrix, method="mean_importance")
        
        self.assertEqual(len(importance_last), self.config.seq_len)
        self.assertEqual(len(importance_mean), self.config.seq_len)
        
        # Sum of normalized weights should be approx 1.0
        self.assertAlmostEqual(float(np.sum(importance_last)), 1.0, places=4)
        self.assertAlmostEqual(float(np.sum(importance_mean)), 1.0, places=4)

    def test_attention_interpreter_output(self):
        """Test interpreter maps to timestamps and creates correct JSON structure."""
        seq_len = 16
        dummy_weights = np.ones(seq_len) / seq_len
        
        timestamps = pd.date_range(start="2026-06-11 12:00:00", periods=seq_len, freq="15min")
        
        # Setup dummy features with some spikes
        features = np.zeros((seq_len, 8))
        features[:, 1] = 100.0  # close price baseline
        features[:, 2] = 1000.0  # volume baseline
        
        # Trigger price surge at index 5
        features[5, 1] = 120.0
        
        # Trigger volume spike at index 10
        features[10, 2] = 2500.0
        
        # Trigger sentiment spike at index 12
        features[12, 0] = 0.8  # sentiment score
        features[12, 7] = 0.9  # reddit hype
        
        result = self.interpreter.interpret(
            attention_weights=dummy_weights,
            timestamps=list(timestamps),
            features=features,
            query_time="3:45 PM"
        )
        
        # Check output structure
        self.assertIn("query_time", result)
        self.assertIn("attention_distribution", result)
        self.assertIn("top_attended_events", result)
        
        self.assertEqual(len(result["attention_distribution"]), seq_len)
        
        # Check dynamic event description generation
        # Event at index 5 is price surge
        self.assertIn("Price surge", result["attention_distribution"][5]["description"])
        
        # Event at index 10 is volume spike
        self.assertIn("Volume spike", result["attention_distribution"][10]["description"])
        
        # Event at index 12 is Reddit hype storm
        self.assertIn("Reddit hype storm", result["attention_distribution"][12]["description"])


if __name__ == "__main__":
    unittest.main()
