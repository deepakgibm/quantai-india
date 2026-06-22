"""
Momentum Scanner Service (Vectorized)
Finds stocks with strong price momentum using ROC and MFI indicators.
Optimized: Uses vectorized Pandas operations for <2s latency.
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime
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
        self.min_score = 40
        # Precomputed check logic removed/simplified as vectorization is fast enough
        # But we can keep it if needed. For now, vectorization is the priority refactor.
        self._use_precomputed = False 
    
    def _get_bulk_ohlcv_df(self, days: int = 60) -> pd.DataFrame:
        """Fetch OHLCV data for ALL active symbols from stock_candle table."""
        try:
            from database import SessionLocal
            
            session = SessionLocal()
            try:
                # Use raw SQL for efficiency and to avoid model confusion
                # This ensures we use the NEW SCHEMA correctly
                query = f"""
                    SELECT 
                        im.symbol, 
                        sc.candle_ts as timestamp, 
                        sc.open, 
                        sc.high, 
                        sc.low, 
                        sc.close, 
                        sc.volume
                    FROM stock_candle sc
                    JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                    WHERE sc.timeframe = 1440
                    AND im.is_active = TRUE
                    AND sc.candle_ts >= NOW() - INTERVAL '{days} days'
                """
                
                df = pd.read_sql(query, session.bind)

                if df.empty:
                    logger.warning("No data found in stock_candle for momentum scan")
                    return pd.DataFrame()
                
                # Ensure correct types
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['high'] = pd.to_numeric(df['high'], errors='coerce')
                df['low'] = pd.to_numeric(df['low'], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

                # Drop NaNs
                df = df.dropna(subset=['close', 'high', 'low', 'volume'])

                logger.info(f"Fetched {len(df)} rows for {df['symbol'].nunique()} symbols from stock_candle")
                return df
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error fetching bulk data from stock_candle: {e}")
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
        
        # 3. ATR (20d) for Trade Levels
        tr = pd.concat([
            (df['high'] - df['low']),
            (df['high'] - g['close'].shift(1)).abs(),
            (df['low'] - g['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        
        # Calculate ATR using transform (keeps index aligned)

        df['tr'] = tr
        df['atr_20d'] = g['tr'].transform(lambda x: x.rolling(20).mean())
        
        # Avoid division by zero
        df['neg_mf_14'] = df['neg_mf_14'].replace(0, 1) # or handle infinity
        
        df['mfr'] = df['pos_mf_14'] / df['neg_mf_14']
        df['mfi'] = 100 - (100 / (1 + df['mfr']))
        
        # Default MFI to 50 if NaN
        df['mfi'] = df['mfi'].fillna(50)
        
        return df

    def scan_all(self, limit: int = 10) -> List[Dict]:
        """Perform full scan and return results."""
        logger.info(f"scan_all: Starting scan with limit={limit}")
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
        roc_score = np.select(
            [
                latest_df['roc_10'] > 5.0,
                latest_df['roc_10'] > 2.0,
                (latest_df['roc_10'] >= -1.0) & (latest_df['roc_10'] <= 2.0),
                latest_df['roc_10'] >= -3.0
            ],
            [100, 80, 50, 35],
            default=10
        )
        
        # MFI Score (30%)
        mfi = latest_df['mfi']
        mfi_score = np.select(
            [
                (mfi > 50) & (mfi < 80),
                (mfi >= 35) & (mfi <= 50),
                (mfi >= 20) & (mfi < 35),
                mfi < 20
            ],
            [90, 50, 35, 10],
            default=40  # overbought
        )
        
        # Trend Score (30%)
        trend_score = np.select(
            [
                (latest_df['roc_10'] > 0) & (latest_df['roc_20'] > 0),
                (latest_df['roc_10'] > 0) | (latest_df['roc_20'] > 0),
                (latest_df['roc_10'] < 0) & (latest_df['roc_20'] < 0),
                (latest_df['roc_10'] < 0) | (latest_df['roc_20'] < 0)
            ],
            [90, 70, 10, 35],
            default=50
        )
        
        # Total Weighted Score
        total_score = (roc_score * 0.4) + (mfi_score * 0.3) + (trend_score * 0.3)
        latest_df['score'] = total_score
        
        # Balanced Selection: ensure all 5 buckets are represented
        sb_df = latest_df[latest_df['score'] >= 80].sort_values('score', ascending=False)
        mb_df = latest_df[(latest_df['score'] >= 60) & (latest_df['score'] < 80)].sort_values('score', ascending=False)
        neut_df = latest_df[(latest_df['score'] >= 40) & (latest_df['score'] < 60)].copy()
        neut_df['dist_to_50'] = (neut_df['score'] - 50).abs()
        neut_df = neut_df.sort_values('dist_to_50', ascending=True)
        mbe_df = latest_df[(latest_df['score'] >= 30) & (latest_df['score'] < 40)].sort_values('score', ascending=True)
        sbe_df = latest_df[latest_df['score'] < 30].sort_values('score', ascending=True)
        
        # We will keep track of how many we select from each bucket dataframe
        dfs = {
            "STRONG_BULLISH": sb_df,
            "MODERATE_BULLISH": mb_df,
            "NEUTRAL": neut_df,
            "MODERATE_BEARISH": mbe_df,
            "STRONG_BEARISH": sbe_df
        }
        
        selected_dfs = {k: pd.DataFrame() for k in dfs}
        
        # Round-robin selection to distribute up to 'limit'
        remaining_limit = limit
        active_buckets = list(dfs.keys())
        
        while remaining_limit > 0 and active_buckets:
            alloc = max(1, remaining_limit // len(active_buckets))
            next_active = []
            
            for b in active_buckets:
                df = dfs[b]
                current_selected = selected_dfs[b]
                current_len = len(current_selected)
                available = len(df) - current_len
                
                if available > 0:
                    take = min(alloc, available, remaining_limit)
                    chunk = df.iloc[current_len : current_len + take]
                    selected_dfs[b] = pd.concat([selected_dfs[b], chunk])
                    remaining_limit -= len(chunk)
                    
                    if len(selected_dfs[b]) < len(df) and remaining_limit > 0:
                        next_active.append(b)
            
            if len(active_buckets) == len(next_active) and alloc == 0:
                break
                
            active_buckets = next_active
            
        momentum_stocks = pd.concat(selected_dfs.values())
        momentum_stocks = momentum_stocks.sort_values('score', ascending=False)
        momentum_stocks = momentum_stocks.fillna(0)
        
        t3 = time.time()
        logger.info(f"Vectorized Momentum Scan: Fetch={t1-t0:.2f}s, Calc={t2-t1:.2f}s, Filter={t3-t2:.2f}s. Total={t3-t0:.2f}s")
        
        # 6. Format
        results = []
        counts = {"STRONG_BULLISH": 0, "MODERATE_BULLISH": 0, "NEUTRAL": 0, "MODERATE_BEARISH": 0, "STRONG_BEARISH": 0}
        
        for _, row in momentum_stocks.iterrows():
            roc_10 = row['roc_10']
            mfi_val = row['mfi']
            score = row['score']
            
            # Determine Bucket (Align with Frontend BUCKETS)
            if score >= 80:
                bucket = "STRONG_BULLISH"
            elif score >= 60:
                bucket = "MODERATE_BULLISH"
            elif score >= 40:
                bucket = "NEUTRAL"
            elif score >= 30:
                bucket = "MODERATE_BEARISH"
            else:
                bucket = "STRONG_BEARISH"
                
            counts[bucket] = counts.get(bucket, 0) + 1
            
            results.append({
                "symbol": str(row['symbol']),
                "ltp": float(round(row['close'], 2)),
                "prev_close": float(round(row['close'] / (1 + roc_10/100), 2)),
                "change_pct": float(round(roc_10, 2)),
                "momentum_score": int(round(score)),
                "bucket": bucket,
                "direction": "Bullish" if roc_10 >= 0 else "Bearish",
                "correlation": 0.5,
                "source": "DB_FALLBACK",
                "last_update": datetime.now().isoformat(),
                "roc_20d": float(round(row['roc_20'], 2)),
                "mfi": float(round(mfi_val, 2))
            })
            
        logger.info(f"Momentum Scan results distribution: {counts}")
        return results

    def get_symbols(self) -> List[str]:
        from utils.symbol_utils import get_all_symbols
        return get_all_symbols()
