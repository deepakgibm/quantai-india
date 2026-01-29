import asyncio
import logging
import sys
import os
import pandas as pd
import torch

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from backend.services.feature_store import get_feature_store
from backend.ml.dataset import get_dataloader
from backend.ml.trainer import QuantAITrainer
from backend.ml.algorithm_registry import get_algorithm_registry

async def train_sample_model():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    store = get_feature_store()
    
    print("🚀 Phase 2: Loading data for Deep Learning training...")
    # Load data from v1_test (created in Phase 1)
    df = store.query_features(feature_version="v1_test")
    
    if df.empty:
        print("❌ Error: No features found in Feature Store. Run Phase 1 verification first.")
        return False
        
    print(f"📊 Loaded {len(df)} feature rows for {df['symbol'].nunique()} symbols.")
    
    # Initialize Trainer
    num_features = 12
    num_symbols = 1000
    num_timeframes = 8
    
    trainer = QuantAITrainer(num_features, num_symbols, num_timeframes)
    
    # Create DataLoader
    dataloader = get_dataloader(df, batch_size=32, seq_len=50)
    
    print("🏋️ Starting training (3 epochs for verification)...")
    for epoch in range(1, 4):
        loss = trainer.train_epoch(dataloader)
        print(f"Epoch {epoch}/3 - Loss: {loss:.6f}")
        
    trainer.save_model()
    print("✅ Model trained and saved.")
    return True

async def verify_inference():
    print("\n🔍 Verifying Inference via AlgorithmRegistry...")
    registry = get_algorithm_registry()
    
    # Get some sample data again
    store = get_feature_store()
    df = store.query_features(feature_version="v1_test")
    
    # Filter for one symbol/timeframe
    sample_symbol = df['symbol'].iloc[0]
    sample_df = df[df['symbol'] == sample_symbol].sort_values('timestamp').tail(100)
    
    # Needs close, timestamp for the predict method
    # Since we queried from Parquet, it should have them
    
    try:
        predicted, upper, lower, confidence = registry.get("transformer_informer_dl").predict(
            sample_df, horizon=5
        )
        
        print(f"✅ Inference Success for {sample_symbol}!")
        print(f"Confidence: {confidence}")
        print(f"Predictions: {predicted}")
        print(f"Upper Band: {upper}")
        print(f"Lower Band: {lower}")
        
    except Exception as e:
        print(f"❌ Inference Failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    if await train_sample_model():
        await verify_inference()

if __name__ == "__main__":
    asyncio.run(main())
