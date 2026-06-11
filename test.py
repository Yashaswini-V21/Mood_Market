"""
Comprehensive test suite for Informer model
Validates all components and functionality
"""

import torch
import numpy as np
import logging
from pathlib import Path
from typing import Tuple, List

from model import Informer, InformerConfig, PositionalEncoding, ProbSparseMultiHeadAttention, HuberLoss
from train import FinancialDataset, create_dataloaders, generate_synthetic_data, Trainer
from inference import InferenceEngine, RealTimePredictor
from config import ExperimentConfig, get_baseline_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSuite:
    """Comprehensive test suite"""
    
    def __init__(self):
        """Initialize test suite"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tests_passed = 0
        self.tests_failed = 0
    
    def run_all_tests(self) -> None:
        """Run all tests"""
        logger.info("\n" + "="*70)
        logger.info("INFORMER MODEL - COMPREHENSIVE TEST SUITE")
        logger.info("="*70)
        
        # Component tests
        self.test_positional_encoding()
        self.test_probsparse_attention()
        self.test_huber_loss()
        self.test_model_initialization()
        self.test_forward_pass()
        self.test_model_serialization()
        
        # Data tests
        self.test_financial_dataset()
        self.test_dataloaders()
        
        # Training tests
        self.test_trainer_initialization()
        self.test_training_step()
        
        # Inference tests
        self.test_single_prediction()
        self.test_batch_prediction()
        self.test_streaming_prediction()
        
        # Configuration tests
        self.test_config_management()
        
        # Print summary
        self.print_summary()
    
    def assert_equal(self, actual, expected, message: str) -> None:
        """Assert equality with logging"""
        if isinstance(actual, torch.Tensor):
            actual = actual.item() if actual.numel() == 1 else actual
        
        if actual == expected:
            self.tests_passed += 1
            logger.info(f"✓ PASS: {message}")
        else:
            self.tests_failed += 1
            logger.error(f"✗ FAIL: {message}")
            logger.error(f"  Expected: {expected}, Got: {actual}")
    
    def assert_shape(self, tensor: torch.Tensor, expected_shape: Tuple, message: str) -> None:
        """Assert tensor shape"""
        if tensor.shape == expected_shape:
            self.tests_passed += 1
            logger.info(f"✓ PASS: {message}")
        else:
            self.tests_failed += 1
            logger.error(f"✗ FAIL: {message}")
            logger.error(f"  Expected shape: {expected_shape}, Got: {tensor.shape}")
    
    def assert_range(self, tensor: torch.Tensor, min_val: float, max_val: float, message: str) -> None:
        """Assert tensor values in range"""
        if (tensor >= min_val).all() and (tensor <= max_val).all():
            self.tests_passed += 1
            logger.info(f"✓ PASS: {message}")
        else:
            self.tests_failed += 1
            logger.error(f"✗ FAIL: {message}")
            logger.error(f"  Expected range: [{min_val}, {max_val}]")
            logger.error(f"  Got min: {tensor.min():.4f}, max: {tensor.max():.4f}")
    
    def test_positional_encoding(self) -> None:
        """Test positional encoding"""
        logger.info("\n--- Testing Positional Encoding ---")
        
        d_model = 512
        max_len = 72
        
        pos_enc = PositionalEncoding(d_model, max_len)
        
        # Create input
        x = torch.randn(2, 72, d_model)
        output = pos_enc(x)
        
        self.assert_shape(output, x.shape, "Positional encoding output shape")
        self.assert_range(output, -10, 10, "Positional encoding output range")
    
    def test_probsparse_attention(self) -> None:
        """Test ProbSparse attention mechanism"""
        logger.info("\n--- Testing ProbSparse Attention ---")
        
        d_model = 512
        n_heads = 8
        
        attn = ProbSparseMultiHeadAttention(d_model, n_heads, factor=5)
        attn.to(self.device)
        
        # Create inputs
        query = torch.randn(2, 72, d_model).to(self.device)
        key = torch.randn(2, 72, d_model).to(self.device)
        value = torch.randn(2, 72, d_model).to(self.device)
        
        output, attn_weights = attn(query, key, value)
        
        self.assert_shape(output, query.shape, "Attention output shape")
        self.assert_range(attn_weights, 0, 1, "Attention weights in [0, 1]")
    
    def test_huber_loss(self) -> None:
        """Test Huber loss"""
        logger.info("\n--- Testing Huber Loss ---")
        
        loss_fn = HuberLoss(delta=1.0)
        
        output = torch.tensor([[0.9], [0.1], [0.5]])
        target = torch.tensor([[1.0], [0.0], [0.5]])
        
        loss = loss_fn(output, target)
        
        self.assert_range(loss, 0, 1, "Huber loss in valid range")
    
    def test_model_initialization(self) -> None:
        """Test model initialization"""
        logger.info("\n--- Testing Model Initialization ---")
        
        config = InformerConfig(device=self.device)
        model = Informer(config)
        
        # Check parameter count
        params = model.count_parameters()
        self.assert_range(torch.tensor(params), 1e6, 1e8, "Parameter count in reasonable range")
        
        # Check device
        for param in model.parameters():
            self.assert_equal(param.device.type, self.device.type, "Model on correct device")
            break  # Check only first parameter
    
    def test_forward_pass(self) -> None:
        """Test forward pass"""
        logger.info("\n--- Testing Forward Pass ---")
        
        config = InformerConfig(device=self.device)
        model = Informer(config)
        
        batch_size = 4
        encoder_input = torch.randn(batch_size, 72, 8).to(self.device)
        decoder_input = torch.randn(batch_size, 1, 8).to(self.device)
        
        prediction, uncertainty, attn_weights = model(encoder_input, decoder_input)
        
        self.assert_shape(prediction, (batch_size, 1, 1), "Prediction shape")
        self.assert_shape(uncertainty, (batch_size, 1, 1), "Uncertainty shape")
        self.assert_range(prediction, 0, 1, "Prediction in [0, 1] (probability)")
        self.assert_range(uncertainty, 0, 10, "Uncertainty positive")
    
    def test_model_serialization(self) -> None:
        """Test model save/load"""
        logger.info("\n--- Testing Model Serialization ---")
        
        config = InformerConfig(device=self.device)
        model = Informer(config)
        
        # Save
        checkpoint_path = "./test_checkpoint.pt"
        model.save_checkpoint(checkpoint_path)
        self.assert_equal(Path(checkpoint_path).exists(), True, "Checkpoint saved")
        
        # Load
        loaded_model, _ = Informer.load_checkpoint(checkpoint_path, self.device)
        self.assert_equal(loaded_model.count_parameters(), model.count_parameters(), 
                         "Loaded model same size as original")
        
        # Clean up
        Path(checkpoint_path).unlink()
    
    def test_financial_dataset(self) -> None:
        """Test financial dataset"""
        logger.info("\n--- Testing Financial Dataset ---")
        
        data = np.random.randn(1000, 8)
        dataset = FinancialDataset(data, seq_len=72, pred_len=1, stride=1)
        
        self.assert_equal(len(dataset) > 0, True, "Dataset length > 0")
        
        sample = dataset[0]
        encoder_input, decoder_input, target = sample
        
        self.assert_shape(encoder_input, (72, 8), "Dataset encoder input shape")
        self.assert_shape(decoder_input, (1, 8), "Dataset decoder input shape")
        self.assert_range(target, 0, 1, "Dataset target in [0, 1]")
    
    def test_dataloaders(self) -> None:
        """Test dataloader creation"""
        logger.info("\n--- Testing DataLoaders ---")
        
        data = generate_synthetic_data(n_samples=10000)
        train_loader, val_loader, test_loader = create_dataloaders(
            data,
            batch_size=32,
            train_ratio=0.7,
            val_ratio=0.15
        )
        
        self.assert_equal(train_loader is not None, True, "Train loader created")
        self.assert_equal(val_loader is not None, True, "Val loader created")
        self.assert_equal(test_loader is not None, True, "Test loader created")
        
        # Check batch
        batch = next(iter(train_loader))
        encoder_input, decoder_input, target = batch
        
        self.assert_shape(encoder_input, (32, 72, 8), "Batch encoder input shape")
        self.assert_shape(decoder_input, (32, 1, 8), "Batch decoder input shape")
    
    def test_trainer_initialization(self) -> None:
        """Test trainer initialization"""
        logger.info("\n--- Testing Trainer Initialization ---")
        
        data = generate_synthetic_data(n_samples=5000)
        train_loader, val_loader, test_loader = create_dataloaders(
            data,
            batch_size=32,
            train_ratio=0.7,
            val_ratio=0.15
        )
        
        config = InformerConfig(device=self.device)
        model = Informer(config)
        
        trainer = Trainer(model, train_loader, val_loader, test_loader, self.device)
        
        self.assert_equal(trainer.model is not None, True, "Trainer model initialized")
        self.assert_equal(trainer.optimizer is not None, True, "Trainer optimizer initialized")
    
    def test_training_step(self) -> None:
        """Test single training step"""
        logger.info("\n--- Testing Training Step ---")
        
        data = generate_synthetic_data(n_samples=5000)
        train_loader, val_loader, test_loader = create_dataloaders(
            data,
            batch_size=32,
            train_ratio=0.7,
            val_ratio=0.15
        )
        
        config = InformerConfig(device=self.device)
        model = Informer(config)
        
        trainer = Trainer(model, train_loader, val_loader, test_loader, self.device)
        
        # Train one epoch
        loss = trainer.train_epoch()
        self.assert_range(torch.tensor(loss), 0, 10, "Training loss in valid range")
        
        # Validate
        val_loss, val_acc = trainer.validate()
        self.assert_range(torch.tensor(val_acc), 0, 1, "Validation accuracy in [0, 1]")
    
    def test_single_prediction(self) -> None:
        """Test single prediction"""
        logger.info("\n--- Testing Single Prediction ---")
        
        # Create and save model
        config = InformerConfig(device=self.device)
        model = Informer(config)
        checkpoint_dir = "./checkpoints"
        Path(checkpoint_dir).mkdir(exist_ok=True)
        model.save_checkpoint(f"{checkpoint_dir}/best_model.pt")
        
        # Load inference engine
        engine = InferenceEngine(f"{checkpoint_dir}/best_model.pt")
        
        # Make prediction
        encoder_input = np.random.randn(72, 8)
        decoder_input = np.random.randn(1, 8)
        
        result = engine.predict_single(encoder_input, decoder_input, confidence_level=0.95)
        
        self.assert_range(torch.tensor(result['prediction']), 0, 1, "Prediction in [0, 1]")
        self.assert_range(torch.tensor(result['uncertainty']), 0, 1, "Uncertainty in valid range")
    
    def test_batch_prediction(self) -> None:
        """Test batch prediction"""
        logger.info("\n--- Testing Batch Prediction ---")
        
        # Create and save model
        config = InformerConfig(device=self.device)
        model = Informer(config)
        checkpoint_dir = "./checkpoints"
        Path(checkpoint_dir).mkdir(exist_ok=True)
        model.save_checkpoint(f"{checkpoint_dir}/best_model.pt")
        
        # Load inference engine
        engine = InferenceEngine(f"{checkpoint_dir}/best_model.pt")
        
        # Make batch prediction
        encoder_batch = np.random.randn(10, 72, 8)
        decoder_batch = np.random.randn(10, 1, 8)
        
        results = engine.predict_batch(encoder_batch, decoder_batch, batch_size=5)
        
        self.assert_shape(torch.tensor(results['predictions']), (10, 1), "Batch predictions shape")
        self.assert_equal(len(results['predictions']) == 10, True, "Batch prediction count")
    
    def test_streaming_prediction(self) -> None:
        """Test real-time streaming"""
        logger.info("\n--- Testing Real-Time Streaming ---")
        
        # Create and save model
        config = InformerConfig(device=self.device)
        model = Informer(config)
        checkpoint_dir = "./checkpoints"
        Path(checkpoint_dir).mkdir(exist_ok=True)
        model.save_checkpoint(f"{checkpoint_dir}/best_model.pt")
        
        # Initialize predictor
        predictor = RealTimePredictor(f"{checkpoint_dir}/best_model.pt")
        
        # Stream data
        predictions_count = 0
        for i in range(100):
            new_data = np.random.randn(8)
            prediction = predictor.add_data_point(new_data)
            
            if prediction is not None:
                predictions_count += 1
        
        self.assert_equal(predictions_count > 0, True, "Streaming predictions generated")
    
    def test_config_management(self) -> None:
        """Test configuration management"""
        logger.info("\n--- Testing Configuration Management ---")
        
        from config import get_baseline_config, save_config, load_config
        
        # Create config
        config = get_baseline_config()
        self.assert_equal(config.seq_len == 72, True, "Baseline config has seq_len=72")
        
        # Save config
        config_path = "test_config.json"
        save_config(config, config_path)
        self.assert_equal(Path(config_path).exists(), True, "Config file saved")
        
        # Load config
        loaded_config = load_config(config_path)
        self.assert_equal(loaded_config.seq_len, config.seq_len, "Loaded config matches original")
        
        # Clean up
        Path(config_path).unlink()
    
    def print_summary(self) -> None:
        """Print test summary"""
        logger.info("\n" + "="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)
        
        total_tests = self.tests_passed + self.tests_failed
        pass_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {self.tests_passed} ✓")
        logger.info(f"Failed: {self.tests_failed} ✗")
        logger.info(f"Pass Rate: {pass_rate:.1f}%")
        
        if self.tests_failed == 0:
            logger.info("\n🎉 ALL TESTS PASSED! 🎉")
        else:
            logger.error(f"\n⚠️  {self.tests_failed} test(s) failed")
        
        logger.info("="*70 + "\n")


def run_tests():
    """Run test suite"""
    suite = TestSuite()
    suite.run_all_tests()
    
    return suite.tests_failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
