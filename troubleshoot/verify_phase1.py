import asyncio
import logging
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from backend.services.feature_store_orchestrator import get_feature_orchestrator
from backend.services.feature_store import get_feature_store

async def main():
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = get_feature_orchestrator(version="v1_test")
    store = get_feature_store()
    
    print("🚀 Starting Feature Store Verification...")
    
    # Process only 1d for speed in testing
    # We only process a few symbols by limiting the loop in the orchestrator if needed, 
    # but here we'll just let it run for a bit.
    
    try:
        # Run incremental update
        await orchestrator.process_incremental_updates(timeframes=["1d"])
        
        print("\n📊 Checking Feature Store Content...")
        df = store.query_features(feature_version="v1_test")
        
        if not df.empty:
            print(f"✅ Success! Found {len(df)} feature rows in Parquet.")
            print("\nSample Data:")
            print(df[['timestamp', 'symbol', 'timeframe', 'rsi_14', 'target_return_1']].head())
            
            # Check partitioning
            print("\nPartitions created:")
            base_test = os.path.join("backend", "data", "feature_store", "feature_version=v1_test")
            for root, dirs, files in os.walk(base_test):
                if files:
                    print(f" - {root}: {files}")
        else:
            print("❌ Failure: Feature Store is empty.")
            
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
