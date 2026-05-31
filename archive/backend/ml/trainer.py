import torch
import torch.nn as nn
import torch.optim as optim
import logging
import os
from typing import List
from ml.transformer_model import QuantAIInformer

logger = logging.getLogger(__name__)

class QuantAITrainer:
    """
    Handles training and evaluation of the QuantAI Informer model.
    """
    def __init__(self, 
                 num_features: int, 
                 num_symbols: int, 
                 num_timeframes: int,
                 model_path: str = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = QuantAIInformer(
            num_features=num_features,
            num_symbols=num_symbols,
            num_timeframes=num_timeframes
        ).to(self.device)
        
        self.model_path = model_path or os.path.join("models", "transformer_v1.pt")
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        self.optimizer = optim.AdamW(self.model.parameters(), lr=1e-4, weight_decay=1e-5)
        self.mse_loss = nn.MSELoss()
        
    def quantile_loss(self, preds: torch.Tensor, target: torch.Tensor, quantiles: List[float]) -> torch.Tensor:
        """
        Pinball loss for quantile regression.
        preds: [batch, len(quantiles)]
        target: [batch, 1]
        """
        loss = 0
        for i, q in enumerate(quantiles):
            errors = target - preds[:, i:i+1]
            loss += torch.max((q - 1) * errors, q * errors).mean()
        return loss / len(quantiles)

    def train_epoch(self, dataloader, callback=None):
        import time
        torch.set_num_threads(1) # Prevent core contention on 2.0 limit
        self.model.train()
        total_loss = 0
        total_batches = len(dataloader)
        
        epoch_start = time.time()
        for i, batch in enumerate(dataloader):
            batch_start = time.time()
            x, s_idx, t_idx, y_ret, y_vol = [b.to(self.device) for b in batch]
            
            self.optimizer.zero_grad()
            
            ret_pred, vol_pred, q_pred = self.model(x, s_idx, t_idx)
            
            # 1. Prediction Loss (Multi-horizon returns)
            loss_ret = self.mse_loss(ret_pred, y_ret) # t+1, t+3, t+5
            
            # 2. Volatility Loss
            loss_vol = self.mse_loss(vol_pred, y_vol)
            
            # 3. Quantile Loss
            quantiles = [0.05, 0.25, 0.5, 0.75, 0.95]
            loss_q = self.quantile_loss(q_pred, y_ret[:, 0:1], quantiles)
            
            loss = loss_ret + 0.1 * loss_vol + 0.5 * loss_q
            
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            
            # Diagnostic logging every 10 batches
            if (i + 1) % 10 == 0:
                logger.info(f"   [Batch {i+1}/{total_batches}] Loss: {loss.item():.6f} | Batch Time: {time.time() - batch_start:.3f}s")
            
            if callback:
                callback(i + 1, total_batches, loss.item())
            
        logger.info(f"✨ Epoch completed in {time.time() - epoch_start:.2f}s")
        return total_loss / total_batches

    def save_model(self):
        torch.save(self.model.state_dict(), self.model_path)
        logger.info(f"Model saved to {self.model_path}")

    def load_model(self):
        if os.path.exists(self.model_path):
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            logger.info("Model loaded successfully.")
            return True
        return False
        
    def predict_latest(self, x: torch.Tensor, s_idx: int, t_idx: int):
        """
        Inference on a single sample or batch.
        """
        self.model.eval()
        with torch.no_grad():
            x = x.to(self.device).unsqueeze(0) if x.dim() == 2 else x.to(self.device)
            s_idx = torch.tensor([s_idx]).to(self.device)
            t_idx = torch.tensor([t_idx]).to(self.device)
            
            returns, vol, quantiles = self.model(x, s_idx, t_idx)
            return returns.cpu().numpy(), vol.cpu().numpy(), quantiles.cpu().numpy()
