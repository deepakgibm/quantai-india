"""
ML Training Celery Tasks

Replaces the subprocess-based training pattern in api/ml_training.py.
Training runs as a Celery worker task with progress published to DragonflyDB.
"""

import os
import json
import logging
from datetime import datetime
from celery import current_task

from celery_app import celery_app

logger = logging.getLogger(__name__)

# Resolve paths
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
_STATUS_FILE = os.path.join(_PROJECT_ROOT, "data", "ml_status.json")

import math

def _sanitize_metrics(metrics: dict):
    """Ensure metrics are JSON compliant (handles NaN and Infinity)."""
    for key, value in metrics.items():
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                metrics[key] = 0.0
    return metrics

def _update_status(data: dict):
    """Write status to JSON file (backward compatible with UI polling)."""
    try:
        data = _sanitize_metrics(data)
        data["last_update"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(_STATUS_FILE), exist_ok=True)
        with open(_STATUS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning(f"Status file write failed: {e}")


def _publish_progress(stage: str, epoch: int = 0, total_epochs: int = 0, 
                      train_loss: float = 0.0, val_loss: float = 0.0, 
                      best_loss: float = 0.0, **extra):
    """Publish progress to both Celery task state and DragonflyDB."""
    meta = {
        "stage": stage,
        "epoch": epoch,
        "total_epochs": total_epochs,
        "train_loss": train_loss,
        "val_loss": val_loss,
        "best_loss": best_loss,
        "last_update": datetime.now().isoformat(),
        **extra,
    }
    
    # Update Celery task state (queryable via AsyncResult)
    if current_task:
        current_task.update_state(state="PROGRESS", meta=meta)
    
    # Also write to status file for backward compatibility
    _update_status(meta)
    
    logger.info(f"Published training progress: stage={stage}, epoch={epoch}/{total_epochs}")
    
    # Publish to DragonflyDB for real-time WebSocket push
    try:
        from services.dragonfly_client import get_cache
        cache = get_cache()
        if cache.is_available():
            cache.set("qai:ml:training:progress", json.dumps(meta), ttl=3600)
            # Pub/Sub channel for real-time listeners
            cache._client.publish("qai:ml:training:events", json.dumps(meta))
    except Exception as e:
        logger.debug(f"Cache publish side-effect failed: {e}")


@celery_app.task(
    bind=True,
    name="tasks.ml_tasks.train_model",
    soft_time_limit=14400,  # 4 hours soft limit for training
    time_limit=18000,       # 5 hours hard kill
    max_retries=0,          # Training should not auto-retry
    acks_late=True,
)
def train_model(self, epochs: int = 10, batch_size: int = 64):
    """
    Run ML model training as a Celery task.
    
    Replaces the subprocess.Popen pattern from api/ml_training.py.
    Progress is published to DragonflyDB for real-time UI updates.
    
    Args:
        epochs: Number of training epochs
        batch_size: Batch size for SGD
        
    Returns:
        dict with training results
    """
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting ML training: epochs={epochs}, batch={batch_size}")
    
    _publish_progress("starting", total_epochs=epochs)
    
    if not settings.ENABLE_AI_FEATURES:
        logger.warning(f"[Task {task_id}] ML training requested but ENABLE_AI_FEATURES is false.")
        _publish_progress("error", reason="ML Training is disabled (Project Aegis Safe Mode)")
        return {"status": "error", "reason": "AI features disabled"}

    try:
        # Import training dependencies (heavy imports inside task)
        from services.feature_store import get_feature_store
        
        store = get_feature_store()
        logger.info(f"[Task {task_id}] Querying features from store...")
        df = store.query_features(feature_version="v1")
        
        if df.empty:
            _publish_progress("error", reason="No training data found in v1 Feature Store")
            return {"status": "error", "reason": "No training data"}
        
        logger.info(f"[Task {task_id}] Loaded {len(df)} rows across {df['symbol'].nunique()} symbols")
        
        # Check for PyTorch
        try:
            import torch
        except ImportError:
            _publish_progress("error", reason="PyTorch not installed")
            return {"status": "error", "reason": "PyTorch not installed"}
        
        from ml.dataset import get_dataloader
        from ml.trainer import QuantAITrainer
        
        # Chronological train/val split
        df = df.sort_values("timestamp")
        split_idx = int(len(df) * 0.9)
        train_df = df.iloc[:split_idx]
        val_df = df.iloc[split_idx:]
        
        seq_len = 30
        train_loader = get_dataloader(train_df, batch_size=batch_size, seq_len=seq_len, shuffle=True)
        val_loader = get_dataloader(val_df, batch_size=batch_size, seq_len=seq_len, shuffle=False)
        
        if len(train_loader) == 0:
            logger.error(f"[Task {task_id}] Train loader is empty. Dataframe size: {len(train_df)}")
            _publish_progress("error", reason="Train loader empty")
            return {"status": "error", "reason": "Insufficient training data"}
        
        if len(val_loader) == 0:
            val_loader = None
        
        # Initialize trainer
        trainer = QuantAITrainer(num_features=12, num_symbols=1000, num_timeframes=8)
        
        _publish_progress("running", epoch=0, total_epochs=epochs)
        
        best_loss = float("inf")
        
        for epoch in range(1, epochs + 1):
            def batch_callback(batch, total, loss):
                # Only publish every 10% of batches to avoid overwhelming the status file
                if batch % max(1, (total // 10)) == 0 or batch == total:
                    perc = int((batch / total) * 100)
                    _publish_progress(
                        f"training {perc}%", 
                        epoch=epoch, 
                        total_epochs=epochs,
                        train_loss=loss, # Show current batch loss as preview
                        best_loss=best_loss
                    )

            # Training epoch logic...
            train_loss = trainer.train_epoch(train_loader, callback=batch_callback)
            
            # Validation
            avg_val_loss = train_loss
            if val_loader:
                val_loss = 0
                trainer.model.eval()
                with torch.no_grad():
                    for batch in val_loader:
                        x, s_idx, t_idx, y_ret, y_vol = [b.to(trainer.device) for b in batch]
                        ret_pred, vol_pred, q_pred = trainer.model(x, s_idx, t_idx)
                        loss_ret = trainer.mse_loss(ret_pred, y_ret)
                        loss_vol = trainer.mse_loss(vol_pred, y_vol)
                        loss_q = trainer.quantile_loss(q_pred, y_ret[:, 0:1], [0.05, 0.25, 0.5, 0.75, 0.95])
                        loss = loss_ret + 0.1 * loss_vol + 0.5 * loss_q
                        val_loss += loss.item()
                avg_val_loss = val_loss / len(val_loader)
            
            logger.info(f"[Task {task_id}] Epoch {epoch}/{epochs} | Train: {train_loss:.6f} | Val: {avg_val_loss:.6f}")
            
            if avg_val_loss < best_loss:
                best_loss = avg_val_loss
                trainer.save_model()
                logger.info(f"[Task {task_id}] New best model saved (loss={best_loss:.6f})")

            _publish_progress(
                "running", epoch=epoch, total_epochs=epochs,
                train_loss=train_loss, val_loss=avg_val_loss,
                best_loss=best_loss,
            )
        
        _publish_progress("completed", epoch=epochs, total_epochs=epochs,
                         train_loss=train_loss, val_loss=avg_val_loss, best_loss=best_loss)
        
        return {
            "status": "completed",
            "epochs": epochs,
            "best_loss": best_loss,
            "final_train_loss": train_loss,
            "final_val_loss": avg_val_loss,
        }
        
    except Exception as e:
        logger.error(f"[Task {task_id}] Training failed: {e}", exc_info=True)
        _publish_progress("error", reason=str(e))
        raise  # Let Celery mark as FAILURE
