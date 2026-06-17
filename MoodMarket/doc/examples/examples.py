"""
Example usage and integration guide for Informer financial forecasting model
Demonstrates all key components: training, inference, deployment, and benchmarking
"""

import os
import sys
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import numpy as np
from pathlib import Path
import logging

# Import components
from model import Informer, InformerConfig, HuberLoss
from trainer import Trainer
from data_loader import generate_synthetic_data, create_dataloaders
from inference import InferenceEngine, RealTimePredictor
from benchmark import ModelBenchmark, LSTMModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_1_basic_training():
    """Example 1: Basic model training"""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 1: Basic Model Training")
    logger.info("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Generate data
    logger.info("Generating synthetic data...")
    data = generate_synthetic_data(n_samples=50000)
    
    # Create dataloaders
    logger.info("Creating dataloaders...")
    train_loader, val_loader, test_loader = create_dataloaders(
        data,
        seq_len=72,
        pred_len=1,
        batch_size=32,
        train_ratio=0.7,
        val_ratio=0.15
    )
    
    # Initialize model
    logger.info("Initializing Informer model...")
    config = InformerConfig(
        seq_len=72,
        pred_len=1,
        enc_in=8,
        dec_in=8,
        c_out=1,
        d_model=512,
        n_heads=8,
        n_encoder_layers=2,
        n_decoder_layers=2,
        d_ff=2048,
        device=device
    )
    
    model = Informer(config)
    logger.info(f"Model parameters: {model.count_parameters():,}")
    
    # Train
    logger.info("Training model...")
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        device=device,
        learning_rate=1e-4
    )
    
    history = trainer.train(epochs=3)  # Short training for demo
    
    # Test
    test_loss, test_acc, metrics = trainer.test()
    logger.info(f"✓ Test Accuracy: {test_acc:.4f}")
    logger.info(f"✓ Test F1-Score: {metrics['f1_score']:.4f}")


def example_2_single_prediction():
    """Example 2: Single prediction with confidence intervals"""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 2: Single Prediction with Confidence Intervals")
    logger.info("="*60)
    
    # First, create a dummy model checkpoint (skip if already trained)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    config = InformerConfig(device=device)
    model = Informer(config)
    checkpoint_dir = './checkpoints'
    Path(checkpoint_dir).mkdir(exist_ok=True)
    model.save_checkpoint(f'{checkpoint_dir}/best_model.pt')
    
    # Load inference engine
    logger.info("Loading inference engine...")
    engine = InferenceEngine(f'{checkpoint_dir}/best_model.pt')
    
    # Generate sample data
    encoder_input = np.random.randn(72, 8)
    decoder_input = np.random.randn(1, 8)
    
    # Make prediction
    logger.info("Making prediction...")
    result = engine.predict_single(
        encoder_input,
        decoder_input,
        confidence_level=0.95
    )
    
    logger.info(f"Prediction (UP probability): {result['prediction']:.4f}")
    logger.info(f"Uncertainty: {result['uncertainty']:.6f}")
    logger.info(f"95% Confidence Interval: [{result['lower_bound']:.4f}, {result['upper_bound']:.4f}]")


def example_3_batch_prediction():
    """Example 3: Batch prediction"""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 3: Batch Prediction")
    logger.info("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Create model checkpoint
    config = InformerConfig(device=device)
    model = Informer(config)
    checkpoint_dir = './checkpoints'
    Path(checkpoint_dir).mkdir(exist_ok=True)
    model.save_checkpoint(f'{checkpoint_dir}/best_model.pt')
    
    # Load inference engine
    engine = InferenceEngine(f'{checkpoint_dir}/best_model.pt')
    
    # Generate batch data
    n_samples = 100
    encoder_batch = np.random.randn(n_samples, 72, 8)
    decoder_batch = np.random.randn(n_samples, 1, 8)
    
    logger.info(f"Running batch inference on {n_samples} samples...")
    results = engine.predict_batch(
        encoder_batch,
        decoder_batch,
        confidence_level=0.95,
        batch_size=32
    )
    
    logger.info(f"Predictions shape: {results['predictions'].shape}")
    logger.info(f"Mean prediction: {results['predictions'].mean():.4f}")
    logger.info(f"Mean uncertainty: {results['uncertainties'].mean():.6f}")
    logger.info(f"✓ Batch prediction completed")


def example_4_real_time_streaming():
    """Example 4: Real-time streaming predictions"""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 4: Real-Time Streaming Predictions")
    logger.info("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Create model checkpoint
    config = InformerConfig(device=device)
    model = Informer(config)
    checkpoint_dir = './checkpoints'
    Path(checkpoint_dir).mkdir(exist_ok=True)
    model.save_checkpoint(f'{checkpoint_dir}/best_model.pt')
    
    # Initialize real-time predictor
    logger.info("Initializing real-time predictor...")
    predictor = RealTimePredictor(f'{checkpoint_dir}/best_model.pt')
    
    # Simulate streaming data
    logger.info("Simulating data stream...")
    predictions_made = 0
    
    for t in range(150):
        # Generate new data point (8 features)
        new_data = np.random.randn(8)
        
        # Add to buffer and get prediction if ready
        prediction = predictor.add_data_point(new_data)
        
        if prediction is not None:
            predictions_made += 1
            
            if predictions_made % 10 == 0:
                logger.info(
                    f"Streaming prediction #{predictions_made} at step {t}: "
                    f"P(UP)={prediction['prediction']:.4f}, "
                    f"CI=[{prediction['lower_bound']:.4f}, {prediction['upper_bound']:.4f}]"
                )
    
    logger.info(f"✓ Generated {predictions_made} streaming predictions")


def example_5_model_deployment():
    """Example 5: Model optimization and deployment"""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 5: Model Deployment & Optimization")
    logger.info("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Create model checkpoint
    config = InformerConfig(device=device)
    model = Informer(config)
    checkpoint_dir = './checkpoints'
    Path(checkpoint_dir).mkdir(exist_ok=True)
    model.save_checkpoint(f'{checkpoint_dir}/best_model.pt')
    
    # Load and optimize
    logger.info("Loading and optimizing model...")
    engine = InferenceEngine(f'{checkpoint_dir}/best_model.pt')
    
    # Get original size
    original_size = Path(f'{checkpoint_dir}/best_model.pt').stat().st_size / (1024**2)
    logger.info(f"Original model size: {original_size:.2f} MB")
    
    # Optimize for deployment
    logger.info("Optimizing model for edge deployment...")
    engine.optimize_for_deployment(
        output_path='model_optimized.pt',
        quantize=True,
        prune=False
    )
    
    optimized_size = Path('model_optimized.pt').stat().st_size / (1024**2)
    logger.info(f"Optimized model size: {optimized_size:.2f} MB")
    logger.info(f"Size reduction: {(1 - optimized_size/original_size)*100:.1f}%")


def example_6_attention_visualization():
    """Example 6: Extract attention weights for explainability"""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 6: Attention Visualization (Explainability)")
    logger.info("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Create model checkpoint
    config = InformerConfig(device=device)
    model = Informer(config)
    checkpoint_dir = './checkpoints'
    Path(checkpoint_dir).mkdir(exist_ok=True)
    model.save_checkpoint(f'{checkpoint_dir}/best_model.pt')
    
    # Load inference engine
    engine = InferenceEngine(f'{checkpoint_dir}/best_model.pt')
    
    # Generate sample data
    encoder_input = np.random.randn(72, 8)
    decoder_input = np.random.randn(1, 8)
    
    # Extract attention weights
    logger.info("Extracting attention weights...")
    attn_viz = engine.get_attention_visualization(
        encoder_input,
        decoder_input,
        layer_idx=0,
        head_idx=0
    )
    
    logger.info("Attention patterns:")
    if attn_viz['encoder_attention'] is not None:
        logger.info(f"  Encoder attention shape: {attn_viz['encoder_attention'].shape}")
    if attn_viz['decoder_self_attention'] is not None:
        logger.info(f"  Decoder self-attention shape: {attn_viz['decoder_self_attention'].shape}")
    if attn_viz['decoder_cross_attention'] is not None:
        logger.info(f"  Decoder cross-attention shape: {attn_viz['decoder_cross_attention'].shape}")
    
    logger.info("✓ These attention weights can be visualized as heatmaps for interpretation")


def example_7_uncertainty_calibration():
    """Example 7: Uncertainty calibration"""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 7: Uncertainty Calibration")
    logger.info("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Create model checkpoint
    config = InformerConfig(device=device)
    model = Informer(config)
    checkpoint_dir = './checkpoints'
    Path(checkpoint_dir).mkdir(exist_ok=True)
    model.save_checkpoint(f'{checkpoint_dir}/best_model.pt')
    
    # Load inference engine
    engine = InferenceEngine(f'{checkpoint_dir}/best_model.pt')
    
    # Generate validation data
    n_val_samples = 500
    encoder_inputs = np.random.randn(n_val_samples, 72, 8)
    decoder_inputs = np.random.randn(n_val_samples, 1, 8)
    targets = np.random.randint(0, 2, (n_val_samples, 1))
    
    # Calibrate uncertainty
    logger.info("Calibrating uncertainty estimates...")
    calibration_metrics = engine.calibrate_uncertainty(
        encoder_inputs,
        decoder_inputs,
        targets,
        num_bins=10
    )
    
    logger.info(f"Calibration metric: {calibration_metrics['calibration_metric']:.4f}")
    logger.info(f"Mean accuracy per bin: {calibration_metrics['accuracies_per_bin'].mean():.4f}")
    logger.info("✓ Uncertainty calibration completed")


def example_8_model_information():
    """Example 8: Model information and configuration"""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 8: Model Information")
    logger.info("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    config = InformerConfig(device=device)
    model = Informer(config)
    
    logger.info("Model Configuration:")
    logger.info(f"  Input sequence length: {config.seq_len}")
    logger.info(f"  Prediction length: {config.pred_len}")
    logger.info(f"  Input features: {config.enc_in}")
    logger.info(f"  Model dimension: {config.d_model}")
    logger.info(f"  Attention heads: {config.n_heads}")
    logger.info(f"  Encoder layers: {config.n_encoder_layers}")
    logger.info(f"  Decoder layers: {config.n_decoder_layers}")
    logger.info(f"  FFN hidden dimension: {config.d_ff}")
    logger.info(f"  ProbSparse factor: {config.factor}")
    logger.info(f"  Dropout: {config.dropout}")
    
    logger.info("\nModel Complexity:")
    total_params = model.count_parameters()
    logger.info(f"  Total parameters: {total_params:,}")
    logger.info(f"  Estimated memory: {(total_params * 4) / (1024**2):.2f} MB (FP32)")
    logger.info(f"  Estimated memory: {(total_params * 2) / (1024**2):.2f} MB (FP16/mixed)")
    
    attn_info = model.get_attention_weights()
    logger.info("\nAttention Information:")
    for key, value in attn_info.items():
        logger.info(f"  {key}: {value}")


def run_all_examples():
    """Run all examples"""
    logger.info("\n" + "="*80)
    logger.info("INFORMER MODEL - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("="*80)
    
    try:
        # Example 1: Basic training (skip for speed in examples)
        # example_1_basic_training()
        logger.info("\nSkipping Example 1 (basic training) - use train.py for full training")
        
        # Example 2-8: Inference and deployment examples
        example_2_single_prediction()
        example_3_batch_prediction()
        example_4_real_time_streaming()
        example_5_model_deployment()
        example_6_attention_visualization()
        example_7_uncertainty_calibration()
        example_8_model_information()
        
        logger.info("\n" + "="*80)
        logger.info("✓ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        logger.info("="*80)
        logger.info("\nNext steps:")
        logger.info("1. Train full model: python train.py")
        logger.info("2. Run benchmarks: python benchmark.py")
        logger.info("3. Deploy to production: See example_5_model_deployment()")
        logger.info("="*80 + "\n")
        
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        logger.error("Please ensure model checkpoint exists or run train.py first")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_examples()

# clean architecture alignment
