"""
Indicator Computation Service
Background service that precomputes technical indicators for all symbols.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy import create_engine, desc, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
import logging
import uuid

from config import settings

logger = logging.getLogger(__name__)


class IndicatorComputer:
    """
    Computes technical indicators from OHLCV data.
    Optimized for batch processing.
    """
    
    @staticmethod
    def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def compute_roc(close: pd.Series, period: int = 10) -> pd.Series:
        """Calculate Rate of Change."""
        return ((close - close.shift(period)) / close.shift(period)) * 100
    
    @staticmethod
    def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD, Signal, and Histogram."""
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def compute_mfi(high: pd.Series, low: pd.Series, close: pd.Series, 
                    volume: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Money Flow Index."""
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
        
        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()
        
        mfi = 100 - (100 / (1 + positive_mf / negative_mf))
        return mfi
    
    @staticmethod
    def compute_bollinger(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> tuple:
        """Calculate Bollinger Bands."""
        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        pct_b = (close - lower) / (upper - lower)
        return upper, sma, lower, pct_b
    
    @staticmethod
    def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    @staticmethod
    def compute_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate Volume Weighted Average Price (cumulative within session)."""
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()
    
    @staticmethod
    def compute_ema(close: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return close.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def compute_sma(close: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return close.rolling(window=period).mean()
    
    @staticmethod
    def compute_momentum_score(rsi: float, roc: float, macd_hist: float) -> float:
        """
        Compute composite momentum score (0-100).
        Weighted average of normalized indicators.
        """
        # Normalize RSI (already 0-100)
        rsi_score = rsi if not pd.isna(rsi) else 50
        
        # Normalize ROC (assume -10 to +10 range maps to 0-100)
        if pd.isna(roc):
            roc_score = 50
        else:
            roc_score = max(0, min(100, 50 + (roc * 5)))
        
        # Normalize MACD histogram (assume -2 to +2 range)
        if pd.isna(macd_hist):
            macd_score = 50
        else:
            macd_score = max(0, min(100, 50 + (macd_hist * 25)))
        
        # Weighted average: RSI 40%, ROC 35%, MACD 25%
        return round(rsi_score * 0.4 + roc_score * 0.35 + macd_score * 0.25, 2)
    
    def compute_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all indicators for a DataFrame with OHLCV columns.
        Returns DataFrame with indicator columns added.
        """
        if df.empty or len(df) < 50:
            return pd.DataFrame()
        
        result = df.copy()
        
        # Momentum
        result['rsi_14'] = self.compute_rsi(df['close'], 14)
        result['roc_10'] = self.compute_roc(df['close'], 10)
        result['roc_20'] = self.compute_roc(df['close'], 20)
        
        macd, macd_signal, macd_hist = self.compute_macd(df['close'])
        result['macd'] = macd
        result['macd_signal'] = macd_signal
        result['macd_histogram'] = macd_hist
        
        # Volume
        result['mfi_14'] = self.compute_mfi(df['high'], df['low'], df['close'], df['volume'])
        result['vwap'] = self.compute_vwap(df['high'], df['low'], df['close'], df['volume'])
        result['volume_sma_20'] = self.compute_sma(df['volume'].astype(float), 20)
        result['volume_ratio'] = df['volume'] / result['volume_sma_20']
        
        # Volatility
        result['atr_14'] = self.compute_atr(df['high'], df['low'], df['close'])
        bb_upper, bb_mid, bb_lower, bb_pct = self.compute_bollinger(df['close'])
        result['bollinger_upper'] = bb_upper
        result['bollinger_mid'] = bb_mid
        result['bollinger_lower'] = bb_lower
        result['bollinger_pct'] = bb_pct
        
        # Trend
        result['ema_9'] = self.compute_ema(df['close'], 9)
        result['ema_20'] = self.compute_ema(df['close'], 20)
        result['ema_50'] = self.compute_ema(df['close'], 50)
        result['sma_20'] = self.compute_sma(df['close'], 20)
        result['sma_50'] = self.compute_sma(df['close'], 50)
        
        # Composite scores
        result['momentum_score'] = result.apply(
            lambda row: self.compute_momentum_score(
                row['rsi_14'], row['roc_10'], row['macd_histogram']
            ), axis=1
        )
        
        # Volatility score (normalized ATR as % of price)
        result['volatility_score'] = (result['atr_14'] / df['close'] * 100).clip(0, 100)
        
        return result


class IndicatorComputeService:
    """
    Service that computes and stores indicators for all symbols.
    Designed to run as a Celery task or standalone batch job.
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self._computer = IndicatorComputer()
    
    def get_symbols(self, limit: int = None) -> List[str]:
        """Get all unique symbols from stock_data table."""
        session = self._Session()
        try:
            query = "SELECT DISTINCT symbol FROM stock_data ORDER BY symbol"
            if limit:
                query += f" LIMIT {limit}"
            result = session.execute(text(query))
            return [row[0] for row in result]
        finally:
            session.close()
    
    def get_ohlcv_data(self, symbol: str, interval: str = "1d", 
                       days: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol."""
        session = self._Session()
        try:
            cutoff = datetime.now() - timedelta(days=days)
            query = text("""
                SELECT timestamp, open, high, low, close, volume
                FROM stock_data
                WHERE symbol = :symbol 
                  AND interval = :interval
                  AND timestamp >= :cutoff
                ORDER BY timestamp ASC
            """)
            result = session.execute(query, {
                "symbol": symbol, 
                "interval": interval,
                "cutoff": cutoff
            })
            rows = result.fetchall()
            
            if not rows:
                return pd.DataFrame()
            
            df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            df['volume'] = df['volume'].astype(int)
            return df
        finally:
            session.close()
    
    def save_indicators(self, symbol: str, interval: str, df: pd.DataFrame):
        """Save computed indicators to database using upsert."""
        if df.empty:
            return 0
        
        session = self._Session()
        try:
            from models_indicators import PrecomputedIndicator
            
            records = []
            for _, row in df.iterrows():
                record = {
                    'symbol': symbol,
                    'interval': interval,
                    'timestamp': row['timestamp'],
                    'close': row.get('close'),
                    'volume': row.get('volume'),
                    'rsi_14': row.get('rsi_14') if not pd.isna(row.get('rsi_14')) else None,
                    'roc_10': row.get('roc_10') if not pd.isna(row.get('roc_10')) else None,
                    'roc_20': row.get('roc_20') if not pd.isna(row.get('roc_20')) else None,
                    'macd': row.get('macd') if not pd.isna(row.get('macd')) else None,
                    'macd_signal': row.get('macd_signal') if not pd.isna(row.get('macd_signal')) else None,
                    'macd_histogram': row.get('macd_histogram') if not pd.isna(row.get('macd_histogram')) else None,
                    'mfi_14': row.get('mfi_14') if not pd.isna(row.get('mfi_14')) else None,
                    'vwap': row.get('vwap') if not pd.isna(row.get('vwap')) else None,
                    'volume_sma_20': row.get('volume_sma_20') if not pd.isna(row.get('volume_sma_20')) else None,
                    'volume_ratio': row.get('volume_ratio') if not pd.isna(row.get('volume_ratio')) else None,
                    'atr_14': row.get('atr_14') if not pd.isna(row.get('atr_14')) else None,
                    'bollinger_upper': row.get('bollinger_upper') if not pd.isna(row.get('bollinger_upper')) else None,
                    'bollinger_mid': row.get('bollinger_mid') if not pd.isna(row.get('bollinger_mid')) else None,
                    'bollinger_lower': row.get('bollinger_lower') if not pd.isna(row.get('bollinger_lower')) else None,
                    'bollinger_pct': row.get('bollinger_pct') if not pd.isna(row.get('bollinger_pct')) else None,
                    'ema_9': row.get('ema_9') if not pd.isna(row.get('ema_9')) else None,
                    'ema_20': row.get('ema_20') if not pd.isna(row.get('ema_20')) else None,
                    'ema_50': row.get('ema_50') if not pd.isna(row.get('ema_50')) else None,
                    'sma_20': row.get('sma_20') if not pd.isna(row.get('sma_20')) else None,
                    'sma_50': row.get('sma_50') if not pd.isna(row.get('sma_50')) else None,
                    'momentum_score': row.get('momentum_score') if not pd.isna(row.get('momentum_score')) else None,
                    'volatility_score': row.get('volatility_score') if not pd.isna(row.get('volatility_score')) else None,
                    'computed_at': datetime.utcnow()
                }
                records.append(record)
            
            # Batch upsert using PostgreSQL ON CONFLICT
            if records:
                stmt = insert(PrecomputedIndicator.__table__).values(records)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_indicator_symbol_interval_ts',
                    set_={
                        'close': stmt.excluded.close,
                        'volume': stmt.excluded.volume,
                        'rsi_14': stmt.excluded.rsi_14,
                        'roc_10': stmt.excluded.roc_10,
                        'roc_20': stmt.excluded.roc_20,
                        'macd': stmt.excluded.macd,
                        'macd_signal': stmt.excluded.macd_signal,
                        'macd_histogram': stmt.excluded.macd_histogram,
                        'mfi_14': stmt.excluded.mfi_14,
                        'vwap': stmt.excluded.vwap,
                        'volume_sma_20': stmt.excluded.volume_sma_20,
                        'volume_ratio': stmt.excluded.volume_ratio,
                        'atr_14': stmt.excluded.atr_14,
                        'bollinger_upper': stmt.excluded.bollinger_upper,
                        'bollinger_mid': stmt.excluded.bollinger_mid,
                        'bollinger_lower': stmt.excluded.bollinger_lower,
                        'bollinger_pct': stmt.excluded.bollinger_pct,
                        'ema_9': stmt.excluded.ema_9,
                        'ema_20': stmt.excluded.ema_20,
                        'ema_50': stmt.excluded.ema_50,
                        'sma_20': stmt.excluded.sma_20,
                        'sma_50': stmt.excluded.sma_50,
                        'momentum_score': stmt.excluded.momentum_score,
                        'volatility_score': stmt.excluded.volatility_score,
                        'computed_at': stmt.excluded.computed_at
                    }
                )
                session.execute(stmt)
                session.commit()
            
            return len(records)
        except Exception as e:
            logger.error(f"Error saving indicators for {symbol}: {e}")
            session.rollback()
            return 0
        finally:
            session.close()
    
    def compute_for_symbol(self, symbol: str, interval: str = "1d") -> int:
        """Compute and save indicators for a single symbol."""
        df = self.get_ohlcv_data(symbol, interval)
        if df.empty:
            return 0
        
        indicators_df = self._computer.compute_all_indicators(df)
        if indicators_df.empty:
            return 0
        
        return self.save_indicators(symbol, interval, indicators_df)
    
    def compute_all(self, interval: str = "1d", symbol_limit: int = None) -> Dict:
        """
        Compute indicators for all symbols.
        Returns summary statistics.
        """
        job_id = str(uuid.uuid4())[:8]
        logger.info(f"Starting indicator computation job {job_id}")
        
        start_time = datetime.now()
        symbols = self.get_symbols(limit=symbol_limit)
        
        stats = {
            "job_id": job_id,
            "interval": interval,
            "symbols_total": len(symbols),
            "symbols_processed": 0,
            "symbols_failed": 0,
            "rows_computed": 0,
            "started_at": start_time.isoformat(),
        }
        
        for symbol in symbols:
            try:
                rows = self.compute_for_symbol(symbol, interval)
                stats["rows_computed"] += rows
                stats["symbols_processed"] += 1
                
                if stats["symbols_processed"] % 50 == 0:
                    logger.info(f"Progress: {stats['symbols_processed']}/{len(symbols)} symbols")
            except Exception as e:
                logger.error(f"Failed to compute indicators for {symbol}: {e}")
                stats["symbols_failed"] += 1
        
        duration = (datetime.now() - start_time).total_seconds()
        stats["duration_seconds"] = round(duration, 2)
        stats["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"Completed job {job_id}: {stats['symbols_processed']} symbols, "
                   f"{stats['rows_computed']} rows in {duration:.1f}s")
        
        return stats


# Singleton instance
_indicator_service: Optional[IndicatorComputeService] = None


def get_indicator_service() -> IndicatorComputeService:
    """Get singleton indicator compute service."""
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = IndicatorComputeService()
    return _indicator_service


# CLI entry point
if __name__ == "__main__":
    import sys
    
    service = get_indicator_service()
    
    interval = sys.argv[1] if len(sys.argv) > 1 else "1d"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    print(f"Computing indicators for interval={interval}, limit={limit}")
    result = service.compute_all(interval=interval, symbol_limit=limit)
    print(f"Result: {result}")
