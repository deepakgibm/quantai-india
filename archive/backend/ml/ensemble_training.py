"""
Ensemble Training Script (No PyTorch Required)

Trains APF Ensemble models (XGBoost + Ridge) per symbol using
Parquet Feature Store data. Updates ml_status.json for UI polling.

Usage:
    python -m ml.ensemble_training --epochs 5 --batch 64
    python ml/ensemble_training.py --symbols RELIANCE TCS
"""

import asyncio
import logging
import sys
import os
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
# Also add parent of root_dir in case the script is inside backend/ml/
sys.path.insert(0, os.path.dirname(root_dir))

# Import with fallback for Docker vs local paths
try:
    from ml.ensemble import APFEnsemble
    from ml.feature_builder import FeatureBuilder
except ImportError:
    # If not running as module
    from ensemble import APFEnsemble
    from feature_builder import FeatureBuilder

STATUS_FILE = os.path.join(root_dir, "data", "ml_status.json")
# In Docker, the API writes to /data/ml_status.json (different from /app/data/)
# Always prefer /data/ml_status.json if it exists (matches the API)
if os.path.exists("/data/ml_status.json"):
    STATUS_FILE = "/data/ml_status.json"
elif os.path.isdir("/data") and not os.path.exists(STATUS_FILE):
    STATUS_FILE = "/data/ml_status.json"

logger = logging.getLogger("EnsembleTraining")


def update_status(data: dict):
    """Writes training status to a JSON file for the UI to poll."""
    try:
        data['last_update'] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        with open(STATUS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Status update failed: {e}")


def load_candle_data_from_parquet(data_dir: str = None) -> pd.DataFrame:
    """
    Load OHLCV data from the Parquet feature store for training.
    Falls back to reading raw candle data if feature store is unavailable.
    """
    if data_dir is None:
        # Check Docker mount first, then local
        if os.path.isdir("/data/feature_store"):
            data_dir = "/data/feature_store"
        else:
            data_dir = os.path.join(root_dir, "data", "feature_store")
    
    # Try DuckDB for fast parquet reading
    try:
        import duckdb
        db = duckdb.connect(database=':memory:')
        
        parquet_path = os.path.join(data_dir, "**", "*.parquet")
        query = f"""
            SELECT * FROM read_parquet('{parquet_path}', hive_partitioning=1)
            ORDER BY symbol, timeframe, timestamp
        """
        df = db.execute(query).df()
        db.close()
        
        if not df.empty:
            logger.info(f"Loaded {len(df)} rows from Feature Store ({df['symbol'].nunique()} symbols)")
            return df
    except Exception as e:
        logger.warning(f"DuckDB load failed: {e}")
    
    return pd.DataFrame()


def train_ensemble_models(
    symbols_filter: list = None,
    timeframes_filter: list = None,
    epochs: int = 1,  # For ensemble, "epochs" means full passes over train set (not really used, for UI compat)
):
    """
    Train APF Ensemble models (XGBoost + Ridge) for each symbol-timeframe combination.
    Updates ml_status.json for the training UI.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    update_status({
        "stage": "loading",
        "reason": "Loading data from Feature Store...",
        "epoch": 0,
        "total_epochs": epochs,
        "train_loss": 0.0,
        "val_loss": 0.0,
        "best_loss": 0.0,
    })
    
    # Load data
    df = load_candle_data_from_parquet()
    
    if df.empty:
        logger.error("No data found in Feature Store!")
        update_status({
            "stage": "error",
            "reason": "No training data in Feature Store. Run the feature pipeline first.",
            "train_loss": 0.0,
            "val_loss": 0.0,
            "best_loss": 0.0,
        })
        return
    
    # Determine symbol-timeframe combinations
    required_cols = {'open', 'high', 'low', 'close', 'volume'}
    available_cols = set(df.columns)
    
    if not required_cols.issubset(available_cols):
        logger.error(f"Missing required OHLCV columns. Available: {available_cols}")
        update_status({
            "stage": "error",
            "reason": f"Missing columns: {required_cols - available_cols}",
        })
        return
    
    # Get all symbol-timeframe combos
    combos = df.groupby(['symbol', 'timeframe']).size().reset_index(name='count')
    combos = combos[combos['count'] >= 30]  # Need at least 30 rows for training
    
    if symbols_filter:
        combos = combos[combos['symbol'].isin(symbols_filter)]
    if timeframes_filter:
        combos = combos[combos['timeframe'].isin(timeframes_filter)]
    
    total_combos = len(combos)
    logger.info(f"Training {total_combos} symbol-timeframe combinations")
    
    if total_combos == 0:
        update_status({
            "stage": "error",
            "reason": "No symbol-timeframe combinations with enough data (need 50+ rows).",
        })
        return
    
    feature_builder = FeatureBuilder()
    
    all_train_mse = []
    all_val_mse = []
    best_overall_loss = float('inf')
    models_trained = 0
    errors = []
    
    for epoch in range(1, epochs + 1):
        epoch_train_losses = []
        epoch_val_losses = []
        
        for idx, (_, row) in enumerate(combos.iterrows()):
            symbol = row['symbol']
            timeframe = row['timeframe']
            
            try:
                # Get data for this symbol-timeframe
                mask = (df['symbol'] == symbol) & (df['timeframe'] == timeframe)
                sym_df = df[mask].sort_values('timestamp').copy()
                
                if len(sym_df) < 30:
                    continue
                
                # Build features
                features_df = feature_builder.build_features(sym_df)
                if features_df is None or len(features_df) < 15:
                    continue
                
                X, y, _ = feature_builder.get_feature_matrix(sym_df)
                if X is None or len(X) < 15:
                    continue
                
                # Train/Val split (80/20)
                split = int(len(X) * 0.8)
                X_train, X_val = X[:split], X[split:]
                y_train, y_val = y[:split], y[split:]
                
                # Train ensemble
                ensemble = APFEnsemble(symbol=symbol, timeframe=timeframe)
                metrics = ensemble.train(X_train, y_train, feature_names=feature_builder.feature_names)
                
                # Validate
                pred, upper, lower, confidence = ensemble.predict(X_val)
                val_mse = float(np.mean((pred - y_val) ** 2))
                train_mse = metrics.get("ridge_mse", 0.0)
                if metrics.get("xgb_mse") is not None:
                    train_mse = 0.6 * metrics["xgb_mse"] + 0.4 * metrics["ridge_mse"]
                
                epoch_train_losses.append(train_mse)
                epoch_val_losses.append(val_mse)
                
                # Save model
                ensemble.save()
                models_trained += 1
                
                # Update status periodically (every 10 symbols)
                if (idx + 1) % 10 == 0 or idx == total_combos - 1:
                    avg_train = float(np.mean(epoch_train_losses)) if epoch_train_losses else 0.0
                    avg_val = float(np.mean(epoch_val_losses)) if epoch_val_losses else 0.0
                    best_overall_loss = min(best_overall_loss, avg_val) if avg_val > 0 else best_overall_loss
                    
                    update_status({
                        "stage": "running",
                        "epoch": epoch,
                        "total_epochs": epochs,
                        "train_loss": avg_train,
                        "val_loss": avg_val,
                        "best_loss": best_overall_loss if best_overall_loss != float('inf') else 0.0,
                        "models_trained": models_trained,
                        "total_models": total_combos,
                        "current_symbol": f"{symbol}/{timeframe}",
                        "reason": f"Training {idx+1}/{total_combos} ({symbol}/{timeframe})",
                    })
                    
            except Exception as e:
                errors.append(f"{symbol}/{timeframe}: {str(e)[:100]}")
                logger.warning(f"Failed {symbol}/{timeframe}: {e}")
                continue
        
        # Epoch summary
        avg_train = float(np.mean(epoch_train_losses)) if epoch_train_losses else 0.0
        avg_val = float(np.mean(epoch_val_losses)) if epoch_val_losses else 0.0
        best_overall_loss = min(best_overall_loss, avg_val) if avg_val > 0 else best_overall_loss
        
        all_train_mse.append(avg_train)
        all_val_mse.append(avg_val)
        
        logger.info(f"Epoch {epoch}/{epochs} | Train MSE: {avg_train:.6f} | Val MSE: {avg_val:.6f} | Models: {models_trained}")
    
    # Final status
    final_train = float(np.mean(all_train_mse)) if all_train_mse else 0.0
    final_val = float(np.mean(all_val_mse)) if all_val_mse else 0.0
    
    update_status({
        "stage": "completed",
        "epoch": epochs,
        "total_epochs": epochs,
        "train_loss": final_train,
        "val_loss": final_val,
        "best_loss": best_overall_loss if best_overall_loss != float('inf') else 0.0,
        "models_trained": models_trained,
        "errors": len(errors),
        "reason": f"Training complete! {models_trained} models trained.",
    })
    
    logger.info(f"\n{'='*50}")
    logger.info(f"TRAINING COMPLETED")
    logger.info(f"{'='*50}")
    logger.info(f"Models trained: {models_trained}")
    logger.info(f"Final Train MSE: {final_train:.6f}")
    logger.info(f"Final Val MSE: {final_val:.6f}")
    logger.info(f"Errors: {len(errors)}")
    if errors:
        for e in errors[:5]:
            logger.info(f"  - {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train APF Ensemble models (XGBoost + Ridge)")
    parser.add_argument("--epochs", type=int, default=1, help="Number of passes (default: 1)")
    parser.add_argument("--batch", type=int, default=64, help="Batch size (unused, for API compat)")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to train (e.g., RELIANCE TCS)")
    parser.add_argument("--timeframes", nargs="+", help="Specific timeframes (e.g., 15m 1d)")
    
    args = parser.parse_args()
    
    train_ensemble_models(
        symbols_filter=args.symbols,
        timeframes_filter=args.timeframes,
        epochs=args.epochs,
    )
