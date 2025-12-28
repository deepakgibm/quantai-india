"""
Stochastic Oscillator Strategy
Momentum reversal strategy by George Lane
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, Signal
from ..backtest.executor import OrderSide


class StochasticStrategy(BaseStrategy):
    """
    Stochastic Oscillator Strategy
    
    Buys when %K crosses above %D in oversold zone
    Sells when %K crosses below %D in overbought zone
    
    Research: George Lane's Stochastic - momentum reversal with overbought/oversold zones
    
    Parameters:
        k_period: %K period (default: 14)
        d_period: %D smoothing period (default: 3)
        oversold: Oversold threshold (default: 20)
        overbought: Overbought threshold (default: 80)
        position_size_pct: Position size as % of capital (default: 10)
    """
    
    name = "Stochastic"
    version = "1.0.0"
    
    DEFAULT_PARAMS = {
        'k_period': 14,
        'd_period': 3,
        'oversold': 20,
        'overbought': 80,
        'position_size_pct': 10,
        'stop_loss_pct': 2.5,
        'take_profit_pct': 5.0,
    }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(merged_params)
        
        self.k_period = self.params['k_period']
        self.d_period = self.params['d_period']
        self.oversold = self.params['oversold']
        self.overbought = self.params['overbought']
        self.position_size_pct = self.params['position_size_pct']
        self.stop_loss_pct = self.params['stop_loss_pct']
        self.take_profit_pct = self.params['take_profit_pct']
    
    def get_lookback(self) -> int:
        """Minimum bars needed for Stochastic calculation"""
        return self.k_period + self.d_period + 1
    
    def _calculate_stochastic(self, df: pd.DataFrame) -> tuple:
        """Calculate %K and %D"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        lowest_low = low.rolling(window=self.k_period).min()
        highest_high = high.rolling(window=self.k_period).max()
        
        # %K
        k = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-10)
        
        # %D (smoothed %K)
        d = k.rolling(window=self.d_period).mean()
        
        return k, d
    
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
        
        # Calculate Stochastic
        k, d = self._calculate_stochastic(history)
        
        k_current = k.iloc[-1]
        k_prev = k.iloc[-2]
        d_current = d.iloc[-1]
        d_prev = d.iloc[-2]
        
        current_price = bar['close']
        has_position = symbol in positions
        
        # Bullish crossover in oversold zone
        bullish = k_prev <= d_prev and k_current > d_current and k_current < self.oversold + 10
        
        # Bearish crossover in overbought zone
        bearish = k_prev >= d_prev and k_current < d_current and k_current > self.overbought - 10
        
        # Entry
        if bullish and not has_position:
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
                    confidence=0.65,
                    reason=f"Stochastic bullish crossover in oversold (%K: {k_current:.1f}, %D: {d_current:.1f})"
                )
        
        # Exit
        if has_position:
            position = positions[symbol]
            
            if bearish:
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
                    confidence=0.65,
                    reason=f"Stochastic bearish crossover in overbought (%K: {k_current:.1f}, %D: {d_current:.1f})"
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
                    reason=f"Stop loss at {stop_loss_price:.2f}"
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
        if self.k_period < 2 or self.d_period < 2:
            return False
        if self.oversold >= self.overbought:
            return False
        if self.position_size_pct <= 0 or self.position_size_pct > 100:
            return False
        return True
