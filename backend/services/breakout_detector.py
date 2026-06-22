"""
BreakoutDetector Service (Vectorized)
Identifies stocks with volume-backed breakouts using optimized Pandas vectorization.
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from database import SessionLocal
import logging

logger = logging.getLogger(__name__)

class BreakoutDetector:
    """
    Quantitative breakout detection service.
    
    Breakout Criteria:
    - Price breaking above 20-day high with 1.5x+ volume
    - Breaking out of consolidation (low ATR followed by expansion)
    - Fresh 52-week highs with volume confirmation
    - RSI momentum confirmation (> 50)
    
    Score threshold: >= 60 for valid breakouts
    """
    
    def __init__(self):
        self._Session = SessionLocal
        self.min_score = 60
        
    def _get_bulk_ohlcv_df(self, days: int = 365) -> pd.DataFrame:
        """Fetch OHLCV data for ALL symbols using new schema (stock_candle)."""
        try:
            session = self._Session()
            try:
                # Use raw SQL for precision with the partitioned schema
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
                    logger.warning("No data found in stock_candle for breakout detection")
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
            logger.error(f"Error fetching bulk data for breakout detector: {e}")
            return pd.DataFrame()
    
    def _calculate_indicators_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators on the entire DataFrame using groupby transforms."""
        # Sort properly
        df = df.sort_values(['symbol', 'timestamp'])
        
        # Group by symbol
        g = df.groupby('symbol')
        
        # 1. Rolling Highs (Transform ensures index alignment)
        df['high_20d'] = g['high'].transform(lambda x: x.shift(1).rolling(window=20, min_periods=1).max())
        df['high_52w'] = g['high'].transform(lambda x: x.shift(1).rolling(window=250, min_periods=1).max())
        
        # 2. Volume Averages
        df['vol_avg_20d'] = g['volume'].transform(lambda x: x.shift(1).rolling(window=20, min_periods=1).mean())
        
        from core.indicators import grouped_atr, grouped_rsi
        
        # 3. ATR (Average True Range)
        df['atr_20d'] = grouped_atr(df, groupby_col='symbol', period=20, min_periods=1)
        df['atr_5d'] = grouped_atr(df, groupby_col='symbol', period=5, min_periods=1)
        
        # 4. RSI (Relative Strength Index)
        df['rsi'] = grouped_rsi(df, groupby_col='symbol', period=14)
        
        return df

    def scan_all(self, limit: int = 10) -> List[Dict]:
        """Scan all stocks for breakouts using optimized vectorization."""
        import time
        t0 = time.time()
        
        # 1. Fetch
        df = self._get_bulk_ohlcv_df()
        if df.empty:
            return []
            
        t1 = time.time()
        
        # 2. Calculate Indicators
        df = self._calculate_indicators_vectorized(df)
        t2 = time.time()
        
        # 3. Filter for Latest Candle Only
        # We only care about the current status
        latest_df = df.groupby('symbol').tail(1).copy()
        
        # 4. Apply Logic (Vectorized Filters)
        # Avoid DivisionByZero
        latest_df['vol_avg_20d'] = latest_df['vol_avg_20d'].replace(0, 1)
        latest_df['atr_20d'] = latest_df['atr_20d'].replace(0, 1)
        
        # Ratios
        latest_df['volume_ratio'] = latest_df['volume'] / latest_df['vol_avg_20d']
        latest_df['atr_expansion'] = latest_df['atr_5d'] / latest_df['atr_20d']
        
        # Breakout Conditions
        # Use fillna to handle missing data (e.g. new stocks)
        latest_df['is_52w_high'] = latest_df['close'] >= latest_df['high_52w'] * 0.98
        latest_df['is_20d_high'] = latest_df['close'] >= latest_df['high_20d'] * 0.98
        latest_df['is_consolidation_breakout'] = latest_df['atr_expansion'] >= 1.5
        
        # Scoring Vectorized
        scores = pd.Series(20, index=latest_df.index) # Base score
        
        # Breakout Level Score
        scores += np.where(latest_df['is_52w_high'], 80, 0) # 20+80=100
        scores += np.where((~latest_df['is_52w_high']) & latest_df['is_20d_high'], 60, 0) # 20+60=80
        scores += np.where((~latest_df['is_52w_high']) & (~latest_df['is_20d_high']) & latest_df['is_consolidation_breakout'], 50, 0) # 20+50=70
        
        # Volume Score
        vol_score = np.select(
            [latest_df['volume_ratio'] >= 2.0, latest_df['volume_ratio'] >= 1.5, latest_df['volume_ratio'] >= 1.0],
            [100, 80, 50],
            default=20
        )
        
        # Momentum Score
        mom_score = np.select(
            [latest_df['rsi'] >= 60, latest_df['rsi'] >= 50],
            [90, 70],
            default=30
        )
        
        # Total Weighted Score
        # weights = {"breakout_level": 0.35, "volume": 0.30, "momentum": 0.20, "price_action": 0.15}
        # Simplified for vectorization (assuming price_action ~ 80 for breakouts)
        final_scores = (scores * 0.4) + (vol_score * 0.35) + (mom_score * 0.25)
        latest_df['score'] = final_scores
        
        # Filter Results
        breakouts = latest_df[latest_df['score'] >= self.min_score].sort_values('score', ascending=False).head(limit)
        
        t3 = time.time()
        elapsed = (time.time() - t0) * 1000
        logger.info(f"Vectorized Scan: Fetch={t1-t0:.2f}s, Calc={t2-t1:.2f}s, Filter={t3-t2:.2f}s. Total={elapsed:.1f}ms")
        
        # 5. Format Output
        results = []
        for _, row in breakouts.iterrows():
            breakout_type = "CONSOLIDATION"
            if row['is_52w_high']: breakout_type = "52W_HIGH"
            elif row['is_20d_high']: breakout_type = "RESISTANCE"
            
            # Helper to handle NaN/Inf and convert to native float
            def clean_val(v, default=0.0):
                try:
                    import math
                    if v is None or (isinstance(v, (float, np.float64, np.float32)) and (math.isnan(v) or math.isinf(v))):
                        return default
                    return float(v)
                except:
                    return default
            
            val_score = clean_val(row['score'])

            results.append({
                "symbol": str(row['symbol']),
                "name": str(row['symbol']),
                "breakout_type": breakout_type,
                "volume_ratio": round(clean_val(row['volume_ratio']), 2),
                "strength": int(val_score),
                "current_price": round(clean_val(row['close']), 2),
                "breakout_level": round(clean_val(row['high_52w'] if breakout_type == "52W_HIGH" else row['high_20d']), 2),
                "atr": round(clean_val(row['atr_20d']), 2),
                "target_price": round(clean_val(row['close'] * 1.08), 2),
                "stop_loss": round(clean_val(row['close'] * 0.97), 2),
                "indicators": {
                    "rsi": round(clean_val(row['rsi'], 50.0), 2),
                    "atr_expansion": round(clean_val(row['atr_expansion']), 2),
                    "high_52w": round(clean_val(row['high_52w']), 2)
                },
                "trend": "BULLISH",
                "action": "BUY",
                "reason": f"{breakout_type} with {clean_val(row['volume_ratio']):.1f}x Vol"
            })
            
        return {
            "stocks": results,
            "symbols_processed": len(latest_df),
            "total_symbols": len(latest_df),
            "completed_all": True,
            "filter_stats": {
                "filtered_by_rule": len(latest_df) - len(results)
            },
            "tables_used": ["nifty100_daily"],
            "metrics": {
                "total_ms": int(elapsed)
            }
        }

    def get_symbols(self) -> List[str]:
        from utils.symbol_utils import get_all_symbols
        return get_all_symbols()
