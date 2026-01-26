"""
Volume Breakout Strategy
Volume-confirmed breakout strategy based on Wyckoff methodology
"""

from typing import Dict, Any, Optional
import pandas as pd

from .base_strategy import BaseStrategy, Signal
from ..backtest.executor import OrderSide


class VolumeBreakoutStrategy(BaseStrategy):
    """
    Volume Breakout Strategy
    
    Trades breakouts confirmed by above-average volume.
    Based on Wyckoff principle: volume precedes price.
    
    Research: Richard Wyckoff methodology - accumulation/distribution with volume
    
    Parameters:
        lookback: Lookback period for high/low (default: 20)
        volume_mult: Volume multiplier for confirmation (default: 1.5)
        position_size_pct: Position size as % of capital (default: 10)
    """
    
    name = "VolumeBreakout"
    version = "1.0.0"
    
    DEFAULT_PARAMS = {
        'lookback': 20,
        'volume_mult': 1.5,
        'position_size_pct': 10,
        'stop_loss_pct': 2.5,
        'take_profit_pct': 5.0,
    }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(merged_params)
        
        self.lookback = self.params['lookback']
        self.volume_mult = self.params['volume_mult']
        self.position_size_pct = self.params['position_size_pct']
        self.stop_loss_pct = self.params['stop_loss_pct']
        self.take_profit_pct = self.params['take_profit_pct']
    
    def get_lookback(self) -> int:
        """Minimum bars needed"""
        return self.lookback + 1
    
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
        
        # Calculate lookback high/low
        lookback_data = history.iloc[-(self.lookback+1):-1]
        resistance = lookback_data['high'].max()
        support = lookback_data['low'].min()
        avg_volume = lookback_data['volume'].mean()
        
        current_price = bar['close']
        current_high = bar['high']
        current_volume = bar['volume']
        
        has_position = symbol in positions
        
        # Volume confirmation
        high_volume = current_volume > avg_volume * self.volume_mult
        
        # Bullish breakout: price breaks resistance with volume
        bullish_breakout = current_high > resistance and high_volume
        
        # Entry
        if bullish_breakout and not has_position:
            capital = executor.cash
            position_value = capital * (self.position_size_pct / 100)
            quantity = int(position_value / current_price)
            
            if quantity > 0:
                stop_loss = support  # Previous support as stop
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
                    reason=f"Volume breakout (Price > {resistance:.2f}, Vol: {current_volume/avg_volume:.1f}x avg)"
                )
        
        # Exit
        if has_position:
            position = positions[symbol]
            
            # Exit if price falls back below breakout level
            if current_price < resistance * 0.98:  # 2% below resistance
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
                    confidence=0.6,
                    reason=f"Failed breakout (Price < {resistance:.2f})"
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
        if self.lookback < 5:
            return False
        if self.volume_mult <= 1:
            return False
        if self.position_size_pct <= 0 or self.position_size_pct > 100:
            return False
        return True
