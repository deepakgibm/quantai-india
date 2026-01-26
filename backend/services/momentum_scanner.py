"""
Momentum Scanner Service (Vectorized)
Finds stocks with strong price momentum using ROC and MFI indicators.
Optimized: Uses vectorized Pandas operations for <2s latency.
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta
from database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class MomentumScanner:
    """
    Momentum-based stock scanner (Vectorized).
    
    Indicators:
    - ROC (Rate of Change) - Price momentum
    - MFI (Money Flow Index) - Volume-weighted momentum
    - RSI acceleration - Momentum of momentum
    
    Optimization: Vectorized calculation on full dataset.
    """
    
    def __init__(self):
        self._Session = SessionLocal
        self.min_score = 60
        # Precomputed check logic removed/simplified as vectorization is fast enough
        # But we can keep it if needed. For now, vectorization is the priority refactor.
        self._use_precomputed = False 
    
    def _get_bulk_ohlcv_df(self, days: int = 60) -> pd.DataFrame:
        """Fetch OHLCV data for ALL symbols in one query as a single DataFrame."""
        try:
            from models_ml import Nifty100Daily
            
            session = self._Session()
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # Bulk query
                query = session.query(
                    Nifty100Daily.symbol,
                    Nifty100Daily.timestamp,
                    Nifty100Daily.open,
                    Nifty100Daily.high,
                    Nifty100Daily.low,
                    Nifty100Daily.close,
                    Nifty100Daily.volume
                ).filter(
                    Nifty100Daily.timestamp >= cutoff_date
                ).statement
                
                df = pd.read_sql(query, session.bind)

                if df.empty:
                    return pd.DataFrame()
                
                # Ensure correct types
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['close'] = df['close'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['volume'] = df['volume'].astype(float)

                return df
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error fetching bulk data: {e}")
            return pd.DataFrame()

    def _calculate_indicators_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate ROC and MFI vectorized."""
        df = df.sort_values(['symbol', 'timestamp'])
        g = df.groupby('symbol')
        
        # 1. ROC (10d, 20d)
        # Shift close by 10 and 20
        close_shift_10 = g['close'].shift(10)
        close_shift_20 = g['close'].shift(20)
        
        df['roc_10'] = ((df['close'] - close_shift_10) / close_shift_10) * 100
        df['roc_20'] = ((df['close'] - close_shift_20) / close_shift_20) * 100
        
        # 2. MFI (Money Flow Index) - 14 period
        # Needs high, low, close, volume
        df['tp'] = (df['high'] + df['low'] + df['close']) / 3
        df['rmf'] = df['tp'] * df['volume'] # Raw Money Flow
        
        # Vectorized MFI logic
        # Positive/Negative Flow requires comparing TP with previous TP
        tp_prev = g['tp'].shift(1)
        
        df['pos_flow'] = np.where(df['tp'] > tp_prev, df['rmf'], 0)
        df['neg_flow'] = np.where(df['tp'] < tp_prev, df['rmf'], 0)
        
        # Rolling Sums
        # Note: we must group again for rolling operations
        # But we can assume df is sorted by symbol, so transform works
        
        # We need rolling sum of pos_flow and neg_flow
        # Since transform runs on Series, we invoke it per column
        
        df['pos_mf_14'] = g['pos_flow'].transform(lambda x: x.rolling(14).sum())
        df['neg_mf_14'] = g['neg_flow'].transform(lambda x: x.rolling(14).sum())
        
        # Avoid division by zero
        df['neg_mf_14'] = df['neg_mf_14'].replace(0, 1) # or handle infinity
        
        df['mfr'] = df['pos_mf_14'] / df['neg_mf_14']
        df['mfi'] = 100 - (100 / (1 + df['mfr']))
        
        # Default MFI to 50 if NaN
        df['mfi'] = df['mfi'].fillna(50)
        
        return df

    def scan_all(self, limit: int = 10) -> List[Dict]:
        """Vectorized scan for momentum."""
        import time
        t0 = time.time()
        
        # 1. Fetch
        df = self._get_bulk_ohlcv_df()
        if df.empty:
            return []
        
        t1 = time.time()
        
        # 2. Calculate
        df = self._calculate_indicators_vectorized(df)
        t2 = time.time()
        
        # 3. Filter Latest
        latest_df = df.groupby('symbol').tail(1).copy()
        
        # 4. Filter empty/NaN ROCs (e.g. not enough data)
        latest_df['roc_10'] = latest_df['roc_10'].fillna(0)
        latest_df['roc_20'] = latest_df['roc_20'].fillna(0)
        
        # 5. Scoring Vectorized
        # ROC Score (40%)
        # >5 -> 100, >2 -> 80, >0 -> 60, else 30
        roc_score = np.select(
            [latest_df['roc_10'] > 5, latest_df['roc_10'] > 2, latest_df['roc_10'] > 0],
            [100, 80, 60],
            default=30
        )
        
        # MFI Score (30%)
        # 50 < mfi < 80 -> 90 (Strong)
        # mfi >= 80 -> 50 (Overbought)
        # else -> 40
        mfi = latest_df['mfi']
        mfi_score = np.select(
            [(mfi > 50) & (mfi < 80), mfi >= 80],
            [90, 50],
            default=40
        )
        
        # Trend Score (30%)
        # roc10 > 0 and roc20 > 0 -> 90
        # roc10 > 0 -> 60
        # else 30
        trend_score = np.select(
            [(latest_df['roc_10'] > 0) & (latest_df['roc_20'] > 0), latest_df['roc_10'] > 0],
            [90, 60],
            default=30
        )
        
        # Total Weighted Score
        total_score = (roc_score * 0.4) + (mfi_score * 0.3) + (trend_score * 0.3)
        latest_df['score'] = total_score
        
        # Filter & Sort
        momentum_stocks = latest_df[latest_df['score'] >= self.min_score].sort_values('score', ascending=False).head(limit)
        
        t3 = time.time()
        logger.info(f"Vectorized Momentum Scan: Fetch={t1-t0:.2f}s, Calc={t2-t1:.2f}s, Filter={t3-t2:.2f}s. Total={t3-t0:.2f}s")
        
        # 6. Format
        results = []
        for _, row in momentum_stocks.iterrows():
            roc_10 = row['roc_10']
            mfi_val = row['mfi']
            
            strength_desc = "STRONG" if roc_10 > 3 else "MODERATE"
            
            results.append({
                "symbol": row['symbol'],
                "name": row['symbol'], 
                "momentum_type": strength_desc,
                "strength": round(row['score']),
                "current_price": round(row['close'], 2),
                "roc_10d": round(roc_10, 2),
                "roc_20d": round(row['roc_20'], 2),
                "mfi": round(mfi_val, 2),
                "target_price": round(row['close'] * 1.05, 2),
                "stop_loss": round(row['close'] * 0.97, 2),
                "reason": f"ROC {roc_10:.1f}%. MFI {mfi_val:.0f}"
            })
            
        return results

    def get_symbols(self) -> List[str]:
        from utils.symbol_utils import get_all_symbols
        return get_all_symbols()
