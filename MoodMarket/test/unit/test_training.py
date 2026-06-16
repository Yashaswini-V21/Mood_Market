import unittest
import os
import sys
import shutil
import tempfile
import torch
import numpy as np
import pandas as pd
import yaml

# Adjust path to import from parent folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import FinancialDataset, preprocess_data, generate_synthetic_3y_data, create_walk_forward_dataloaders
from model import Informer, InformerConfig
from trainer import Trainer, EarlyStopping
from train import load_config, train_single_run


class TestTrainingPipeline(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for checkpoints
        self.test_dir = tempfile.mkdtemp()
        
        # Simple config for testing
        self.config = {
            "training": {
                "batch_size": 4,
                "epochs": 2,
                "learning_rate": 1e-4,
                "weight_decay": 1e-5,
                "grad_clip": 1.0,
                "patience": 2,
                "accumulation_steps": 1,
                "scheduler_T0": 5,
                "scheduler_Tmult": 2,
                "seed": 42
            },
            "data": {
                "seq_len": 16,
                "pred_len": 1,
                "train_ratio": 0.6,
                "val_ratio": 0.2,
                "test_ratio": 0.2,
                "csv_path": ""
            },
            "model": {
                "enc_in": 8,
                "dec_in": 8,
                "c_out": 1,
                "d_model": 32,
                "n_heads": 2,
                "n_encoder_layers": 1,
                "n_decoder_layers": 1,
                "d_ff": 64,
                "dropout": 0.05,
                "factor": 2
            }
        }
        
        self.config_path = os.path.join(self.test_dir, "test_config.yaml")
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f)
            
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_synthetic_data_generation_and_preprocessing(self):
        """Test synthetic data generation is valid and preprocess works correctly."""
        df = generate_synthetic_3y_data(seed=42)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 100)
        
        # Test required columns
        required_cols = [
            "sentiment_score", "close", "volume", "RSI", "MACD", 
            "Bollinger_Band", "google_trends", "reddit_hype"
        ]
        for col in required_cols:
            self.assertIn(col, df.columns)
            
        data, info = preprocess_data(df)
        self.assertEqual(data.shape[1], 8)
        self.assertIn("feature_columns", info)

    def test_data_loaders(self):
        """Test chronological walk-forward validation splitting and shapes."""
        df = generate_synthetic_3y_data(seed=42)
        data, _ = preprocess_data(df)
        
        # Split ratios sum to 1.0
        train_loader, val_loader, test_loader, scaler = create_walk_forward_dataloaders(
            data=data,
            seq_len=16,
            pred_len=1,
            train_ratio=0.6,
            val_ratio=0.2,
            batch_size=4
        )
        
        # Check first batch shape
        for enc_in, dec_in, target in train_loader:
            self.assertEqual(enc_in.shape, (4, 16, 8))
            self.assertEqual(dec_in.shape, (4, 1, 8))
            self.assertEqual(target.shape, (4, 1))
            break
            
        self.assertIn("means", scaler)
        self.assertIn("stds", scaler)

    def test_trainer_and_checkpoints(self):
        """Test model training iteration, validation, and checkpoint load/save."""
        df = generate_synthetic_3y_data(seed=42)
        # Slicing data for quick testing
        data, _ = preprocess_data(df[:500])
        
        train_loader, val_loader, test_loader, _ = create_walk_forward_dataloaders(
            data=data,
            seq_len=16,
            pred_len=1,
            train_ratio=0.6,
            val_ratio=0.2,
            batch_size=4
        )
        
        model_cfg = InformerConfig(
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
        
        model = Informer(model_cfg)
        
        trainer = Trainer(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            test_loader=test_loader,
            config=self.config["training"],
            device=self.device
        )
        
        # Run 1 epoch
        train_loss = trainer.train_epoch(0)
        self.assertIsInstance(train_loss, float)
        
        # Run validation
        val_loss, val_acc = trainer.validate()
        self.assertIsInstance(val_loss, float)
        self.assertGreaterEqual(val_acc, 0.0)
        self.assertLessEqual(val_acc, 1.0)
        
        # Test checkpoint saving and restoring
        checkpoint_path = os.path.join(self.test_dir, "best_model.pt")
        trainer.save_checkpoint(checkpoint_path, 1, val_acc)
        self.assertTrue(os.path.exists(checkpoint_path))
        
        # Load and verify config and state
        loaded_epoch = trainer.load_checkpoint(checkpoint_path)
        self.assertEqual(loaded_epoch, 1)

    def test_early_stopping(self):
        """Test EarlyStopping helper class logic."""
        es = EarlyStopping(patience=2)
        # Stop flag should be False initially
        self.assertFalse(es(0.5))
        # No improvement -> counter increments
        self.assertFalse(es(0.6))
        # Counter reaches patience -> stop flag becomes True
        self.assertTrue(es(0.7))


if __name__ == "__main__":
    unittest.main()

# clean architecture alignment
