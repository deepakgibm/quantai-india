"""
Ichimoku Cloud Strategy
Complete trading system by Goichi Hosoda
"""

from typing import Dict, Any, Optional
import pandas as pd

from .base_strategy import BaseStrategy, Signal
from ..backtest.executor import OrderSide


class IchimokuStrategy(BaseStrategy):
    """
    Ichimoku Cloud Strategy
    
    Complete trading system using Tenkan-sen, Kijun-sen, and Kumo (cloud).
    
    Research: Goichi Hosoda's Ichimoku Kinko Hyo - "equilibrium chart at a glance"
    
    Parameters:
        tenkan_period: Tenkan-sen (conversion line) period (default: 9)
        kijun_period: Kijun-sen (base line) period (default: 26)
        senkou_b_period: Senkou Span B period (default: 52)
        position_size_pct: Position size as % of capital (default: 10)
    """
    
    name = "Ichimoku"
    version = "1.0.0"
    
    DEFAULT_PARAMS = {
        'tenkan_period': 9,
        'kijun_period': 26,
        'senkou_b_period': 52,
        'position_size_pct': 10,
        'stop_loss_pct': 3.0,
        'take_profit_pct': 6.0,
    }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(merged_params)
        
        self.tenkan_period = self.params['tenkan_period']
        self.kijun_period = self.params['kijun_period']
        self.senkou_b_period = self.params['senkou_b_period']
        self.position_size_pct = self.params['position_size_pct']
        self.stop_loss_pct = self.params['stop_loss_pct']
        self.take_profit_pct = self.params['take_profit_pct']
    
    def get_lookback(self) -> int:
        """Minimum bars needed for Ichimoku calculation"""
        return self.senkou_b_period + self.kijun_period + 1
    
    def _donchian_mid(self, high: pd.Series, low: pd.Series, period: int) -> pd.Series:
        """Calculate Donchian channel midline"""
        return (high.rolling(window=period).max() + low.rolling(window=period).min()) / 2
    
    def _calculate_ichimoku(self, df: pd.DataFrame) -> dict:
        """Calculate all Ichimoku components"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Tenkan-sen (Conversion Line) - 9-period mid
        tenkan = self._donchian_mid(high, low, self.tenkan_period)
        
        # Kijun-sen (Base Line) - 26-period mid
        kijun = self._donchian_mid(high, low, self.kijun_period)
        
        # Senkou Span A (Leading Span A) - average of Tenkan and Kijun
        senkou_a = (tenkan + kijun) / 2
        
        # Senkou Span B (Leading Span B) - 52-period mid
        senkou_b = self._donchian_mid(high, low, self.senkou_b_period)
        
        # For current bar, we use current cloud (not displaced)
        return {
            'tenkan': tenkan,
            'kijun': kijun,
            'senkou_a': senkou_a,
            'senkou_b': senkou_b,
        }
    
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
        
        # Calculate Ichimoku
        ichimoku = self._calculate_ichimoku(history)
        tenkan = ichimoku['tenkan']
        kijun = ichimoku['kijun']
        senkou_a = ichimoku['senkou_a']
        senkou_b = ichimoku['senkou_b']
        
        tenkan_current = tenkan.iloc[-1]
        tenkan_prev = tenkan.iloc[-2]
        kijun_current = kijun.iloc[-1]
        kijun_prev = kijun.iloc[-2]
        senkou_a_current = senkou_a.iloc[-1]
        senkou_b_current = senkou_b.iloc[-1]
        
        current_price = bar['close']
        has_position = symbol in positions
        
        # Cloud top and bottom
        cloud_top = max(senkou_a_current, senkou_b_current)
        cloud_bottom = min(senkou_a_current, senkou_b_current)
        
        # Bullish signal:
        # 1. Price above cloud
        # 2. Tenkan crosses above Kijun
        # 3. Cloud is bullish (Senkou A > Senkou B)
        price_above_cloud = current_price > cloud_top
        tenkan_cross_up = tenkan_prev <= kijun_prev and tenkan_current > kijun_current
        bullish_cloud = senkou_a_current > senkou_b_current
        
        strong_bullish = price_above_cloud and tenkan_cross_up and bullish_cloud
        
        # Bearish signal: opposite conditions
        price_below_cloud = current_price < cloud_bottom
        tenkan_cross_down = tenkan_prev >= kijun_prev and tenkan_current < kijun_current
        bearish_cloud = senkou_a_current < senkou_b_current
        
        strong_bearish = price_below_cloud and tenkan_cross_down
        
        # Entry
        if strong_bullish and not has_position:
            capital = executor.cash
            position_value = capital * (self.position_size_pct / 100)
            quantity = int(position_value / current_price)
            
            if quantity > 0:
                stop_loss = kijun_current  # Kijun as trailing stop
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
                    confidence=0.8,
                    reason=f"Ichimoku bullish (Price > Cloud, TK cross up)"
                )
        
        # Exit
        if has_position:
            position = positions[symbol]
            
            # Exit on bearish signal
            if strong_bearish:
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
                    reason="Ichimoku bearish (TK cross down)"
                )
            
            # Exit if price enters cloud (indecision)
            if cloud_bottom <= current_price <= cloud_top:
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
                    confidence=0.5,
                    reason="Price entered Kumo cloud (indecision)"
                )
            
            # Trailing stop using Kijun
            if current_price < kijun_current:
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
                    reason=f"Price below Kijun-sen ({kijun_current:.2f})"
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
        if self.tenkan_period >= self.kijun_period:
            return False
        if self.kijun_period >= self.senkou_b_period:
            return False
        if self.position_size_pct <= 0 or self.position_size_pct > 100:
            return False
        return True
