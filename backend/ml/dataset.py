import torch
import numpy as np
import pandas as pd
import logging
from torch.utils.data import Dataset, DataLoader
from typing import List
from backend.ml.metadata_utils import SymbolMapper, TIMEFRAME_TO_IDX

class QuantAIDataset(Dataset):
    """
    DL Dataset that loads from Feature Store Parquet files.
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
        
        # Data pre-processing: Group by symbol and timeframe to create sequences
        self.sequences = []
        
        for (symbol, timeframe), group in df.groupby(['symbol', 'timeframe']):
            group = group.sort_values('timestamp')
            
            # Convert to numpy for performance
            features = group[self.feature_cols].values.astype(np.float32)
            # Labels (t+1, t+3, t+5 returns and volatility)
            labels = group[['target_return_1', 'target_return_3', 'target_return_5', 'volatility_20']].values.astype(np.float32)
            
            symbol_idx = self.mapper.get_idx(symbol)
            tf_idx = TIMEFRAME_TO_IDX.get(timeframe, 6) # Default 1d
            
            # Create windowed sequences
            for i in range(len(group) - seq_len):
                x = features[i : i+seq_len]
                y = labels[i+seq_len-1] # Label for the current step (or next step depending on pipeline lag)
                
                # In our pipeline: target_return_1 is shift(-1), so labels[i+seq_len-1] 
                # corresponds to the prediction for the bar AFTER the sequence ends.
                
                self.sequences.append({
                    'x': x,
                    'y_returns': y[:3],
                    'y_vol': y[3:], # volatility_20
                    'symbol_idx': symbol_idx,
                    'tf_idx': tf_idx
                })
        
        logger = logging.getLogger(__name__)
        logger.info(f"Created QuantAIDataset with {len(self.sequences)} samples.")

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        item = self.sequences[idx]
        return (
            torch.from_numpy(item['x']),
            torch.tensor(item['symbol_idx'], dtype=torch.long),
            torch.tensor(item['tf_idx'], dtype=torch.long),
            torch.from_numpy(item['y_returns']),
            torch.from_numpy(item['y_vol'])
        )

def get_dataloader(df: pd.DataFrame, batch_size: int = 64, seq_len: int = 50, shuffle: bool = True):
    dataset = QuantAIDataset(df, seq_len=seq_len)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
