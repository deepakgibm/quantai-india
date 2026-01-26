"""
Bollinger Bands Squeeze Strategy
Volatility contraction/expansion strategy by John Bollinger
"""

from typing import Dict, Any, Optional
import pandas as pd

from .base_strategy import BaseStrategy, Signal
from ..backtest.executor import OrderSide


class BollingerSqueezeStrategy(BaseStrategy):
    """
    Bollinger Bands Squeeze Strategy
    
    Identifies periods of low volatility (squeeze) and trades the breakout.
    Squeeze is detected when band width contracts significantly.
    
    Research: John Bollinger's squeeze strategy - volatility contraction precedes expansion
    
    Parameters:
        period: BB period (default: 20)
        std_dev: Standard deviation multiplier (default: 2.0)
        squeeze_threshold: Band width threshold for squeeze (default: 0.04)
        position_size_pct: Position size as % of capital (default: 10)
    """
    
    name = "BollingerSqueeze"
    version = "1.0.0"
    
    DEFAULT_PARAMS = {
        'period': 20,
        'std_dev': 2.0,
        'squeeze_threshold': 0.04,  # 4% band width = squeeze
        'lookback_squeeze': 10,  # Bars to confirm squeeze
        'position_size_pct': 10,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 4.0,
    }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(merged_params)
        
        self.period = self.params['period']
        self.std_dev = self.params['std_dev']
        self.squeeze_threshold = self.params['squeeze_threshold']
        self.lookback_squeeze = self.params['lookback_squeeze']
        self.position_size_pct = self.params['position_size_pct']
        self.stop_loss_pct = self.params['stop_loss_pct']
        self.take_profit_pct = self.params['take_profit_pct']
        
        self._in_squeeze = {}  # Track if currently in squeeze
    
    def get_lookback(self) -> int:
        """Minimum bars needed for BB calculation"""
        return self.period + self.lookback_squeeze + 1
    
    def _calculate_bollinger(self, prices: pd.Series) -> tuple:
        """Calculate Bollinger Bands and band width"""
        sma = prices.rolling(window=self.period).mean()
        std = prices.rolling(window=self.period).std()
        
        upper_band = sma + (std * self.std_dev)
        lower_band = sma - (std * self.std_dev)
        
        # Band width as percentage of middle band
        band_width = (upper_band - lower_band) / sma
        
        return sma, upper_band, lower_band, band_width
    
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
        
        # Calculate Bollinger Bands
        close = history['close']
        sma, upper_band, lower_band, band_width = self._calculate_bollinger(close)
        
        current_price = bar['close']
        current_bw = band_width.iloc[-1]
        prev_bw = band_width.iloc[-2]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_sma = sma.iloc[-1]
        
        has_position = symbol in positions
        
        # Detect squeeze (low volatility period)
        is_squeeze = current_bw < self.squeeze_threshold
        was_squeeze = self._in_squeeze.get(symbol, False)
        
        # Check if squeeze is releasing (band width expanding)
        squeeze_release = was_squeeze and current_bw > prev_bw * 1.1
        
        # Update squeeze state
        self._in_squeeze[symbol] = is_squeeze
        
        # Entry on squeeze release with direction
        if squeeze_release and not has_position:
            # Determine direction from price vs SMA
            is_bullish = current_price > current_sma
            
            if is_bullish:
                capital = executor.cash
                position_value = capital * (self.position_size_pct / 100)
                quantity = int(position_value / current_price)
                
                if quantity > 0:
                    stop_loss = current_lower
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
                        reason=f"BB squeeze breakout (BW: {current_bw:.2%} expanding)"
                    )
        
        # Exit conditions
        if has_position:
            position = positions[symbol]
            
            # Exit when price touches opposite band
            if current_price >= current_upper:
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
                    reason=f"Price touched upper BB ({current_upper:.2f})"
                )
            
            # Exit when price falls below lower band
            if current_price <= current_lower:
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
                    reason=f"Price broke lower BB ({current_lower:.2f})"
                )
            
            # Stop loss
            stop_loss_price = position.avg_price * (1 - self.stop_loss_pct / 100)
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
        
        return None
    
    def validate_params(self) -> bool:
        """Validate strategy parameters"""
        if self.period < 2:
            return False
        if self.std_dev <= 0:
            return False
        if self.squeeze_threshold <= 0 or self.squeeze_threshold > 0.5:
            return False
        if self.position_size_pct <= 0 or self.position_size_pct > 100:
            return False
        return True
