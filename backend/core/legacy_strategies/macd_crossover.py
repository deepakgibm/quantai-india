"""
MACD Crossover Strategy
Classic momentum strategy by Gerald Appel
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, Signal
from ..backtest.executor import OrderSide


class MACDCrossoverStrategy(BaseStrategy):
    """
    MACD Crossover Strategy
    
    Buys when MACD line crosses above signal line
    Sells when MACD line crosses below signal line
    
    Research: Gerald Appel's MACD - one of the most reliable momentum indicators
    
    Parameters:
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line period (default: 9)
        position_size_pct: Position size as % of capital (default: 10)
    """
    
    name = "MACDCrossover"
    version = "1.0.0"
    
    DEFAULT_PARAMS = {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9,
        'position_size_pct': 10,
        'stop_loss_pct': 2.5,
        'take_profit_pct': 5.0,
        'use_histogram': True,  # Use histogram for confirmation
    }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(merged_params)
        
        self.fast_period = self.params['fast_period']
        self.slow_period = self.params['slow_period']
        self.signal_period = self.params['signal_period']
        self.position_size_pct = self.params['position_size_pct']
        self.stop_loss_pct = self.params['stop_loss_pct']
        self.take_profit_pct = self.params['take_profit_pct']
        self.use_histogram = self.params['use_histogram']
    
    def get_lookback(self) -> int:
        """Minimum bars needed for MACD calculation"""
        return self.slow_period + self.signal_period + 1
    
    def _calculate_macd(self, prices: pd.Series) -> tuple:
        """Calculate MACD, Signal, and Histogram"""
        fast_ema = prices.ewm(span=self.fast_period, adjust=False).mean()
        slow_ema = prices.ewm(span=self.slow_period, adjust=False).mean()
        
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def on_bar(
        self,
        bar: pd.Series,
        history: pd.DataFrame,
        positions: Dict[str, Any],
        executor: Any
    ) -> Optional[Signal]:
        """Process current bar and generate signals"""
        
        if len(history) < self.get_lookback():
            return None
        
        symbol = executor.data_handler.symbol if hasattr(executor, 'data_handler') else 'UNKNOWN'
        
        # Calculate MACD
        close = history['close']
        macd_line, signal_line, histogram = self._calculate_macd(close)
        
        macd_current = macd_line.iloc[-1]
        macd_prev = macd_line.iloc[-2]
        signal_current = signal_line.iloc[-1]
        signal_prev = signal_line.iloc[-2]
        hist_current = histogram.iloc[-1]
        hist_prev = histogram.iloc[-2]
        
        current_price = bar['close']
        has_position = symbol in positions
        
        # Bullish crossover: MACD crosses above signal
        bullish_cross = macd_prev <= signal_prev and macd_current > signal_current
        # Confirm with histogram turning positive
        if self.use_histogram:
            bullish_cross = bullish_cross and hist_current > 0 and hist_prev <= 0
        
        # Bearish crossover: MACD crosses below signal
        bearish_cross = macd_prev >= signal_prev and macd_current < signal_current
        if self.use_histogram:
            bearish_cross = bearish_cross and hist_current < 0 and hist_prev >= 0
        
        # Entry
        if bullish_cross and not has_position:
            capital = executor.cash
            position_value = capital * (self.position_size_pct / 100)
            quantity = int(position_value / current_price)
            
            if quantity > 0:
                stop_loss = current_price * (1 - self.stop_loss_pct / 100)
                take_profit = current_price * (1 + self.take_profit_pct / 100)
                
                executor.submit_order(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    quantity=quantity,
                    strategy_id=self.name
                )
                
                return Signal(
                    symbol=symbol,
                    action='BUY',
                    quantity=quantity,
                    price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=0.7,
                    reason=f"Bullish MACD crossover (MACD: {macd_current:.2f} > Signal: {signal_current:.2f})"
                )
        
        # Exit
        if has_position:
            position = positions[symbol]
            
            # Exit on bearish crossover
            if bearish_cross:
                executor.submit_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    strategy_id=self.name
                )
                return Signal(
                    symbol=symbol,
                    action='SELL',
                    quantity=position.quantity,
                    price=current_price,
                    confidence=0.7,
                    reason=f"Bearish MACD crossover (MACD: {macd_current:.2f} < Signal: {signal_current:.2f})"
                )
            
            # Stop loss / Take profit
            stop_loss_price = position.avg_price * (1 - self.stop_loss_pct / 100)
            take_profit_price = position.avg_price * (1 + self.take_profit_pct / 100)
            
            if current_price <= stop_loss_price:
                executor.submit_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    strategy_id=self.name
                )
                return Signal(
                    symbol=symbol,
                    action='SELL',
                    quantity=position.quantity,
                    price=current_price,
                    reason=f"Stop loss triggered at {stop_loss_price:.2f}"
                )
            
            if current_price >= take_profit_price:
                executor.submit_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    strategy_id=self.name
                )
                return Signal(
                    symbol=symbol,
                    action='SELL',
                    quantity=position.quantity,
                    price=current_price,
                    reason=f"Take profit at {take_profit_price:.2f}"
                )
        
        return None
    
    def validate_params(self) -> bool:
        """Validate strategy parameters"""
        if self.fast_period >= self.slow_period:
            return False
        if self.fast_period < 2 or self.slow_period < 2 or self.signal_period < 2:
            return False
        if self.position_size_pct <= 0 or self.position_size_pct > 100:
            return False
        return True
