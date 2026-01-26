"""
Moving Average Crossover Strategy
Simple but effective trend-following strategy
"""

from typing import Dict, Any, Optional
import pandas as pd

from .base_strategy import BaseStrategy, Signal
from ..backtest.executor import OrderSide


class MACrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy
    
    Generates BUY signal when fast MA crosses above slow MA
    Generates SELL signal when fast MA crosses below slow MA
    
    Parameters:
        fast_period: Fast MA period (default: 10)
        slow_period: Slow MA period (default: 30)
        ma_type: 'SMA' or 'EMA' (default: 'EMA')
        position_size_pct: Position size as % of capital (default: 10)
    """
    
    name = "MACrossover"
    version = "1.0.0"
    
    DEFAULT_PARAMS = {
        'fast_period': 10,
        'slow_period': 30,
        'ma_type': 'EMA',
        'position_size_pct': 10,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 6.0,
    }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(merged_params)
        
        self.fast_period = self.params['fast_period']
        self.slow_period = self.params['slow_period']
        self.ma_type = self.params['ma_type']
        self.position_size_pct = self.params['position_size_pct']
        self.stop_loss_pct = self.params['stop_loss_pct']
        self.take_profit_pct = self.params['take_profit_pct']
    
    def get_lookback(self) -> int:
        """Minimum bars needed for calculation"""
        return self.slow_period + 1
    
    def on_bar(
        self,
        bar: pd.Series,
        history: pd.DataFrame,
        positions: Dict[str, Any],
        executor: Any
    ) -> Optional[Signal]:
        """Process current bar and generate signals"""
        
        # Need enough history
        if len(history) < self.get_lookback():
            return None
        
        symbol = executor.data_handler.symbol if hasattr(executor, 'data_handler') else 'UNKNOWN'
        
        # Calculate MAs
        close = history['close']
        
        if self.ma_type == 'EMA':
            fast_ma = close.ewm(span=self.fast_period, adjust=False).mean()
            slow_ma = close.ewm(span=self.slow_period, adjust=False).mean()
        else:  # SMA
            fast_ma = close.rolling(window=self.fast_period).mean()
            slow_ma = close.rolling(window=self.slow_period).mean()
        
        # Current and previous values
        fast_current = fast_ma.iloc[-1]
        fast_prev = fast_ma.iloc[-2]
        slow_current = slow_ma.iloc[-1]
        slow_prev = slow_ma.iloc[-2]
        
        current_price = bar['close']
        has_position = symbol in positions
        
        # Generate signals
        # Bullish crossover: fast crosses above slow
        bullish_cross = fast_prev <= slow_prev and fast_current > slow_current
        
        # Bearish crossover: fast crosses below slow
        bearish_cross = fast_prev >= slow_prev and fast_current < slow_current
        
        if bullish_cross and not has_position:
            # Calculate position size
            capital = executor.cash
            position_value = capital * (self.position_size_pct / 100)
            quantity = int(position_value / current_price)
            
            if quantity > 0:
                # Calculate stop loss and take profit
                stop_loss = current_price * (1 - self.stop_loss_pct / 100)
                take_profit = current_price * (1 + self.take_profit_pct / 100)
                
                # Place buy order
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
                    reason=f"Bullish MA crossover (Fast {self.fast_period} > Slow {self.slow_period})"
                )
        
        elif bearish_cross and has_position:
            position = positions[symbol]
            
            # Place sell order
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
                reason=f"Bearish MA crossover (Fast {self.fast_period} < Slow {self.slow_period})"
            )
        
        # Check stop loss
        if has_position:
            position = positions[symbol]
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
            
            elif current_price >= take_profit_price:
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
                    reason=f"Take profit triggered at {take_profit_price:.2f}"
                )
        
        return None
    
    def validate_params(self) -> bool:
        """Validate strategy parameters"""
        if self.fast_period >= self.slow_period:
            return False
        if self.fast_period < 2 or self.slow_period < 2:
            return False
        if self.position_size_pct <= 0 or self.position_size_pct > 100:
            return False
        return True
