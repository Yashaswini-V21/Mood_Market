import unittest
import pandas as pd
import numpy as np
import torch
import sys
import os

# Adjust path to import from parent folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import (
    FinancialDataset,
    preprocess_data,
    generate_synthetic_3y_data,
    create_walk_forward_dataloaders,
    create_dataloaders,
    generate_synthetic_data
)


class TestDataLoader(unittest.TestCase):
    """
    Unit tests for data loader functionality, preprocessing, normalizations, and Dataset configurations.
    """

    def test_generate_synthetic_data(self):
        """Test generate_synthetic_data generates expected numpy array dimensions"""
        data = generate_synthetic_data(n_samples=100)
        self.assertEqual(data.shape, (100, 8))
        self.assertIsInstance(data, np.ndarray)

    def test_generate_synthetic_3y_data(self):
        """Test generate_synthetic_3y_data creates expected columns and types"""
        df = generate_synthetic_3y_data(seed=42)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("close", df.columns)
        self.assertIn("volume", df.columns)
        self.assertIn("sentiment_score", df.columns)
        self.assertTrue(len(df) > 0)

    def test_preprocess_data(self):
        """Test data preprocessing cleans columns and prepares values correctly"""
        # Create small synthetic dataframe with a missing column to trigger default neutral values
        df = generate_synthetic_3y_data(seed=42).head(50)
        df_dropped = df.drop(columns=["Bollinger_Band"])
        
        data, params = preprocess_data(df_dropped)
        self.assertEqual(data.shape, (50, 8))
        self.assertIn("feature_columns", params)
        self.assertEqual(params["feature_columns"][-3], "Bollinger_Band")

    def test_financial_dataset_indexing(self):
        """Test FinancialDataset returns correct shapes for encoder/decoder/target slices"""
        data = generate_synthetic_data(n_samples=150)
        dataset = FinancialDataset(data, seq_len=72, pred_len=4)
        
        # Expected len: 150 - 72 - 4 + 1 = 75
        self.assertEqual(len(dataset), 75)
        
        enc, dec, target = dataset[0]
        self.assertEqual(enc.shape, (72, 8))
        # Decoder input length matches pred_len
        self.assertEqual(dec.shape, (4, 8))
        self.assertEqual(target.shape, (1,))
        self.assertIsInstance(enc, torch.Tensor)

    def test_create_walk_forward_dataloaders(self):
        """Test splitting and scaling configurations for dataloaders"""
        data = generate_synthetic_data(n_samples=500)
        train_loader, val_loader, test_loader, scaler_params = create_walk_forward_dataloaders(
            data, seq_len=10, pred_len=1, train_ratio=0.6, val_ratio=0.2, batch_size=16
        )
        
        self.assertIsNotNone(train_loader)
        self.assertIsNotNone(val_loader)
        self.assertIsNotNone(test_loader)
        self.assertIn("means", scaler_params)
        self.assertIn("ranges", scaler_params)
        
        # Verify compatibility wrappers alias
        t, v, te = create_dataloaders(data, seq_len=10, pred_len=1, train_ratio=0.6, val_ratio=0.2, batch_size=16)
        self.assertIsNotNone(t)
        self.assertIsNotNone(v)
        self.assertIsNotNone(te)


if __name__ == "__main__":
    unittest.main()
