"""
Data Handler for Backtesting
Handles OHLCV data loading and preprocessing
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DataConfig:
    """Configuration for data handling"""
    symbol: str
    start_date: date
    end_date: date
    interval: str = "1d"  # 1d, 1h, 15m, 5m, 1m


class DataHandler:
    """
    Handles market data for backtesting
    No lookahead bias - strict temporal ordering
    """
    
    REQUIRED_COLUMNS = ['open', 'high', 'low', 'close', 'volume']
    
    def __init__(self):
        self._data: Optional[pd.DataFrame] = None
        self._current_index: int = 0
        self._symbol: str = ""
    
    def load_from_dataframe(self, df: pd.DataFrame, symbol: str) -> None:
        """
        Load data from a pandas DataFrame
        
        Args:
            df: DataFrame with OHLCV columns and DateTimeIndex
            symbol: Stock symbol
        """
        # Validate required columns
        missing_cols = set(self.REQUIRED_COLUMNS) - set(df.columns.str.lower())
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Normalize column names
        df.columns = df.columns.str.lower()
        
        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            elif 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            else:
                raise ValueError("DataFrame must have DateTimeIndex or 'date'/'timestamp' column")
        
        # Sort by date (ascending for forward-looking prevention)
        df = df.sort_index(ascending=True)
        
        # Remove any NaN values
        df = df.dropna(subset=self.REQUIRED_COLUMNS)
        
        self._data = df
        self._symbol = symbol
        self._current_index = 0
        
        logger.info(f"Loaded {len(df)} bars for {symbol}")
    
    def load_from_database(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        db_session: Any,
        timeframe: str = "1d"
    ) -> None:
        """
        Load data from StockCandle database table (V3 source)
        """
        import models # Ensure User is registered first to avoid TradeDecision relationship errors
        from models_alpha import StockCandle, TimeframeMapper
        from sqlalchemy import and_, cast, text
        from sqlalchemy.dialects.postgresql import TIMESTAMP
        import datetime as dt
        
        db_tf = TimeframeMapper.to_standard(timeframe)
        
        # Step 1: Resolve instrument_id using raw SQL from instrument_master (new schema)
        sql = text("SELECT instrument_id FROM instrument_master WHERE symbol = :symbol AND is_active = TRUE")
        result = db_session.execute(sql, {"symbol": symbol}).fetchone()
        instrument_id = result[0] if result else None
        
        if not instrument_id:
            logger.warning(f"Could not resolve instrument_id for {symbol}, trying fallback symbol query")

        # Step 2: Query stock_candle using ORM for OHLCV data (new schema uses stock_candle)
        # Note: StockCandle ORM model must map to stock_candle table with instrument_id FK
        if instrument_id:
            # Use raw SQL for compatibility with new schema
            sql = text("""
                SELECT candle_ts as timestamp, open, high, low, close, volume
                FROM stock_candle
                WHERE instrument_id = :instrument_id
                AND timeframe = :timeframe
                AND candle_ts >= :start_date
                AND candle_ts <= :end_date
                ORDER BY candle_ts ASC
            """)
            result = db_session.execute(sql, {
                "instrument_id": instrument_id,
                "timeframe": TimeframeMapper.to_minutes(db_tf),  # Convert to minutes for new schema
                "start_date": start_date,
                "end_date": end_date
            })
            records = result.fetchall()
        else:
            # Fallback: try by symbol via join
            sql = text("""
                SELECT sc.candle_ts as timestamp, sc.open, sc.high, sc.low, sc.close, sc.volume
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE im.symbol = :symbol
                AND sc.timeframe = :timeframe
                AND sc.candle_ts >= :start_date
                AND sc.candle_ts <= :end_date
                ORDER BY sc.candle_ts ASC
            """)
            result = db_session.execute(sql, {
                "symbol": symbol,
                "timeframe": TimeframeMapper.to_minutes(db_tf),
                "start_date": start_date,
                "end_date": end_date
            })
            records = result.fetchall()
        
        if not records:
            # Fallback to Nifty100Daily for daily data if candles missing
            if db_tf == "1d":
                logger.info(f"No {db_tf} data in stock_candle for {symbol}, trying Nifty100Daily fallback")
                from models_ml import Nifty100Daily
                query = db_session.query(Nifty100Daily).filter(
                    and_(
                        Nifty100Daily.symbol == symbol,
                        Nifty100Daily.timestamp >= start_date,
                        Nifty100Daily.timestamp <= end_date
                    )
                ).order_by(Nifty100Daily.timestamp.asc())
                orm_records = query.all()
                # Convert ORM records to same format as raw SQL
                records = [(r.timestamp, r.open, r.high, r.low, r.close, r.volume or 0) for r in orm_records]
        
        if not records:
            raise ValueError(f"No data found for {symbol} ({db_tf}) between {start_date} and {end_date}")
        
        data = []
        for r in records:
            # Handle both raw SQL tuples and ORM objects
            if hasattr(r, 'timestamp'):
                # ORM object
                ts_raw = r.timestamp
                o, h, l, c, v = r.open, r.high, r.low, r.close, r.volume or 0
            else:
                # Raw SQL tuple: (timestamp, open, high, low, close, volume)
                ts_raw, o, h, l, c, v = r
            
            if isinstance(ts_raw, str):
                ts = dt.datetime.fromisoformat(ts_raw)
            else:
                ts = ts_raw
                
            data.append({
                'date': ts,
                'open': float(o),
                'high': float(h),
                'low': float(l),
                'close': float(c),
                'volume': float(v)
            })
        
        df = pd.DataFrame(data)
        df.set_index('date', inplace=True)
        
        self.load_from_dataframe(df, symbol)
    
    @property
    def data(self) -> pd.DataFrame:
        """Get full dataset"""
        if self._data is None:
            raise ValueError("No data loaded")
        return self._data
    
    @property
    def symbol(self) -> str:
        return self._symbol
    
    def get_bar(self, index: int) -> pd.Series:
        """Get a single bar by index"""
        if self._data is None:
            raise ValueError("No data loaded")
        return self._data.iloc[index]
    
    def get_current_bar(self) -> pd.Series:
        """Get current bar in simulation"""
        return self.get_bar(self._current_index)
    
    def get_history(self, lookback: int) -> pd.DataFrame:
        """
        Get historical data up to current bar (inclusive)
        No lookahead - only returns past data
        """
        if self._data is None:
            raise ValueError("No data loaded")
        
        start_idx = max(0, self._current_index - lookback + 1)
        end_idx = self._current_index + 1  # +1 to include current
        
        return self._data.iloc[start_idx:end_idx].copy()
    
    def advance(self) -> bool:
        """
        Advance to next bar
        Returns False if at end of data
        """
        if self._current_index >= len(self._data) - 1:
            return False
        self._current_index += 1
        return True
    
    def reset(self) -> None:
        """Reset to beginning of data"""
        self._current_index = 0
    
    def __len__(self) -> int:
        if self._data is None:
            return 0
        return len(self._data)
    
    def __iter__(self):
        """Iterate through bars"""
        self.reset()
        return self
    
    def __next__(self) -> pd.Series:
        if self._current_index >= len(self._data):
            raise StopIteration
        bar = self.get_current_bar()
        self._current_index += 1
        return bar
    
    def slice(self, start_date: date, end_date: date) -> 'DataHandler':
        """
        Create a new DataHandler with a subset of data
        Useful for walk-forward analysis
        """
        if self._data is None:
            raise ValueError("No data loaded")
        
        mask = (self._data.index.date >= start_date) & (self._data.index.date <= end_date)
        sliced_df = self._data.loc[mask].copy()
        
        new_handler = DataHandler()
        new_handler.load_from_dataframe(sliced_df, self._symbol)
        
        return new_handler
