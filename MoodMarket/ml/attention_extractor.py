import torch
import numpy as np
from typing import Dict, Any, List, Optional, Union


class AttentionExtractor:
    """
    Extracts and processes attention weights from the Informer model.
    Transforms raw multi-head attention weights into consolidated step-level distributions.
    """
    def __init__(self, model):
        self.model = model
        self.n_heads = model.config.n_heads
        self.n_layers = model.config.n_encoder_layers
        self.seq_len = model.config.seq_len

    def extract_encoder_attention(
        self,
        attention_weights: Dict[str, List[torch.Tensor]],
        batch_idx: int = 0,
        layer_aggregation: str = "mean",
        head_aggregation: str = "mean"
    ) -> np.ndarray:
        """
        Extracts and pools the encoder self-attention weights.
        
        Args:
            attention_weights: Dictionary containing attention weight lists from Informer forward pass.
            batch_idx: The batch index of the sample to extract.
            layer_aggregation: How to aggregate across encoder layers ("mean", "max", "last").
            head_aggregation: How to aggregate across attention heads ("mean", "max").
            
        Returns:
            np.ndarray: Aggregated attention matrix of shape (seq_len, seq_len).
        """
        enc_attn_list = attention_weights.get("encoder", [])
        if not enc_attn_list:
            raise ValueError("No encoder attention weights found in the model outputs.")
            
        # Process each layer
        processed_layers = []
        for layer_attn in enc_attn_list:
            # layer_attn shape is (batch_size * n_heads, seq_len, seq_len)
            # Reshape to (batch_size, n_heads, seq_len, seq_len)
            total_elements = layer_attn.size(0)
            batch_size = total_elements // self.n_heads
            
            reshaped_attn = layer_attn.view(batch_size, self.n_heads, self.seq_len, self.seq_len)
            
            # Select target sample in batch
            sample_attn = reshaped_attn[batch_idx]  # Shape: (n_heads, seq_len, seq_len)
            
            # Aggregate heads
            if head_aggregation == "mean":
                head_attn = torch.mean(sample_attn, dim=0)
            elif head_aggregation == "max":
                head_attn, _ = torch.max(sample_attn, dim=0)
            else:
                raise ValueError(f"Unknown head aggregation method: {head_aggregation}")
                
            processed_layers.append(head_attn.detach().cpu().numpy())
            
        # Aggregate layers
        processed_layers = np.array(processed_layers)  # Shape: (n_layers, seq_len, seq_len)
        
        if layer_aggregation == "mean":
            aggregated = np.mean(processed_layers, axis=0)
        elif layer_aggregation == "max":
            aggregated = np.max(processed_layers, axis=0)
        elif layer_aggregation == "last":
            aggregated = processed_layers[-1]
        else:
            raise ValueError(f"Unknown layer aggregation method: {layer_aggregation}")
            
        return aggregated

    def get_step_importance(
        self,
        attn_matrix: np.ndarray,
        method: str = "last_step"
    ) -> np.ndarray:
        """
        Reduces a 2D attention matrix into a 1D sequence importance array.
        
        Args:
            attn_matrix: 2D attention matrix of shape (seq_len, seq_len).
            method: Method for mapping 2D to 1D:
                    - "last_step": Attention paid by the very last timestep (predictive point).
                    - "mean_importance": Mean attention paid by all timesteps.
                    
        Returns:
            np.ndarray: 1D normalized weights of length seq_len.
        """
        if method == "last_step":
            # Extract row corresponding to the last query timestep
            importance = attn_matrix[-1, :]
        elif method == "mean_importance":
            # Average across the query dimension (rows)
            importance = np.mean(attn_matrix, axis=0)
        else:
            raise ValueError(f"Unknown importance mapping method: {method}")
            
        # Normalize to sum to 1
        total = np.sum(importance)
        if total > 0:
            importance = importance / total
            
        return importance

# clean architecture alignment
