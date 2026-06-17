import os
import torch
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List, Optional
from torch.utils.data import Dataset, DataLoader
import logging

logger = logging.getLogger("data_loader")

class FinancialDataset(Dataset):
    """
    Dataset representing sliding windows of financial time-series.
    Prevents data leakage by utilizing walk-forward validation slices.
    """
    def __init__(self, data: np.ndarray, seq_len: int = 72, pred_len: int = 1, stride: int = 1):
        """
        Args:
            data: Preprocessed data of shape (timesteps, 8_features)
            seq_len: Historical lookback sequence length (default 72)
            pred_len: Forecasting steps ahead (default 1)
            stride: Step stride (default 1)
        """
        self.data = torch.from_numpy(data).float()
        self.seq_len = seq_len
        self.pred_len = pred_len
        self.stride = stride
        self.n_samples = len(data) - seq_len - pred_len + 1

    def __len__(self) -> int:
        return max(0, self.n_samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        start = idx
        end = start + self.seq_len
        pred_end = end + self.pred_len
        
        encoder_input = self.data[start:end]
        # Decoder input: start with last point of encoder, pad remaining steps
        decoder_input = self.data[end-1:pred_end-1]
        
        # Target: Price at pred_end. We predict if close price goes UP (classification)
        # Price is at index 1 in feature vector [sentiment, price, volume, rsi, macd, bb, google, reddit]
        price_t0 = self.data[end-1, 1]
        price_t1 = self.data[pred_end-1, 1]
        target = torch.tensor([1.0 if price_t1 > price_t0 else 0.0]).float()
        
        return encoder_input, decoder_input, target


def preprocess_data(df: pd.DataFrame) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Cleans, normalizes, and prepares raw data.
    Ensures missing values are forward filled and features are appropriately scaled.
    """
    df = df.copy()
    
    # 1. Handle missing values
    df = df.ffill().bfill()  # Forward fill then backward fill
    df = df.dropna()
    
    # 2. Extract features in order:
    # [sentiment_score, close, volume, RSI, MACD, Bollinger_Band, google_trends, reddit_hype]
    feature_cols = [
        "sentiment_score", "close", "volume", "RSI", "MACD", 
        "Bollinger_Band", "google_trends", "reddit_hype"
    ]
    
    # Verify cols exist, generate dummy defaults if missing
    for col in feature_cols:
        if col not in df.columns:
            if col == "close" and "price" in df.columns:
                df["close"] = df["price"]
            else:
                logger.warning(f"Feature column '{col}' missing. Creating default neutral values.")
                df[col] = 0.5 if col in ["RSI", "google_trends", "reddit_hype"] else 0.0
                
    data = df[feature_cols].values
    
    return data, {"feature_columns": feature_cols}


def generate_synthetic_3y_data(seed: int = 42) -> pd.DataFrame:
    """
    Generates a realistic 3-year time-series of 15-minute intervals.
    Approx 3 years * 365 days * 24 hours * 4 intervals/hour = ~105,120 rows.
    """
    np.random.seed(seed)
    logger.info("Generating 3 years of synthetic 15-minute market data...")
    
    timestamps = pd.date_range(start="2023-01-01", end="2026-01-01", freq="15min")
    n = len(timestamps)
    
    # Random walk for price
    price_noise = np.random.normal(0, 0.2, n)
    price = 100.0 + np.cumsum(price_noise)
    price = np.clip(price, 10.0, 1000.0)  # Bound price
    
    # Volume
    volume = np.random.lognormal(mean=9, sigma=0.8, size=n)
    
    # Sentiment score (-1 to 1)
    sentiment = np.clip(np.random.normal(0.05, 0.3, n), -1.0, 1.0)
    
    # Indicators
    rsi = 50.0 + np.random.normal(0, 10, n)
    rsi = np.clip(rsi, 0, 100)
    
    macd = np.random.normal(0.1, 0.5, n)
    bb_width = np.abs(np.random.normal(2.0, 0.5, n))
    
    google = np.clip(50.0 + np.random.normal(0, 15, n), 0, 100)
    reddit = np.clip(0.3 + np.random.normal(0, 0.2, n), 0, 1.0)
    
    df = pd.DataFrame({
        "timestamp": timestamps,
        "close": price,
        "volume": volume,
        "sentiment_score": sentiment,
        "RSI": rsi,
        "MACD": macd,
        "Bollinger_Band": bb_width,
        "google_trends": google,
        "reddit_hype": reddit
    })
    df.set_index("timestamp", inplace=True)
    return df


def create_walk_forward_dataloaders(
    data: np.ndarray,
    seq_len: int = 72,
    pred_len: int = 1,
    train_ratio: float = 0.65,
    val_ratio: float = 0.15,
    batch_size: int = 32
) -> Tuple[DataLoader, DataLoader, DataLoader, Dict[str, Any]]:
    """
    Splits data chronologically (Walk-Forward) and sets up PyTorch DataLoaders.
    Fits the normalizer ONLY on the training split to strictly prevent data leakage.
    """
    n_samples = len(data)
    train_end = int(n_samples * train_ratio)
    val_end = train_end + int(n_samples * val_ratio)
    
    # Chronological Split
    train_data = data[:train_end]
    val_data = data[train_end:val_end]
    test_data = data[val_end:]
    
    # Scale fitting (MinMax for prices, Standard for others)
    # To keep code clean and self-contained, we perform custom column-level normalization
    means = np.mean(train_data, axis=0)
    stds = np.std(train_data, axis=0)
    stds[stds == 0] = 1e-6
    
    mins = np.min(train_data, axis=0)
    maxs = np.max(train_data, axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1e-6
    
    # Preprocessing scaling parameters dictionary
    scaler_params = {
        "means": means, "stds": stds,
        "mins": mins, "maxs": maxs,
        "ranges": ranges
    }
    
    def scale_dataset(raw_arr: np.ndarray) -> np.ndarray:
        scaled = np.zeros_like(raw_arr)
        # Index 0: sentiment score -> keep -1 to 1 (standardize)
        scaled[:, 0] = (raw_arr[:, 0] - means[0]) / stds[0]
        scaled[:, 0] = np.clip(scaled[:, 0], -1.0, 1.0)
        
        # Index 1: close price -> scale 0 to 1
        scaled[:, 1] = (raw_arr[:, 1] - mins[1]) / ranges[1]
        
        # Index 2: volume -> scale 0 to 1
        scaled[:, 2] = (raw_arr[:, 2] - mins[2]) / ranges[2]
        
        # Index 3 to 7: indicators -> standard scaler
        for col in range(3, 8):
            scaled[:, col] = (raw_arr[:, col] - mins[col]) / ranges[col]
            
        return scaled
        
    train_scaled = scale_dataset(train_data)
    val_scaled = scale_dataset(val_data)
    test_scaled = scale_dataset(test_data)
    
    # Datasets
    train_dataset = FinancialDataset(train_scaled, seq_len, pred_len)
    val_dataset = FinancialDataset(val_scaled, seq_len, pred_len)
    test_dataset = FinancialDataset(test_scaled, seq_len, pred_len)
    
    # DataLoaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    logger.info(
        f"Walk-Forward DataLoaders initialized: "
        f"Train={len(train_dataset)} samples, Val={len(val_dataset)} samples, Test={len(test_dataset)} samples."
    )
    
    return train_loader, val_loader, test_loader, scaler_params


# ============================================================================
# Compatibility Helpers (Backward Compatibility)
# ============================================================================

def create_dataloaders(*args, **kwargs):
    """Compatibility alias for create_walk_forward_dataloaders."""
    # Remove scaler_params from output for compatibility with simple test scripts
    train, val, test, _ = create_walk_forward_dataloaders(*args, **kwargs)
    return train, val, test


def generate_synthetic_data(n_samples: int = 10000) -> np.ndarray:
    """Generates a numpy array of synthetic features for model testing/benchmarking."""
    np.random.seed(42)
    # 8 features: sentiment, close, volume, RSI, MACD, BB, google_trends, reddit_hype
    # Use 1-D arrays throughout so np.column_stack works cleanly.
    sentiment = np.random.uniform(-1.0, 1.0, n_samples)
    close = np.cumprod(1 + np.random.normal(0, 0.01, n_samples))  # Random walk close price
    volume = np.random.exponential(1000, n_samples)
    rsi = np.random.uniform(20, 80, n_samples)
    macd = np.random.normal(0, 2, n_samples)
    bb = np.random.normal(0, 1, n_samples)
    google_trends = np.random.uniform(10, 100, n_samples)
    reddit_hype = np.random.exponential(5, n_samples)

    return np.column_stack([sentiment, close, volume, rsi, macd, bb, google_trends, reddit_hype])
