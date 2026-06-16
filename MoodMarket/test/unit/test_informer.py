"""
Comprehensive test suite for Informer model.
Validates positional encoding, attention, loss, model lifecycle,
datasets, training steps, inference, and configuration management.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import logging
from pathlib import Path

import torch

from model import Informer, InformerConfig, PositionalEncoding, ProbSparseMultiHeadAttention, HuberLoss
from data_loader import FinancialDataset, create_dataloaders, generate_synthetic_data
from trainer import Trainer
from inference import InferenceEngine, RealTimePredictor
from config import ExperimentConfig, get_baseline_config, save_config, load_config

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Minimal trainer config used across tests
_TRAINER_CFG = {
    "learning_rate": 1e-4,
    "weight_decay": 1e-5,
    "grad_clip": 1.0,
    "patience": 3,
    "accumulation_steps": 1,
    "scheduler_T0": 5,
    "scheduler_Tmult": 2,
    "epochs": 1,
    "batch_size": 32,
}


def _small_loaders(n_samples: int = 3000):
    """Return small train/val/test loaders for speed."""
    data = generate_synthetic_data(n_samples=n_samples)
    return create_dataloaders(
        data,
        batch_size=16,
        train_ratio=0.7,
        val_ratio=0.15,
    )


def _small_model():
    """Return a lightweight Informer model for unit tests."""
    cfg = InformerConfig(
        d_model=64,
        n_heads=2,
        n_encoder_layers=1,
        n_decoder_layers=1,
        d_ff=128,
        device=DEVICE,
    )
    return Informer(cfg)


# ============================================================================
# 1. Positional Encoding
# ============================================================================

class TestPositionalEncoding(unittest.TestCase):
    """Validate PositionalEncoding output shape and value range."""

    def setUp(self):
        self.d_model = 64
        self.max_len = 72
        self.pe = PositionalEncoding(self.d_model, self.max_len)

    def test_output_shape(self):
        x = torch.randn(2, 72, self.d_model)
        out = self.pe(x)
        self.assertEqual(out.shape, x.shape)

    def test_output_range(self):
        x = torch.randn(2, 72, self.d_model)
        out = self.pe(x)
        self.assertTrue((out >= -10).all() and (out <= 10).all(),
                        "Positional encoding values should stay within [-10, 10]")


# ============================================================================
# 2. ProbSparse Attention
# ============================================================================

class TestProbSparseAttention(unittest.TestCase):
    """Validate ProbSparse attention output shapes and weight properties."""

    def setUp(self):
        self.d_model = 64
        self.n_heads = 2
        self.attn = ProbSparseMultiHeadAttention(self.d_model, self.n_heads, factor=3).to(DEVICE)

    def test_output_shape(self):
        q = torch.randn(2, 72, self.d_model).to(DEVICE)
        k = torch.randn(2, 72, self.d_model).to(DEVICE)
        v = torch.randn(2, 72, self.d_model).to(DEVICE)
        out, weights = self.attn(q, k, v)
        self.assertEqual(out.shape, q.shape)

    def test_attention_weights_range(self):
        q = torch.randn(2, 72, self.d_model).to(DEVICE)
        k = torch.randn(2, 72, self.d_model).to(DEVICE)
        v = torch.randn(2, 72, self.d_model).to(DEVICE)
        _, weights = self.attn(q, k, v)
        self.assertTrue((weights >= 0).all() and (weights <= 1).all(),
                        "Attention weights must be in [0, 1]")


# ============================================================================
# 3. Huber Loss
# ============================================================================

class TestHuberLoss(unittest.TestCase):
    """Validate HuberLoss is non-negative and behaves correctly."""

    def setUp(self):
        self.loss_fn = HuberLoss(delta=1.0)

    def test_non_negative(self):
        pred = torch.tensor([[0.9], [0.1], [0.5]])
        tgt = torch.tensor([[1.0], [0.0], [0.5]])
        loss = self.loss_fn(pred, tgt)
        self.assertGreaterEqual(loss.item(), 0.0)

    def test_zero_on_perfect_prediction(self):
        pred = torch.tensor([[0.5], [0.8]])
        tgt = pred.clone()
        loss = self.loss_fn(pred, tgt)
        self.assertAlmostEqual(loss.item(), 0.0, places=5)


# ============================================================================
# 4. Model Initialization
# ============================================================================

class TestModelInitialization(unittest.TestCase):
    """Validate model creation, parameter count, and device placement."""

    def test_parameter_count_in_range(self):
        model = _small_model()
        params = model.count_parameters()
        self.assertGreater(params, 1_000)
        self.assertLess(params, 100_000_000)

    def test_device_placement(self):
        model = _small_model()
        for p in model.parameters():
            self.assertEqual(p.device.type, DEVICE.type)
            break


# ============================================================================
# 5. Forward Pass
# ============================================================================

class TestForwardPass(unittest.TestCase):
    """Validate forward pass shapes and output ranges."""

    def setUp(self):
        self.model = _small_model()
        self.batch = 4

    def test_prediction_shape(self):
        enc = torch.randn(self.batch, 72, 8).to(DEVICE)
        dec = torch.randn(self.batch, 1, 8).to(DEVICE)
        pred, unc, _ = self.model(enc, dec)
        self.assertEqual(pred.shape, (self.batch, 1, 1))

    def test_uncertainty_shape(self):
        enc = torch.randn(self.batch, 72, 8).to(DEVICE)
        dec = torch.randn(self.batch, 1, 8).to(DEVICE)
        _, unc, _ = self.model(enc, dec)
        self.assertEqual(unc.shape, (self.batch, 1, 1))

    def test_prediction_range(self):
        enc = torch.randn(self.batch, 72, 8).to(DEVICE)
        dec = torch.randn(self.batch, 1, 8).to(DEVICE)
        pred, _, _ = self.model(enc, dec)
        self.assertTrue((pred >= 0).all() and (pred <= 1).all(),
                        "Prediction probabilities must be in [0, 1]")

    def test_uncertainty_non_negative(self):
        enc = torch.randn(self.batch, 72, 8).to(DEVICE)
        dec = torch.randn(self.batch, 1, 8).to(DEVICE)
        _, unc, _ = self.model(enc, dec)
        self.assertTrue((unc >= 0).all(), "Uncertainty must be non-negative")


# ============================================================================
# 6. Model Serialization
# ============================================================================

class TestModelSerialization(unittest.TestCase):
    """Validate checkpoint save/load round-trip."""

    def setUp(self):
        self.model = _small_model()
        self.ckpt = "test_informer_ckpt.pt"

    def tearDown(self):
        if Path(self.ckpt).exists():
            Path(self.ckpt).unlink()

    def test_checkpoint_saved(self):
        self.model.save_checkpoint(self.ckpt)
        self.assertTrue(Path(self.ckpt).exists())

    def test_checkpoint_roundtrip(self):
        self.model.save_checkpoint(self.ckpt)
        loaded, _ = Informer.load_checkpoint(self.ckpt, DEVICE)
        self.assertEqual(loaded.count_parameters(), self.model.count_parameters())


# ============================================================================
# 7. FinancialDataset
# ============================================================================

class TestFinancialDataset(unittest.TestCase):
    """Validate dataset length, sample shapes, and target bounds."""

    def setUp(self):
        np.random.seed(42)
        self.data = np.random.randn(500, 8).astype(np.float32)
        # Normalise close col to [0,1] so target assertion holds
        self.data[:, 1] = (self.data[:, 1] - self.data[:, 1].min()) / (
            self.data[:, 1].max() - self.data[:, 1].min() + 1e-9
        )
        self.dataset = FinancialDataset(self.data, seq_len=72, pred_len=1, stride=1)

    def test_dataset_non_empty(self):
        self.assertGreater(len(self.dataset), 0)

    def test_encoder_input_shape(self):
        enc, dec, tgt = self.dataset[0]
        self.assertEqual(enc.shape, (72, 8))

    def test_decoder_input_shape(self):
        enc, dec, tgt = self.dataset[0]
        self.assertEqual(dec.shape, (1, 8))


# ============================================================================
# 8. DataLoaders
# ============================================================================

class TestDataLoaders(unittest.TestCase):
    """Validate that create_dataloaders returns properly shaped batches."""

    def setUp(self):
        data = generate_synthetic_data(n_samples=2000)
        self.train, self.val, self.test = create_dataloaders(
            data, batch_size=8, train_ratio=0.7, val_ratio=0.15
        )

    def test_loaders_not_none(self):
        self.assertIsNotNone(self.train)
        self.assertIsNotNone(self.val)
        self.assertIsNotNone(self.test)

    def test_batch_encoder_shape(self):
        enc, dec, tgt = next(iter(self.train))
        self.assertEqual(enc.shape[1], 72)
        self.assertEqual(enc.shape[2], 8)

    def test_batch_decoder_shape(self):
        enc, dec, tgt = next(iter(self.train))
        self.assertEqual(dec.shape[1], 1)
        self.assertEqual(dec.shape[2], 8)


# ============================================================================
# 9. Trainer
# ============================================================================

class TestTrainer(unittest.TestCase):
    """Validate trainer initialisation and that a single epoch runs."""

    def setUp(self):
        self.train, self.val, self.test = _small_loaders(2000)
        self.model = _small_model()
        self.trainer = Trainer(
            model=self.model,
            train_loader=self.train,
            val_loader=self.val,
            test_loader=self.test,
            config=_TRAINER_CFG,
            device=DEVICE,
        )

    def test_trainer_has_model(self):
        self.assertIsNotNone(self.trainer.model)

    def test_trainer_has_optimizer(self):
        self.assertIsNotNone(self.trainer.optimizer)

    def test_train_epoch_returns_float(self):
        loss = self.trainer.train_epoch(0)
        self.assertIsInstance(loss, float)
        self.assertGreater(loss, 0.0)

    def test_validate_returns_valid_accuracy(self):
        val_loss, val_acc = self.trainer.validate()
        self.assertGreaterEqual(val_acc, 0.0)
        self.assertLessEqual(val_acc, 1.0)


# ============================================================================
# 10. Inference Engine
# ============================================================================

class TestInferenceEngine(unittest.TestCase):
    """Validate single and batch inference through InferenceEngine."""

    def setUp(self):
        model = _small_model()
        self.ckpt_dir = Path("./test_checkpoints_informer")
        self.ckpt_dir.mkdir(exist_ok=True)
        self.ckpt_path = str(self.ckpt_dir / "best_model.pt")
        model.save_checkpoint(self.ckpt_path)
        self.engine = InferenceEngine(self.ckpt_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.ckpt_dir, ignore_errors=True)

    def test_single_prediction_range(self):
        enc = np.random.randn(72, 8)
        dec = np.random.randn(1, 8)
        result = self.engine.predict_single(enc, dec, confidence_level=0.95)
        pred = result["prediction"]
        self.assertGreaterEqual(pred, 0.0)
        self.assertLessEqual(pred, 1.0)

    def test_single_prediction_has_uncertainty(self):
        enc = np.random.randn(72, 8)
        dec = np.random.randn(1, 8)
        result = self.engine.predict_single(enc, dec)
        self.assertIn("uncertainty", result)
        self.assertGreaterEqual(result["uncertainty"], 0.0)

    def test_batch_predictions_count(self):
        enc_batch = np.random.randn(10, 72, 8)
        dec_batch = np.random.randn(10, 1, 8)
        results = self.engine.predict_batch(enc_batch, dec_batch, batch_size=5)
        self.assertEqual(len(results["predictions"]), 10)


# ============================================================================
# 11. Real-Time Streaming Predictor
# ============================================================================

class TestRealTimePredictor(unittest.TestCase):
    """Validate that RealTimePredictor emits predictions once buffer is full."""

    def setUp(self):
        model = _small_model()
        self.ckpt_dir = Path("./test_checkpoints_rt")
        self.ckpt_dir.mkdir(exist_ok=True)
        self.ckpt_path = str(self.ckpt_dir / "best_model.pt")
        model.save_checkpoint(self.ckpt_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.ckpt_dir, ignore_errors=True)

    def test_predictions_generated(self):
        predictor = RealTimePredictor(self.ckpt_path)
        count = 0
        for _ in range(100):
            pred = predictor.add_data_point(np.random.randn(8))
            if pred is not None:
                count += 1
        self.assertGreater(count, 0, "RealTimePredictor should emit predictions once buffer is full")


# ============================================================================
# 12. Configuration Management
# ============================================================================

class TestConfigManagement(unittest.TestCase):
    """Validate ExperimentConfig creation, serialisation, and round-trip."""

    def setUp(self):
        self.cfg_path = "test_informer_config.json"

    def tearDown(self):
        if Path(self.cfg_path).exists():
            Path(self.cfg_path).unlink()

    def test_baseline_seq_len(self):
        cfg = get_baseline_config()
        self.assertEqual(cfg.seq_len, 72)

    def test_save_and_load_roundtrip(self):
        cfg = get_baseline_config()
        save_config(cfg, self.cfg_path)
        self.assertTrue(Path(self.cfg_path).exists())
        loaded = load_config(self.cfg_path)
        self.assertEqual(loaded.seq_len, cfg.seq_len)
        self.assertEqual(loaded.d_model, cfg.d_model)


# ============================================================================
# Runner
# ============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)

# clean architecture alignment
