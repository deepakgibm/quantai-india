import torch
import numpy as np
import pandas as pd
import logging
from torch.utils.data import Dataset, DataLoader
from typing import List
from ml.metadata_utils import SymbolMapper, TIMEFRAME_TO_IDX

class QuantAIDataset(Dataset):
    """
    DL Dataset that loads from Feature Store Parquet files.
    Optimized to use vectorized index calculation instead of list of dicts.
    """
    def __init__(self, 
                 df: pd.DataFrame, 
                 seq_len: int = 50, 
                 feature_cols: List[str] = None):
        self.seq_len = seq_len
        self.mapper = SymbolMapper()
        
        # Standard features to use (must match what's in FeaturePipeline)
        self.feature_cols = feature_cols or [
            'log_return', 'volatility_20', 'rsi_14', 
            'macd_line', 'macd_signal', 'macd_hist',
            'bb_pct_b', 'atr_14_pct', 'adx_14', 
            'plus_di', 'minus_di', 'volume_ratio_20'
        ]
        
        # Drop rows with NaNs in features or targets
        initial_len = len(df)
        df = df.dropna(subset=self.feature_cols + ['target_return_1', 'target_return_3', 'target_return_5', 'volatility_20'])
        dropped = initial_len - len(df)
        
        # Ensure data is sorted
        df = df.sort_values(['symbol', 'timeframe', 'timestamp'])
        
        # Convert to numpy arrays for performance
        self.features = df[self.feature_cols].values.astype(np.float32)
        self.labels = df[['target_return_1', 'target_return_3', 'target_return_5', 'volatility_20']].values.astype(np.float32)
        
        # Pre-map IDs
        self.symbol_array = df['symbol'].apply(self.mapper.get_idx).values.astype(np.int64)
        self.tf_array = df['timeframe'].apply(lambda x: TIMEFRAME_TO_IDX.get(x, 6)).values.astype(np.int64)
        
        # Vectorized valid index calculation
        # A sequence starting at i is valid if the group (symbol+tf) doesn't change for seq_len steps
        group_id = df.groupby(['symbol', 'timeframe']).ngroup().values
        is_valid = (group_id[:-seq_len+1] == group_id[seq_len-1:])
        self.valid_indices = np.where(is_valid)[0]
        
        logger = logging.getLogger(__name__)
        logger.info(f"Created Optimized QuantAIDataset with {len(self.valid_indices)} samples.")

    def __len__(self):
        return len(self.valid_indices)

    def __getitem__(self, idx):
        start_idx = self.valid_indices[idx]
        end_idx = start_idx + self.seq_len
        
        x = self.features[start_idx : end_idx]
        y = self.labels[end_idx - 1]
        
        return (
            torch.from_numpy(x),
            torch.tensor(self.symbol_array[end_idx - 1], dtype=torch.long),
            torch.tensor(self.tf_array[end_idx - 1], dtype=torch.long),
            torch.from_numpy(y[:3]),
            torch.from_numpy(y[3:])
        )

def get_dataloader(df: pd.DataFrame, batch_size: int = 64, seq_len: int = 50, shuffle: bool = True):
    dataset = QuantAIDataset(df, seq_len=seq_len)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
