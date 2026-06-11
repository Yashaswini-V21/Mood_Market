import os
import argparse
import yaml
import torch
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
import logging
from torch.utils.tensorboard import SummaryWriter
import optuna
from pathlib import Path

from model import Informer, InformerConfig
from data_loader import create_walk_forward_dataloaders, preprocess_data, generate_synthetic_3y_data
from trainer import Trainer

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("train")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a YAML file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def get_data(config: Dict[str, Any]) -> pd.DataFrame:
    """Retrieve market data from CSV or generate synthetic 3-year data."""
    csv_path = config["data"].get("csv_path", "")
    if csv_path and os.path.exists(csv_path):
        logger.info(f"Loading market data from {csv_path}...")
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        df.set_index("timestamp", inplace=True)
        return df
    else:
        logger.info("No valid CSV path provided or file does not exist. Generating synthetic 3-year data...")
        return generate_synthetic_3y_data(seed=config["training"].get("seed", 42))


def train_single_run(
    config: Dict[str, Any],
    device: torch.device,
    checkpoint_dir: str,
    writer: Optional[SummaryWriter] = None
) -> Tuple[Trainer, Dict[str, Any]]:
    """Runs a single training run with the given configuration."""
    # 1. Retrieve Data
    df = get_data(config)
    data, preprocess_info = preprocess_data(df)
    
    # 2. Setup DataLoaders
    train_loader, val_loader, test_loader, scaler_params = create_walk_forward_dataloaders(
        data=data,
        seq_len=config["data"]["seq_len"],
        pred_len=config["data"]["pred_len"],
        train_ratio=config["data"]["train_ratio"],
        val_ratio=config["data"]["val_ratio"],
        batch_size=config["training"]["batch_size"]
    )
    
    # 3. Setup Model Configuration
    model_cfg = InformerConfig(
        seq_len=config["data"]["seq_len"],
        pred_len=config["data"]["pred_len"],
        enc_in=config["model"]["enc_in"],
        dec_in=config["model"]["dec_in"],
        c_out=config["model"]["c_out"],
        d_model=config["model"]["d_model"],
        n_heads=config["model"]["n_heads"],
        n_encoder_layers=config["model"]["n_encoder_layers"],
        n_decoder_layers=config["model"]["n_decoder_layers"],
        d_ff=config["model"]["d_ff"],
        dropout=config["model"]["dropout"],
        factor=config["model"]["factor"],
        device=device
    )
    
    model = Informer(model_cfg)
    
    # 4. Setup Trainer
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        config=config["training"],
        device=device
    )
    
    # 5. Overwrite Trainer training loop to support TensorBoard logging
    # We will log training & validation loss and validation accuracy per epoch
    best_checkpoint = os.path.join(checkpoint_dir, "best_model.pt")
    last_checkpoint = os.path.join(checkpoint_dir, "last_checkpoint.pt")
    
    logger.info(f"Starting training run (Model Parameters: {model.count_parameters():,})")
    
    for epoch in range(trainer.epochs):
        train_loss = trainer.train_epoch(epoch)
        val_loss, val_acc = trainer.validate()
        
        trainer.train_losses.append(train_loss)
        trainer.val_losses.append(val_loss)
        trainer.val_accuracies.append(val_acc)
        
        trainer.scheduler.step()
        
        # Tensorboard Logs
        if writer is not None:
            writer.add_scalar("Loss/Train", train_loss, epoch)
            writer.add_scalar("Loss/Val", val_loss, epoch)
            writer.add_scalar("Accuracy/Val", val_acc, epoch)
            writer.add_scalar("LearningRate", trainer.optimizer.param_groups[0]["lr"], epoch)
            
        logger.info(
            f"Epoch {epoch + 1:03d}/{trainer.epochs:03d} | "
            f"Train Loss: {train_loss:.5f} | Val Loss: {val_loss:.5f} | "
            f"Val Acc: {val_acc:.4f} | LR: {trainer.optimizer.param_groups[0]['lr']:.2e}"
        )
        
        # Save checkpoints
        if (epoch + 1) % 5 == 0:
            trainer.save_checkpoint(
                os.path.join(checkpoint_dir, f"checkpoint_epoch_{epoch+1}.pt"), epoch, val_acc
            )
            
        trainer.save_checkpoint(last_checkpoint, epoch, val_acc)
        
        if val_acc > trainer.best_val_acc:
            trainer.best_val_acc = val_acc
            trainer.save_checkpoint(best_checkpoint, epoch, val_acc)
            logger.info(f"✓ Saved new best model checkpoint (Val Acc: {val_acc:.4f})")
            
        if trainer.early_stopping(val_loss):
            logger.info(f"Early stopping triggered at epoch {epoch + 1}")
            break
            
    # Load best model for evaluation
    if os.path.exists(best_checkpoint):
        best_model, _ = Informer.load_checkpoint(best_checkpoint, device)
        trainer.model = best_model
        
    return trainer, scaler_params


def run_optuna_tuning(config: Dict[str, Any], device: torch.device, checkpoint_dir: str) -> Dict[str, Any]:
    """Runs Optuna hyperparameter optimization to find the best configuration."""
    n_trials = config["optuna"].get("n_trials", 10)
    timeout = config["optuna"].get("timeout_seconds", 600)
    
    logger.info(f"Starting Optuna search with {n_trials} trials (timeout: {timeout} seconds)...")
    
    def objective(trial: optuna.Trial) -> float:
        # Suggest trial hyperparameters
        lr = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
        weight_decay = trial.suggest_float("weight_decay", 1e-6, 1e-4, log=True)
        d_model = trial.suggest_categorical("d_model", [128, 256, 512])
        n_heads = trial.suggest_categorical("n_heads", [4, 8])
        factor = trial.suggest_int("factor", 3, 7)
        dropout = trial.suggest_float("dropout", 0.05, 0.2)
        batch_size = trial.suggest_categorical("batch_size", [16, 32, 64])
        
        # Temporary trial config
        trial_config = {
            "training": {
                "batch_size": batch_size,
                "epochs": 10,  # Run fewer epochs for quick trial search
                "learning_rate": lr,
                "weight_decay": weight_decay,
                "grad_clip": 1.0,
                "patience": 3,
                "accumulation_steps": 2,
                "scheduler_T0": 5,
                "scheduler_Tmult": 2,
                "seed": config["training"].get("seed", 42)
            },
            "data": config["data"],
            "model": {
                "enc_in": config["model"]["enc_in"],
                "dec_in": config["model"]["dec_in"],
                "c_out": config["model"]["c_out"],
                "d_model": d_model,
                "n_heads": n_heads,
                "n_encoder_layers": config["model"]["n_encoder_layers"],
                "n_decoder_layers": config["model"]["n_decoder_layers"],
                "d_ff": d_model * 4,  # Standard expansion
                "dropout": dropout,
                "factor": factor
            }
        }
        
        trial_checkpoint_dir = os.path.join(checkpoint_dir, f"trial_{trial.number}")
        os.makedirs(trial_checkpoint_dir, exist_ok=True)
        
        try:
            trainer, _ = train_single_run(trial_config, device, trial_checkpoint_dir)
            return trainer.best_val_acc
        except Exception as e:
            logger.warning(f"Trial {trial.number} failed with error: {e}")
            return 0.0
            
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, timeout=timeout)
    
    logger.info("Optuna search completed!")
    logger.info(f"Best Trial: #{study.best_trial.number}")
    logger.info(f"Best Value (Val Acc): {study.best_value:.4f}")
    logger.info(f"Best Hyperparameters: {study.best_params}")
    
    return study.best_params


def main():
    parser = argparse.ArgumentParser(description="Train Informer Forecasting Model")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--tune", action="store_true", help="Run Optuna hyperparameter search")
    parser.add_argument("--epochs", type=int, default=None, help="Override training epochs")
    parser.add_argument("--checkpoint-dir", type=str, default="./checkpoints", help="Directory for checkpoints")
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    # Overwrite config epochs if provided via CLI
    if args.epochs is not None:
        config["training"]["epochs"] = args.epochs
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    
    os.makedirs(args.checkpoint_dir, exist_ok=True)
    
    # Optional Optuna Tuning
    if args.tune:
        best_params = run_optuna_tuning(config, device, args.checkpoint_dir)
        # Update config with best parameters for final run
        config["training"]["learning_rate"] = best_params["learning_rate"]
        config["training"]["weight_decay"] = best_params["weight_decay"]
        config["training"]["batch_size"] = best_params["batch_size"]
        config["model"]["d_model"] = best_params["d_model"]
        config["model"]["n_heads"] = best_params["n_heads"]
        config["model"]["factor"] = best_params["factor"]
        config["model"]["dropout"] = best_params["dropout"]
        config["model"]["d_ff"] = best_params["d_model"] * 4
        
        # Save tuned config
        tuned_config_path = os.path.join(args.checkpoint_dir, "tuned_config.yaml")
        with open(tuned_config_path, "w") as f:
            yaml.dump(config, f)
        logger.info(f"Tuned config saved to {tuned_config_path}")
        
    # Tensorboard Setup
    tb_log_dir = os.path.join(args.checkpoint_dir, "runs", pd.Timestamp.now().strftime("%Y%m%d-%H%M%S"))
    writer = SummaryWriter(log_dir=tb_log_dir)
    logger.info(f"TensorBoard logging enabled. Run 'tensorboard --logdir={args.checkpoint_dir}/runs' to view.")
    
    # Final training run
    trainer, scaler_params = train_single_run(config, device, args.checkpoint_dir, writer)
    writer.close()
    
    # Save the final preprocessor scaling factors
    np.savez(os.path.join(args.checkpoint_dir, "scaler_params.npz"), **scaler_params)
    logger.info(f"Scaling parameters saved to {args.checkpoint_dir}/scaler_params.npz")
    logger.info("✓ Final Informer model training completed successfully!")


if __name__ == "__main__":
    main()
