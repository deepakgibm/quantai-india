"""
Supertrend Strategy
ATR-based trend following strategy by Olivier Seban
Popular in Indian markets
"""

from typing import Dict, Any, Optional
import pandas as pd

from .base_strategy import BaseStrategy, Signal
from ..backtest.executor import OrderSide


class SupertrendStrategy(BaseStrategy):
    """
    Supertrend Strategy
    
    Uses ATR-based bands to determine trend direction.
    Long when price > Supertrend, Short when price < Supertrend
    
    Research: Olivier Seban's Supertrend - very popular in India for intraday/swing
    
    Parameters:
        period: ATR period (default: 10)
        multiplier: ATR multiplier (default: 3.0)
        position_size_pct: Position size as % of capital (default: 10)
    """
    
    name = "Supertrend"
    version = "1.0.0"
    
    DEFAULT_PARAMS = {
        'period': 10,
        'multiplier': 3.0,
        'position_size_pct': 10,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 6.0,
    }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(merged_params)
        
        self.period = self.params['period']
        self.multiplier = self.params['multiplier']
        self.position_size_pct = self.params['position_size_pct']
        self.stop_loss_pct = self.params['stop_loss_pct']
        self.take_profit_pct = self.params['take_profit_pct']
    
    def get_lookback(self) -> int:
        """Minimum bars needed for Supertrend calculation"""
        return self.period + 5
    
    def _calculate_supertrend(self, df: pd.DataFrame) -> tuple:
        """Calculate Supertrend indicator"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.period).mean()
        
        # Calculate basic upper and lower bands
        hl2 = (high + low) / 2
        basic_upper = hl2 + (self.multiplier * atr)
        basic_lower = hl2 - (self.multiplier * atr)
        
        # Initialize Supertrend arrays
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)
        
        # First valid value
        first_valid = self.period
        supertrend.iloc[first_valid] = basic_upper.iloc[first_valid]
        direction.iloc[first_valid] = -1  # Start bearish
        
        # Calculate Supertrend
        for i in range(first_valid + 1, len(df)):
            if direction.iloc[i-1] == 1:  # Previous was bullish
                if close.iloc[i] < supertrend.iloc[i-1]:
                    supertrend.iloc[i] = basic_upper.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = max(basic_lower.iloc[i], supertrend.iloc[i-1])
                    direction.iloc[i] = 1
            else:  # Previous was bearish
                if close.iloc[i] > supertrend.iloc[i-1]:
                    supertrend.iloc[i] = basic_lower.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = min(basic_upper.iloc[i], supertrend.iloc[i-1])
                    direction.iloc[i] = -1
        
        return supertrend, direction
    
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
        
        # Calculate Supertrend
        supertrend, direction = self._calculate_supertrend(history)
        
        current_dir = direction.iloc[-1]
        prev_dir = direction.iloc[-2] if len(direction) > 1 else current_dir
        current_supertrend = supertrend.iloc[-1]
        
        current_price = bar['close']
        has_position = symbol in positions
        
        # Bullish flip: direction changes from -1 to 1
        bullish_flip = prev_dir == -1 and current_dir == 1
        
        # Bearish flip: direction changes from 1 to -1
        bearish_flip = prev_dir == 1 and current_dir == -1
        
        # Entry on bullish flip
        if bullish_flip and not has_position:
            capital = executor.cash
            position_value = capital * (self.position_size_pct / 100)
            quantity = int(position_value / current_price)
            
            if quantity > 0:
                # Use Supertrend as trailing stop
                stop_loss = current_supertrend
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
                    confidence=0.75,
                    reason=f"Supertrend bullish flip (ST: {current_supertrend:.2f})"
                )
        
        # Exit on bearish flip
        if has_position:
            position = positions[symbol]
            
            if bearish_flip:
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
                    confidence=0.75,
                    reason=f"Supertrend bearish flip (ST: {current_supertrend:.2f})"
                )
            
            # Trailing stop using Supertrend
            if current_price < current_supertrend and current_dir == -1:
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
                    reason=f"Price crossed below Supertrend ({current_supertrend:.2f})"
                )
            
            # Take profit
            take_profit_price = position.avg_price * (1 + self.take_profit_pct / 100)
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
        if self.period < 2:
            return False
        if self.multiplier <= 0:
            return False
        if self.position_size_pct <= 0 or self.position_size_pct > 100:
            return False
        return True
