import os
import sys
import pandas as pd

# Add project root to path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "backend"))

from backend.services.feature_store import get_feature_store

def debug_data():
    store = get_feature_store()
    df = store.query_features(feature_version="v1")
    
    print(f"Total rows: {len(df)}")
    if df.empty:
        print("Empty DataFrame!")
        return
        
    print(f"Columns: {df.columns.tolist()}")
    print(f"Head:\n{df.head(2)}")
    
    # Check groups
    groups = df.groupby(['symbol', 'timeframe']).size()
    print(f"Number of groups: {len(groups)}")
    print(f"Average group size: {groups.mean()}")
    print(f"Min group size: {groups.min()}")
    
    # Check if target columns are present
    target_cols = ['target_return_1', 'target_return_3', 'target_return_5']
    missing = [c for c in target_cols if c not in df.columns]
    if missing:
        print(f"Missing target columns: {missing}")
    else:
        print("All target columns present.")

if __name__ == "__main__":
    debug_data()
