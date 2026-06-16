"""
Configuration file for Informer model experimentation
Modify these settings to experiment with different configurations
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExperimentConfig:
    """Master configuration for experiments"""
    
    # ======================================================================
    # DATA CONFIGURATION
    # ======================================================================
    
    # Dataset size
    n_total_samples: int = 100000          # Total synthetic samples to generate
    n_training_samples: int = None         # None = use ratio below
    
    # Split ratios
    train_ratio: float = 0.70              # 70% training
    val_ratio: float = 0.15                # 15% validation
    test_ratio: float = 0.15               # 15% test
    
    # Data normalization
    normalize_data: bool = True            # Z-score normalization
    random_seed: int = 42                  # Reproducibility
    
    # ======================================================================
    # TIME SERIES CONFIGURATION
    # ======================================================================
    
    seq_len: int = 72                      # Input sequence: 24 hours of 15-min candles
    pred_len: int = 1                      # Forecast horizon: next 4 hours
    n_features: int = 8                    # Input features
    
    # Features: [sentiment_score, price, volume, RSI, MACD, Bollinger_Band, google_trends, reddit_hype]
    
    # ======================================================================
    # MODEL CONFIGURATION
    # ======================================================================
    
    # Model type
    model_type: str = "Informer"           # "Informer" or "LSTM"
    
    # Dimensions
    d_model: int = 512                     # Embedding dimension (256/512/768)
    d_ff: int = 2048                       # FFN hidden dimension (1024/2048/4096)
    
    # Architecture depth
    n_encoder_layers: int = 2              # Encoder depth (1/2/3)
    n_decoder_layers: int = 2              # Decoder depth (1/2/3)
    
    # Attention
    n_heads: int = 8                       # Number of attention heads (4/8/16)
    attention_type: str = "probsparse"     # "probsparse" or "full"
    factor: int = 5                        # ProbSparse factor (3/5/10)
    
    # Dropout & regularization
    dropout: float = 0.1                   # Dropout rate (0.05/0.1/0.2)
    attn_dropout: float = 0.1              # Attention dropout
    weight_decay: float = 1e-5             # L2 regularization
    
    # Activation
    activation: str = "gelu"               # "gelu" or "relu"
    
    # ======================================================================
    # TRAINING CONFIGURATION
    # ======================================================================
    
    # Training parameters
    n_epochs: int = 50                     # Maximum epochs (20/50/100)
    batch_size: int = 64                   # Batch size (32/64/128)
    learning_rate: float = 1e-4            # Initial learning rate (1e-5/1e-4/5e-4)
    
    # Optimizer
    optimizer_type: str = "adamw"          # "adamw" or "adam"
    beta1: float = 0.9                     # Adam beta1
    beta2: float = 0.999                   # Adam beta2
    
    # Learning rate scheduler
    scheduler_type: str = "cosine"         # "cosine" or "linear"
    warmup_epochs: int = 0                 # Warmup epochs
    min_lr: float = 1e-6                   # Minimum learning rate
    
    # Gradient clipping
    gradient_clip: float = 1.0             # Clip norm (0.5/1.0/5.0)
    
    # Early stopping
    early_stopping_patience: int = 15      # Patience for early stopping
    early_stopping_min_delta: float = 1e-4 # Minimum improvement
    
    # ======================================================================
    # LOSS CONFIGURATION
    # ======================================================================
    
    loss_type: str = "bce_huber"           # "bce_huber" or "bce_only"
    huber_delta: float = 1.0               # Huber loss delta
    uncertainty_weight: float = 0.01       # Uncertainty regularization weight
    
    # ======================================================================
    # VALIDATION CONFIGURATION
    # ======================================================================
    
    validation_metric: str = "accuracy"    # "loss" or "accuracy"
    save_best_only: bool = True            # Save only best model
    checkpoint_dir: str = "./checkpoints"  # Checkpoint directory
    
    # ======================================================================
    # INFERENCE CONFIGURATION
    # ======================================================================
    
    # Confidence intervals
    confidence_level: float = 0.95         # 95% CI (0.90/0.95/0.99)
    
    # Uncertainty quantification
    mc_samples: int = 10                   # Monte Carlo samples for uncertainty
    
    # Batch processing
    inference_batch_size: int = 32         # Batch size for inference
    
    # ======================================================================
    # DEPLOYMENT CONFIGURATION
    # ======================================================================
    
    quantize_model: bool = False           # Use int8 quantization
    prune_model: bool = False              # Structured pruning
    max_memory_mb: float = 4096            # Max GPU memory (MB)
    
    # ======================================================================
    # HARDWARE & DEVICE
    # ======================================================================
    
    device: str = "cuda"                   # "cuda" or "cpu"
    mixed_precision: bool = False          # Mixed precision training (FP32/FP16)
    num_workers: int = 4                   # DataLoader workers
    pin_memory: bool = True                # Pin memory for faster loading
    
    # ======================================================================
    # LOGGING & MONITORING
    # ======================================================================
    
    log_level: str = "INFO"                # Logging level
    log_interval: int = 10                 # Logging interval (batches)
    save_history: bool = True              # Save training history
    history_file: str = "training_history.json"
    
    # ======================================================================
    # EXPERIMENT TRACKING
    # ======================================================================
    
    experiment_name: str = "informer_baseline"
    experiment_notes: str = ""             # Notes about experiment
    save_model_summary: bool = True        # Save model architecture
    save_config: bool = True               # Save this config


def get_baseline_config() -> ExperimentConfig:
    """Get baseline configuration (good for most cases)"""
    return ExperimentConfig()


def get_small_config() -> ExperimentConfig:
    """Get small model config (faster training, less memory)"""
    config = ExperimentConfig()
    config.d_model = 256
    config.d_ff = 1024
    config.n_heads = 4
    config.n_encoder_layers = 1
    config.n_decoder_layers = 1
    config.batch_size = 32
    return config


def get_large_config() -> ExperimentConfig:
    """Get large model config (better accuracy, more memory)"""
    config = ExperimentConfig()
    config.d_model = 768
    config.d_ff = 3072
    config.n_heads = 12
    config.n_encoder_layers = 3
    config.n_decoder_layers = 3
    config.batch_size = 128
    config.n_epochs = 100
    return config


def get_efficient_config() -> ExperimentConfig:
    """Get efficient config (production deployment)"""
    config = ExperimentConfig()
    config.d_model = 512
    config.d_ff = 2048
    config.n_heads = 8
    config.n_encoder_layers = 2
    config.n_decoder_layers = 2
    config.batch_size = 64
    config.quantize_model = True
    config.prune_model = False
    return config


def get_fast_config() -> ExperimentConfig:
    """Get fast config (quick experiments)"""
    config = ExperimentConfig()
    config.n_total_samples = 20000
    config.n_epochs = 10
    config.d_model = 256
    config.d_ff = 1024
    config.n_heads = 4
    config.batch_size = 64
    return config


def get_high_accuracy_config() -> ExperimentConfig:
    """Get high accuracy config (research/best results)"""
    config = ExperimentConfig()
    config.d_model = 768
    config.d_ff = 3072
    config.n_heads = 12
    config.n_encoder_layers = 4
    config.n_decoder_layers = 4
    config.dropout = 0.05
    config.learning_rate = 5e-4
    config.n_epochs = 100
    config.batch_size = 128
    return config


def get_lstm_baseline_config() -> ExperimentConfig:
    """Get LSTM baseline for comparison"""
    config = ExperimentConfig()
    config.model_type = "LSTM"
    config.n_epochs = 50
    config.batch_size = 64
    config.learning_rate = 1e-4
    return config


def print_config(config: ExperimentConfig) -> None:
    """Print configuration in a formatted way"""
    print("\n" + "="*60)
    print("EXPERIMENT CONFIGURATION")
    print("="*60)
    
    for key, value in config.__dict__.items():
        print(f"{key:.<40} {value}")
    
    print("="*60 + "\n")


def save_config(config: ExperimentConfig, filepath: str) -> None:
    """Save configuration to JSON file"""
    import json
    
    config_dict = config.__dict__.copy()
    # Convert device to string
    if hasattr(config_dict['device'], '__class__'):
        config_dict['device'] = str(config_dict['device'])
    
    with open(filepath, 'w') as f:
        json.dump(config_dict, f, indent=2)
    
    print(f"✓ Config saved to {filepath}")


def load_config(filepath: str) -> ExperimentConfig:
    """Load configuration from JSON file"""
    import json
    
    with open(filepath, 'r') as f:
        config_dict = json.load(f)
    
    return ExperimentConfig(**config_dict)


# ============================================================================
# HYPERPARAMETER SEARCH GRIDS
# ============================================================================

LEARNING_RATE_GRID = [1e-5, 5e-5, 1e-4, 5e-4, 1e-3]
BATCH_SIZE_GRID = [16, 32, 64, 128, 256]
DROPOUT_GRID = [0.0, 0.05, 0.1, 0.2, 0.3]
D_MODEL_GRID = [256, 384, 512, 768, 1024]
N_HEADS_GRID = [4, 8, 12, 16]
N_LAYERS_GRID = [1, 2, 3, 4, 5]


def grid_search_configs() -> list:
    """Generate configs for grid search"""
    configs = []
    
    for lr in LEARNING_RATE_GRID[:3]:  # Limit for practicality
        for batch_size in BATCH_SIZE_GRID[:3]:
            config = ExperimentConfig(
                learning_rate=lr,
                batch_size=batch_size,
                experiment_name=f"grid_lr{lr}_bs{batch_size}"
            )
            configs.append(config)
    
    return configs


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Get different configurations
    print("Available configurations:")
    print("1. get_baseline_config() - Recommended for most cases")
    print("2. get_small_config() - Fast training, low memory")
    print("3. get_large_config() - Best accuracy, high memory")
    print("4. get_efficient_config() - Production deployment")
    print("5. get_fast_config() - Quick experiments")
    print("6. get_high_accuracy_config() - Research/best results")
    print("7. get_lstm_baseline_config() - LSTM comparison")
    
    # Example: Use baseline config
    config = get_baseline_config()
    print_config(config)
    
    # Save config
    save_config(config, "config_baseline.json")
    
    # Load config
    loaded_config = load_config("config_baseline.json")
    print("✓ Config loaded successfully")


# ============================================================================
# FASTAPI & INGESTION PIPELINE SETTINGS
# ============================================================================

from pydantic_settings import BaseSettings
from pydantic import Field, model_validator, ConfigDict

class APISettings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = Field(default="development", validation_alias="ENV")
    api_key: str = Field(default="moodmarket_secret_api_key_2026", validation_alias="API_KEY")
    timescaledb_uri: str = Field(default="postgresql://postgres:postgres@localhost:5432/moodmarket", validation_alias="TIMESCALEDB_URI")
    redis_uri: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URI")
    rate_limit_per_min: int = Field(default=100, validation_alias="RATE_LIMIT_PER_MIN")
    enforce_https: bool = Field(default=False, validation_alias="ENFORCE_HTTPS")
    cors_origins: str = Field(default="*", validation_alias="CORS_ORIGINS")
    request_timeout_seconds: int = Field(default=30, validation_alias="REQUEST_TIMEOUT_SECONDS")
    
    # Ingestion sources credentials (with defaults for testing)
    reddit_client_id: str = Field(default="mock_reddit_client_id", validation_alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str = Field(default="mock_reddit_client_secret", validation_alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(default="moodmarket_scraper", validation_alias="REDDIT_USER_AGENT")
    
    news_api_key: str = Field(default="mock_news_api_key", validation_alias="NEWS_API_KEY")
    
    @model_validator(mode="after")
    def validate_prod_settings(self) -> "APISettings":
        """Validate production configuration to prevent security misconfigurations."""
        if self.env == "production":
            if self.api_key == "moodmarket_secret_api_key_2026":
                raise ValueError("API_KEY must be explicitly set in production!")
            if self.cors_origins == "*":
                raise ValueError("CORS wildcard '*' is not allowed in production! Restrict to frontend origin.")
            if not self.enforce_https:
                raise ValueError("HTTPS must be enforced in production! Set ENFORCE_HTTPS=true")
        return self

api_settings = APISettings()


# clean architecture alignment
