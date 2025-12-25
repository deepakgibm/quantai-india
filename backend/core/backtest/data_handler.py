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
        db_session: Any
    ) -> None:
        """
        Load data from Nifty100Daily database table
        """
        from models_ml import Nifty100Daily
        from sqlalchemy import and_
        
        query = db_session.query(Nifty100Daily).filter(
            and_(
                Nifty100Daily.symbol == symbol,
                Nifty100Daily.date >= start_date,
                Nifty100Daily.date <= end_date
            )
        ).order_by(Nifty100Daily.date.asc())
        
        records = query.all()
        
        if not records:
            raise ValueError(f"No data found for {symbol} between {start_date} and {end_date}")
        
        data = []
        for r in records:
            data.append({
                'date': r.date,
                'open': r.open,
                'high': r.high,
                'low': r.low,
                'close': r.close,
                'volume': r.volume
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
