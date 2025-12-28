"""
ADX Trend Strength Strategy
Trend filter strategy by Welles Wilder
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, Signal
from ..backtest.executor import OrderSide


class ADXTrendStrategy(BaseStrategy):
    """
    ADX Trend Strength Strategy
    
    Uses ADX to measure trend strength and +DI/-DI for direction.
    Only trades when ADX > threshold (strong trend).
    
    Research: Welles Wilder's ADX - measures trend strength not direction
    
    Parameters:
        period: ADX period (default: 14)
        adx_threshold: Minimum ADX for trend (default: 25)
        position_size_pct: Position size as % of capital (default: 10)
    """
    
    name = "ADXTrend"
    version = "1.0.0"
    
    DEFAULT_PARAMS = {
        'period': 14,
        'adx_threshold': 25,
        'position_size_pct': 10,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
    }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(merged_params)
        
        self.period = self.params['period']
        self.adx_threshold = self.params['adx_threshold']
        self.position_size_pct = self.params['position_size_pct']
        self.stop_loss_pct = self.params['stop_loss_pct']
        self.take_profit_pct = self.params['take_profit_pct']
    
    def get_lookback(self) -> int:
        """Minimum bars needed for ADX calculation"""
        return self.period * 2 + 1
    
    def _calculate_adx(self, df: pd.DataFrame) -> tuple:
        """Calculate ADX, +DI, and -DI"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # +DM and -DM
        up_move = high.diff()
        down_move = -low.diff()
        
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
        
        # Smoothed TR, +DM, -DM
        atr = tr.rolling(window=self.period).mean()
        smooth_plus_dm = plus_dm.rolling(window=self.period).mean()
        smooth_minus_dm = minus_dm.rolling(window=self.period).mean()
        
        # +DI and -DI
        plus_di = 100 * (smooth_plus_dm / atr.replace(0, np.inf))
        minus_di = 100 * (smooth_minus_dm / atr.replace(0, np.inf))
        
        # DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(window=self.period).mean()
        
        return adx, plus_di, minus_di
    
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
        
        # Calculate ADX
        adx, plus_di, minus_di = self._calculate_adx(history)
        
        adx_current = adx.iloc[-1]
        adx_prev = adx.iloc[-2]
        plus_di_current = plus_di.iloc[-1]
        plus_di_prev = plus_di.iloc[-2]
        minus_di_current = minus_di.iloc[-1]
        minus_di_prev = minus_di.iloc[-2]
        
        current_price = bar['close']
        has_position = symbol in positions
        
        # Strong uptrend: ADX > threshold AND +DI > -DI AND +DI crossing above -DI
        strong_uptrend = (
            adx_current > self.adx_threshold and
            plus_di_current > minus_di_current and
            plus_di_prev <= minus_di_prev  # Crossover
        )
        
        # Strong downtrend or DI crossover down
        trend_weakening = (
            adx_current < adx_prev * 0.9 or  # ADX declining
            (minus_di_current > plus_di_current and minus_di_prev <= plus_di_prev)  # Bearish crossover
        )
        
        # Entry on strong uptrend
        if strong_uptrend and not has_position:
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
                    reason=f"Strong uptrend (ADX: {adx_current:.1f}, +DI: {plus_di_current:.1f} > -DI: {minus_di_current:.1f})"
                )
        
        # Exit
        if has_position:
            position = positions[symbol]
            
            if trend_weakening:
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
                    reason=f"Trend weakening (ADX: {adx_current:.1f})"
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
        if self.period < 2:
            return False
        if self.adx_threshold <= 0 or self.adx_threshold > 100:
            return False
        if self.position_size_pct <= 0 or self.position_size_pct > 100:
            return False
        return True
