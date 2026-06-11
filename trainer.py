import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from typing import Tuple, Dict, Any, List, Optional
import logging
from pathlib import Path
from model import Informer, HuberLoss

logger = logging.getLogger("trainer")

class EarlyStopping:
    """Early stopping tracker monitoring validation metric."""
    def __init__(self, patience: int = 15, min_delta: float = 1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_score: Optional[float] = None
        self.early_stop = False

    def __call__(self, val_metric: float) -> bool:
        # Lower is better for loss, higher is better for accuracy.
        # We monitor validation accuracy/loss. Let's assume input is validation loss.
        score = -val_metric  # Convert to higher is better
        
        if self.best_score is None:
            self.best_score = score
        elif score < self.best_score + self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = score
            self.counter = 0
            
        return self.early_stop


class Trainer:
    """
    Production-ready Trainer suite for Informer model.
    Incorporates FP16 Mixed Precision, Gradient Accumulation, Huber Loss, and Cosine Annealing.
    """
    def __init__(
        self,
        model: Informer,
        train_loader: DataLoader,
        val_loader: DataLoader,
        test_loader: DataLoader,
        config: Dict[str, Any],
        device: torch.device
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.test_loader = test_loader
        self.device = device
        self.config = config
        
        # Hyperparameters
        self.epochs = config.get("epochs", 100)
        self.lr = config.get("learning_rate", 1e-4)
        self.weight_decay = config.get("weight_decay", 1e-5)
        self.grad_clip = config.get("grad_clip", 1.0)
        self.accumulation_steps = config.get("accumulation_steps", 4)
        
        # Loss Function: Huber Loss (robust to financial outliers)
        self.criterion = HuberLoss(delta=1.0)
        self.bce_loss = nn.BCELoss()
        
        # Optimizer
        self.optimizer = optim.AdamW(
            self.model.parameters(), 
            lr=self.lr, 
            weight_decay=self.weight_decay
        )
        
        # Learning Rate Schedule
        self.scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer,
            T_0=config.get("scheduler_T0", 10),
            T_mult=config.get("scheduler_Tmult", 2),
            eta_min=1e-6
        )
        
        # Mixed Precision Scaler
        self.scaler = torch.amp.GradScaler('cuda') if self.device.type == 'cuda' else None
        
        # Monitoring
        self.early_stopping = EarlyStopping(patience=config.get("patience", 15))
        self.train_losses = []
        self.val_losses = []
        self.val_accuracies = []
        
        self.best_val_acc = 0.0

    def train_epoch(self, epoch: int) -> float:
        self.model.train()
        total_loss = 0.0
        self.optimizer.zero_grad()
        
        batch_count = 0
        for i, (encoder_input, decoder_input, target) in enumerate(self.train_loader):
            encoder_input = encoder_input.to(self.device)
            decoder_input = decoder_input.to(self.device)
            target = target.to(self.device)
            
            # Autocast FP16 Mixed Precision
            device_type = self.device.type
            with torch.amp.autocast(device_type=device_type, enabled=(device_type == 'cuda')):
                prediction, uncertainty, _ = self.model(encoder_input, decoder_input)
                # Ensure shapes match to prevent broadcasting issues
                target = target.view(prediction.shape)
                # Compute combined loss: Huber + uncertainty regularization
                huber = self.criterion(prediction, target)
                uncertainty_reg = uncertainty.mean() * 0.01
                loss = huber + uncertainty_reg
                # Scale loss for gradient accumulation
                loss = loss / self.accumulation_steps
                
            # Backward pass
            if self.scaler is not None:
                self.scaler.scale(loss).backward()
            else:
                loss.backward()
                
            if (i + 1) % self.accumulation_steps == 0 or (i + 1) == len(self.train_loader):
                # Gradient Clipping
                if self.scaler is not None:
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
                    self.optimizer.step()
                
                self.optimizer.zero_grad()
                
            total_loss += loss.item() * self.accumulation_steps
            batch_count += 1
            
        avg_loss = total_loss / max(batch_count, 1)
        return avg_loss

    def validate(self) -> Tuple[float, float]:
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        batch_count = 0
        
        with torch.no_grad():
            for encoder_input, decoder_input, target in self.val_loader:
                encoder_input = encoder_input.to(self.device)
                decoder_input = decoder_input.to(self.device)
                target = target.to(self.device)
                
                prediction, uncertainty, _ = self.model(encoder_input, decoder_input)
                target = target.view(prediction.shape)
                loss = self.criterion(prediction, target) + uncertainty.mean() * 0.01
                
                total_loss += loss.item()
                
                pred_binary = (prediction > 0.5).float()
                correct += (pred_binary == target).sum().item()
                total += target.numel()
                batch_count += 1
                
        avg_loss = total_loss / max(batch_count, 1)
        accuracy = correct / max(total, 1)
        return avg_loss, accuracy

    def save_checkpoint(self, path: str, epoch: int, val_acc: float):
        """Save model checkpoint for training recovery."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'config': self.model.config,
            'val_acc': val_acc
        }
        torch.save(checkpoint, path)
        logger.info(f"Checkpoint saved to {path} at epoch {epoch} (Val Acc: {val_acc:.4f})")

    def load_checkpoint(self, path: str) -> int:
        """Load model state and restore optimizer/scheduler parameters."""
        try:
            checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        except TypeError:
            checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        logger.info(f"Resumed training from checkpoint {path} at epoch {checkpoint['epoch']}")
        return checkpoint['epoch']

    def train(self, checkpoint_dir: str = "./checkpoints") -> Dict[str, Any]:
        best_checkpoint = os.path.join(checkpoint_dir, "best_model.pt")
        last_checkpoint = os.path.join(checkpoint_dir, "last_checkpoint.pt")
        
        logger.info(f"Starting training pipeline on device: {self.device}")
        
        for epoch in range(self.epochs):
            train_loss = self.train_epoch(epoch)
            val_loss, val_acc = self.validate()
            
            self.train_losses.append(train_loss)
            self.val_losses.append(val_loss)
            self.val_accuracies.append(val_acc)
            
            self.scheduler.step()
            
            logger.info(
                f"Epoch {epoch + 1:03d}/{self.epochs:03d} | "
                f"Train Loss: {train_loss:.5f} | Val Loss: {val_loss:.5f} | "
                f"Val Acc: {val_acc:.4f} | LR: {self.optimizer.param_groups[0]['lr']:.2e}"
            )
            
            # Save periodic checkpoint every 5 epochs
            if (epoch + 1) % 5 == 0:
                self.save_checkpoint(os.path.join(checkpoint_dir, f"checkpoint_epoch_{epoch+1}.pt"), epoch, val_acc)
                
            # Save latest checkpoint
            self.save_checkpoint(last_checkpoint, epoch, val_acc)
            
            # Save best model based on directional accuracy
            if val_acc > self.best_val_acc:
                self.best_val_acc = val_acc
                self.save_checkpoint(best_checkpoint, epoch, val_acc)
                logger.info(f"✓ Saved new best model checkpoint with accuracy: {val_acc:.4f}")
                
            # Early stopping check
            if self.early_stopping(val_loss):
                logger.info(f"Early stopping triggered at epoch {epoch + 1}")
                break
                
        return {
            "train_losses": self.train_losses,
            "val_losses": self.val_losses,
            "val_accuracies": self.val_accuracies,
            "best_val_acc": self.best_val_acc
        }
