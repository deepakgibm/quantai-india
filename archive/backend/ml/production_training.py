import asyncio
import logging
import sys
import os
from datetime import datetime

import json

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "backend"))

from services.feature_store import get_feature_store
from ml.dataset import get_dataloader
from ml.trainer import QuantAITrainer

STATUS_FILE = os.path.join(root_dir, "data", "ml_status.json")

# Safe PyTorch import
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

def is_market_open():
    """Checks if the Indian market is currently open (09:15 - 15:30 IST)."""
    now = datetime.now()
    if now.weekday() >= 5: return False
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return start <= now <= end

def update_status(data: dict):
    """Writes training status to a JSON file for the UI to poll."""
    try:
        data['last_update'] = datetime.now().isoformat()
        with open(STATUS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Status update failed: {e}")

async def run_production_training(epochs: int = 10, batch_size: int = 64):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ProdTraining")
    
    # 0. Check PyTorch availability
    if not TORCH_AVAILABLE:
        logger.error("❌ PyTorch not installed. Run: pip install torch")
        update_status({
            "stage": "error",
            "reason": "PyTorch not installed. Install with: pip install torch",
            "last_update": datetime.now().isoformat()
        })
        return

    store = get_feature_store()
    
    logger.info("📡 Loading full market features for training...")
    # Load all data from production v1
    df = store.query_features(feature_version="v1")
    
    if df.empty:
        logger.error("❌ No training data found in v1 Feature Store. Please run backfill first.")
        return
        
    logger.info(f"📊 Loaded {len(df)} rows across {df['symbol'].nunique()} symbols.")
    
    # 1. Chronological Train/Val Split
    df = df.sort_values('timestamp')
    # Use 90/10 split for small datasets
    split_idx = int(len(df) * 0.9)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]
    
    logger.info(f"✂️ Split: Train={len(train_df)}, Val={len(val_df)}")
    
    # Recommended seq_len for this dataset size
    seq_len = 30
    
    # 2. Setup DataLoaders
    train_loader = get_dataloader(train_df, batch_size=batch_size, seq_len=seq_len, shuffle=True)
    val_loader = get_dataloader(val_df, batch_size=batch_size, seq_len=seq_len, shuffle=False)
    
    if len(train_loader) == 0:
        logger.error("❌ Train loader is empty. Need more data or smaller seq_len.")
        return
        
    if len(val_loader) == 0:
        logger.warning("⚠️ Val loader is empty. Falling back to training on full dataset without validation.")
        val_loader = None
    
    # 3. Initialize Trainer
    trainer = QuantAITrainer(
        num_features=12,
        num_symbols=1000, # Embedding space
        num_timeframes=8
    )
    
    logger.info(f"🚀 Starting training on {trainer.device}...")
    logger.info(f"📝 Status will be written to: {STATUS_FILE}")
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    
    best_loss = float('inf')
    
    try:
        for epoch in range(1, epochs + 1):
            # 0. Market Hours Safety Check (optional - warn but don't stop)
            if is_market_open():
                logger.warning("⚠️ Market is OPEN. Training may impact inference latency.")

            # Training
            train_loss = trainer.train_epoch(train_loader)
            
            # Validation
            avg_val_loss = train_loss # Default if no validation
            if val_loader:
                val_loss = 0
                trainer.model.eval()
                with torch.no_grad():
                    for batch in val_loader:
                        x, s_idx, t_idx, y_ret, y_vol = [b.to(trainer.device) for b in batch]
                        ret_pred, vol_pred, q_pred = trainer.model(x, s_idx, t_idx)
                        
                        # Multi-objective validation loss
                        loss_ret = trainer.mse_loss(ret_pred, y_ret)
                        loss_vol = trainer.mse_loss(vol_pred, y_vol)
                        loss_q = trainer.quantile_loss(q_pred, y_ret[:, 0:1], [0.05, 0.25, 0.5, 0.75, 0.95])
                        
                        loss = loss_ret + 0.1 * loss_vol + 0.5 * loss_q
                        val_loss += loss.item()
                
                avg_val_loss = val_loss / len(val_loader)
            
            logger.info(f"Epoch {epoch}/{epochs} | Train Loss: {train_loss:.6f} | Val Loss: {avg_val_loss:.6f}")
            
            # Update UI Status
            update_status({
                "stage": "running",
                "epoch": epoch,
                "total_epochs": epochs,
                "train_loss": train_loss,
                "val_loss": avg_val_loss,
                "best_loss": min(best_loss, avg_val_loss)
            })

            # Save best model
            if avg_val_loss < best_loss:
                best_loss = avg_val_loss
                trainer.save_model()
                logger.info("💾 New best model saved.")
                
    except KeyboardInterrupt:
        logger.info("🛑 Training stopped manually.")
        update_status({
            "stage": "stopped",
            "reason": "Manual Stop",
            "epoch": epoch,
            "best_loss": best_loss
        })

    logger.info("✅ Training session ended.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch", type=int, default=64)
    args = parser.parse_args()
    
    asyncio.run(run_production_training(epochs=args.epochs, batch_size=args.batch))
