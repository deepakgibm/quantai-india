import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional, Tuple

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)]

class QuantAIInformer(nn.Module):
    """
    Encoder-only Transformer/Informer for Price Forecasting.
    Consumes sequences of engineered features + embeddings.
    """
    def __init__(self, 
                 num_features: int, 
                 num_symbols: int, 
                 num_timeframes: int, 
                 d_model: int = 128, 
                 nhead: int = 8, 
                 num_layers: int = 4, 
                 dim_feedforward: int = 512, 
                 dropout: float = 0.1,
                 max_seq_len: int = 100):
        super().__init__()
        self.d_model = d_model
        
        # Feature Projection
        self.feature_projection = nn.Linear(num_features, d_model)
        
        # Embeddings
        self.symbol_embedding = nn.Embedding(num_symbols, d_model)
        self.timeframe_embedding = nn.Embedding(num_timeframes, d_model)
        
        self.pos_encoding = PositionalEncoding(d_model, max_seq_len)
        
        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, 
            nhead=nhead, 
            dim_feedforward=dim_feedforward, 
            dropout=dropout,
            batch_first=True,
            norm_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Multi-Horizon Heads (Predicts t+1, t+3, t+5 log returns)
        self.return_head = nn.Linear(d_model, 3) 
        
        # Volatility Head (Target Volatility)
        self.vol_head = nn.Linear(d_model, 1)
        
        # Quantile Head (Predicts 5%, 25%, 50%, 75%, 95% quantiles for t+1)
        self.quantile_head = nn.Linear(d_model, 5)

    def forward(self, 
                x_features: torch.Tensor, 
                symbol_idx: torch.Tensor, 
                timeframe_idx: torch.Tensor,
                src_mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Args:
            x_features: [batch, seq_len, num_features]
            symbol_idx: [batch]
            timeframe_idx: [batch]
        Returns:
            returns: [batch, 3] (t+1, t+3, t+5)
            volatility: [batch, 1]
            quantiles: [batch, 5]
        """
        # 1. Project features
        x = self.feature_projection(x_features) # [batch, seq_len, d_model]
        
        # 2. Add embeddings
        # Broadcast embeddings across sequence
        s_emb = self.symbol_embedding(symbol_idx).unsqueeze(1) # [batch, 1, d_model]
        t_emb = self.timeframe_embedding(timeframe_idx).unsqueeze(1) # [batch, 1, d_model]
        
        x = x + s_emb + t_emb
        
        # 3. Add Positional Encoding
        x = self.pos_encoding(x)
        
        # 4. Transformer Encoder
        # Use causal masking if needed (for price sequence, we usually want each step to only see past)
        # But for encoder-only prediction of the LAST step, we just use the whole sequence.
        output = self.transformer_encoder(x, src_mask) # [batch, seq_len, d_model]
        
        # 5. Extract latest representation (last step)
        latest_rep = output[:, -1, :] # [batch, d_model]
        
        # 6. Heads
        returns = self.return_head(latest_rep)
        volatility = F.softplus(self.vol_head(latest_rep))
        quantiles = self.quantile_head(latest_rep)
        
        return returns, volatility, quantiles

def get_model_size(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
