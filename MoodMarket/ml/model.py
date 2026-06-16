"""
Informer Model for Financial Time-Series Forecasting
Implements ProbSparse Self-Attention with Encoder-Decoder Architecture
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
import math


@dataclass
class InformerConfig:
    """Configuration for Informer model"""
    seq_len: int = 72
    pred_len: int = 1  # Predicting 1 timestep ahead (4 hours)
    enc_in: int = 8  # Input features
    dec_in: int = 8
    c_out: int = 1  # Output dimension (probability)
    d_model: int = 512
    n_heads: int = 8
    n_encoder_layers: int = 2
    n_decoder_layers: int = 2
    d_ff: int = 2048
    dropout: float = 0.1
    attn_dropout: float = 0.1
    factor: int = 5  # For ProbSparse attention
    activation: str = "gelu"
    device: torch.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class PositionalEncoding(nn.Module):
    """Positional encoding for time-series data"""
    
    def __init__(self, d_model: int, max_len: int = 5000) -> None:
        """
        Args:
            d_model: Model dimension
            max_len: Maximum sequence length
        """
        super().__init__()
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2, dtype=torch.float) * 
            (-math.log(10000.0) / d_model)
        )
        
        pe[:, 0::2] = torch.sin(position * div_term)
        if d_model % 2 == 1:
            pe[:, 1::2] = torch.cos(position * div_term[:-1])
        else:
            pe[:, 1::2] = torch.cos(position * div_term)
        
        self.register_buffer('pe', pe.unsqueeze(0))
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor of shape (batch_size, seq_len, d_model)
        
        Returns:
            Positional encoded tensor
        """
        return x + self.pe[:, :x.size(1), :]


class ProbSparseMultiHeadAttention(nn.Module):
    """ProbSparse Multi-Head Self-Attention mechanism"""
    
    def __init__(
        self,
        d_model: int,
        n_heads: int,
        dropout: float = 0.1,
        factor: int = 5,
        attn_dropout: float = 0.1
    ) -> None:
        """
        Args:
            d_model: Model dimension
            n_heads: Number of attention heads
            dropout: Dropout rate
            factor: Sparsity factor for ProbSparse
            attn_dropout: Attention dropout rate
        """
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.factor = factor
        self.d_k = d_model // n_heads
        
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"
        
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)
        
        self.dropout = nn.Dropout(dropout)
        self.attn_dropout = nn.Dropout(attn_dropout)
    
    def _prob_sparse_attention(
        self,
        Q: torch.Tensor,
        K: torch.Tensor,
        V: torch.Tensor,
        attn_mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        ProbSparse attention computation
        
        Args:
            Q: Query tensor (batch_size * n_heads, seq_len, d_k)
            K: Key tensor
            V: Value tensor
            attn_mask: Attention mask
        
        Returns:
            Tuple of (output, attention_weights)
        """
        batch_heads, L_Q, _ = Q.shape
        _, L_K, _ = K.shape
        
        # Calculate query sparsity
        U = int(self.factor * np.ceil(np.log(L_K)))
        
        # Top-u queries based on max attention scores
        scores = torch.bmm(Q, K.transpose(1, 2)) / math.sqrt(self.d_k)
        
        if L_K > L_Q and L_Q > U:
            # Use top-u for efficiency
            _, top_k_idx = torch.topk(scores.max(dim=1)[0], U, dim=1)
            attn_weights = torch.softmax(scores, dim=-1)
            attn_weights = torch.gather(attn_weights, 1, top_k_idx.unsqueeze(1).expand(-1, U, -1))
        else:
            attn_weights = torch.softmax(scores, dim=-1)
        
        attn_weights = self.attn_dropout(attn_weights)
        
        if attn_mask is not None:
            attn_weights = attn_weights.masked_fill(attn_mask == 0, 0.0)
        
        output = torch.bmm(attn_weights, V)
        
        return output, attn_weights
    
    def forward(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        attn_mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            query: Query tensor (batch_size, seq_len, d_model)
            key: Key tensor
            value: Value tensor
            attn_mask: Attention mask
        
        Returns:
            Tuple of (output, attention_weights)
        """
        batch_size = query.size(0)
        
        # Linear transformations
        Q = self.W_q(query).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        K = self.W_k(key).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        V = self.W_v(value).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        
        Q = Q.reshape(batch_size * self.n_heads, -1, self.d_k)
        K = K.reshape(batch_size * self.n_heads, -1, self.d_k)
        V = V.reshape(batch_size * self.n_heads, -1, self.d_k)
        
        # ProbSparse attention
        attn_output, attn_weights = self._prob_sparse_attention(Q, K, V, attn_mask)
        
        # Reshape and apply output projection
        attn_output = attn_output.reshape(batch_size, self.n_heads, -1, self.d_k)
        attn_output = attn_output.transpose(1, 2).contiguous()
        attn_output = attn_output.view(batch_size, -1, self.d_model)
        
        output = self.W_o(attn_output)
        output = self.dropout(output)
        
        return output, attn_weights


class FeedForward(nn.Module):
    """Feed-Forward Network"""
    
    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.1, activation: str = "gelu") -> None:
        """
        Args:
            d_model: Model dimension
            d_ff: Feed-forward dimension
            dropout: Dropout rate
            activation: Activation function
        """
        super().__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(dropout)
        
        if activation == "gelu":
            self.activation = nn.GELU()
        elif activation == "relu":
            self.activation = nn.ReLU()
        else:
            self.activation = nn.GELU()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor
        
        Returns:
            Output tensor
        """
        return self.linear2(self.dropout(self.activation(self.linear1(x))))


class EncoderLayer(nn.Module):
    """Single Encoder Layer"""
    
    def __init__(
        self,
        d_model: int,
        n_heads: int,
        d_ff: int,
        dropout: float = 0.1,
        attn_dropout: float = 0.1,
        factor: int = 5,
        activation: str = "gelu"
    ) -> None:
        """
        Args:
            d_model: Model dimension
            n_heads: Number of attention heads
            d_ff: Feed-forward dimension
            dropout: Dropout rate
            attn_dropout: Attention dropout rate
            factor: Sparsity factor
            activation: Activation function
        """
        super().__init__()
        
        self.self_attn = ProbSparseMultiHeadAttention(
            d_model, n_heads, dropout, factor, attn_dropout
        )
        self.feed_forward = FeedForward(d_model, d_ff, dropout, activation)
        
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor, attn_mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: Input tensor
            attn_mask: Attention mask
        
        Returns:
            Tuple of (output, attention_weights)
        """
        # Self-attention with residual connection
        attn_output, attn_weights = self.self_attn(x, x, x, attn_mask)
        x = x + self.dropout1(attn_output)
        x = self.norm1(x)
        
        # Feed-forward with residual connection
        ff_output = self.feed_forward(x)
        x = x + self.dropout2(ff_output)
        x = self.norm2(x)
        
        return x, attn_weights


class DecoderLayer(nn.Module):
    """Single Decoder Layer"""
    
    def __init__(
        self,
        d_model: int,
        n_heads: int,
        d_ff: int,
        dropout: float = 0.1,
        attn_dropout: float = 0.1,
        factor: int = 5,
        activation: str = "gelu"
    ) -> None:
        """
        Args:
            d_model: Model dimension
            n_heads: Number of attention heads
            d_ff: Feed-forward dimension
            dropout: Dropout rate
            attn_dropout: Attention dropout rate
            factor: Sparsity factor
            activation: Activation function
        """
        super().__init__()
        
        self.self_attn = ProbSparseMultiHeadAttention(
            d_model, n_heads, dropout, factor, attn_dropout
        )
        self.cross_attn = ProbSparseMultiHeadAttention(
            d_model, n_heads, dropout, factor, attn_dropout
        )
        self.feed_forward = FeedForward(d_model, d_ff, dropout, activation)
        
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.norm3 = nn.LayerNorm(d_model)
        
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
        self.dropout3 = nn.Dropout(dropout)
    
    def forward(
        self,
        x: torch.Tensor,
        encoder_output: torch.Tensor,
        self_attn_mask: Optional[torch.Tensor] = None,
        cross_attn_mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Args:
            x: Input tensor
            encoder_output: Encoder output
            self_attn_mask: Self-attention mask
            cross_attn_mask: Cross-attention mask
        
        Returns:
            Tuple of (output, self_attn_weights, cross_attn_weights)
        """
        # Self-attention
        self_attn_output, self_attn_weights = self.self_attn(x, x, x, self_attn_mask)
        x = x + self.dropout1(self_attn_output)
        x = self.norm1(x)
        
        # Cross-attention
        cross_attn_output, cross_attn_weights = self.cross_attn(x, encoder_output, encoder_output, cross_attn_mask)
        x = x + self.dropout2(cross_attn_output)
        x = self.norm2(x)
        
        # Feed-forward
        ff_output = self.feed_forward(x)
        x = x + self.dropout3(ff_output)
        x = self.norm3(x)
        
        return x, self_attn_weights, cross_attn_weights


class Encoder(nn.Module):
    """Encoder stack"""
    
    def __init__(self, layers: nn.ModuleList, norm: nn.Module) -> None:
        """
        Args:
            layers: List of encoder layers
            norm: Normalization layer
        """
        super().__init__()
        self.layers = layers
        self.norm = norm
    
    def forward(self, x: torch.Tensor, attn_mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, List[torch.Tensor]]:
        """
        Args:
            x: Input tensor
            attn_mask: Attention mask
        
        Returns:
            Tuple of (output, attention_weights_list)
        """
        attn_weights_list = []
        
        for layer in self.layers:
            x, attn_weights = layer(x, attn_mask)
            attn_weights_list.append(attn_weights)
        
        x = self.norm(x)
        
        return x, attn_weights_list


class Decoder(nn.Module):
    """Decoder stack"""
    
    def __init__(self, layers: nn.ModuleList, norm: nn.Module) -> None:
        """
        Args:
            layers: List of decoder layers
            norm: Normalization layer
        """
        super().__init__()
        self.layers = layers
        self.norm = norm
    
    def forward(
        self,
        x: torch.Tensor,
        encoder_output: torch.Tensor,
        self_attn_mask: Optional[torch.Tensor] = None,
        cross_attn_mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, List[torch.Tensor], List[torch.Tensor]]:
        """
        Args:
            x: Input tensor
            encoder_output: Encoder output
            self_attn_mask: Self-attention mask
            cross_attn_mask: Cross-attention mask
        
        Returns:
            Tuple of (output, self_attn_weights_list, cross_attn_weights_list)
        """
        self_attn_weights_list = []
        cross_attn_weights_list = []
        
        for layer in self.layers:
            x, self_attn_weights, cross_attn_weights = layer(
                x, encoder_output, self_attn_mask, cross_attn_mask
            )
            self_attn_weights_list.append(self_attn_weights)
            cross_attn_weights_list.append(cross_attn_weights)
        
        x = self.norm(x)
        
        return x, self_attn_weights_list, cross_attn_weights_list


class Informer(nn.Module):
    """Informer Model for Time-Series Forecasting"""
    
    def __init__(self, config: InformerConfig) -> None:
        """
        Args:
            config: Model configuration
        """
        super().__init__()
        self.config = config
        self.device = config.device
        
        # Input projection
        self.encoder_projection = nn.Linear(config.enc_in, config.d_model)
        self.decoder_projection = nn.Linear(config.dec_in, config.d_model)
        
        # Positional encoding
        self.pos_encoding = PositionalEncoding(config.d_model, max_len=config.seq_len + config.pred_len)
        
        # Encoder layers
        encoder_layers = nn.ModuleList([
            EncoderLayer(
                config.d_model,
                config.n_heads,
                config.d_ff,
                config.dropout,
                config.attn_dropout,
                config.factor,
                config.activation
            )
            for _ in range(config.n_encoder_layers)
        ])
        self.encoder = Encoder(encoder_layers, nn.LayerNorm(config.d_model))
        
        # Decoder layers
        decoder_layers = nn.ModuleList([
            DecoderLayer(
                config.d_model,
                config.n_heads,
                config.d_ff,
                config.dropout,
                config.attn_dropout,
                config.factor,
                config.activation
            )
            for _ in range(config.n_decoder_layers)
        ])
        self.decoder = Decoder(decoder_layers, nn.LayerNorm(config.d_model))
        
        # Output layer: project to prediction + confidence
        self.output_projection = nn.Sequential(
            nn.Linear(config.d_model, config.d_model // 2),
            nn.GELU(),
            nn.Linear(config.d_model // 2, config.c_out + 1)  # +1 for uncertainty
        )
        
        self.to(self.device)
    
    def forward(
        self,
        encoder_input: torch.Tensor,
        decoder_input: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, List[torch.Tensor]]]:
        """
        Forward pass
        
        Args:
            encoder_input: Encoder input (batch_size, seq_len, enc_in)
            decoder_input: Decoder input (batch_size, pred_len, dec_in)
        
        Returns:
            Tuple of (output, uncertainty, attention_weights_dict)
        """
        # Project and add positional encoding to encoder input
        enc_embedded = self.encoder_projection(encoder_input)
        enc_embedded = self.pos_encoding(enc_embedded)
        
        # Encoder
        encoder_output, encoder_attn_weights = self.encoder(enc_embedded)
        
        # Project and add positional encoding to decoder input
        dec_embedded = self.decoder_projection(decoder_input)
        # Offset position encoding for decoder
        dec_embedded = self.pos_encoding(dec_embedded)
        
        # Decoder
        decoder_output, decoder_self_attn_weights, decoder_cross_attn_weights = self.decoder(
            dec_embedded, encoder_output
        )
        
        # Output projection
        logits = self.output_projection(decoder_output)
        
        # Split output into prediction and uncertainty
        prediction = torch.sigmoid(logits[..., :self.config.c_out])  # Probability between 0 and 1
        uncertainty = F.softplus(logits[..., self.config.c_out:])  # Uncertainty as positive value
        
        attention_weights = {
            'encoder': encoder_attn_weights,
            'decoder_self': decoder_self_attn_weights,
            'decoder_cross': decoder_cross_attn_weights
        }
        
        return prediction, uncertainty, attention_weights
    
    def get_attention_weights(self) -> Dict[str, str]:
        """
        Get attention weight extraction info for explainability
        
        Returns:
            Dictionary with attention extraction details
        """
        return {
            'encoder_layers': str(self.config.n_encoder_layers),
            'decoder_layers': str(self.config.n_decoder_layers),
            'n_heads': str(self.config.n_heads),
            'factor': str(self.config.factor)
        }
    
    def count_parameters(self) -> int:
        """Count trainable parameters"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def quantize_int8(self) -> None:
        """Convert model to int8 quantization for edge deployment"""
        self.cpu()
        torch.quantization.quantize_dynamic(
            self, {nn.Linear, nn.LSTM}, dtype=torch.qint8
        )
    
    def save_checkpoint(self, filepath: str, optimizer: Optional[torch.optim.Optimizer] = None) -> None:
        """
        Save model checkpoint
        
        Args:
            filepath: Path to save checkpoint
            optimizer: Optional optimizer to save state
        """
        checkpoint = {
            'config': self.config,
            'model_state_dict': self.state_dict(),
        }
        if optimizer is not None:
            checkpoint['optimizer_state_dict'] = optimizer.state_dict()
        
        torch.save(checkpoint, filepath)
    
    @staticmethod
    def load_checkpoint(filepath: str, device: torch.device) -> Tuple['Informer', Optional[Dict]]:
        """
        Load model checkpoint
        
        Args:
            filepath: Path to checkpoint
            device: Device to load on
        
        Returns:
            Tuple of (model, optimizer_state_dict)
        """
        try:
            checkpoint = torch.load(filepath, map_location=device, weights_only=False)
        except TypeError:
            checkpoint = torch.load(filepath, map_location=device)
        config = checkpoint['config']
        config.device = device
        
        model = Informer(config).to(device)
        model.load_state_dict(checkpoint['model_state_dict'])
        
        optimizer_state = checkpoint.get('optimizer_state_dict')
        
        return model, optimizer_state


class HuberLoss(nn.Module):
    """Custom Huber Loss for robust handling of outliers"""
    
    def __init__(self, delta: float = 1.0) -> None:
        """
        Args:
            delta: Huber loss delta parameter
        """
        super().__init__()
        self.delta = delta
    
    def forward(self, output: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """
        Args:
            output: Model output (batch_size, pred_len, 1)
            target: Target values (batch_size, pred_len, 1)
        
        Returns:
            Huber loss value
        """
        error = output - target
        is_small_error = torch.abs(error) < self.delta
        
        small_error_loss = 0.5 * torch.pow(error, 2)
        large_error_loss = self.delta * (torch.abs(error) - 0.5 * self.delta)
        
        loss = torch.where(is_small_error, small_error_loss, large_error_loss)
        
        return loss.mean()

# clean architecture alignment
