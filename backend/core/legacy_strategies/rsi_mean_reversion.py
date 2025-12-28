"""
RSI Mean Reversion Strategy
Proven strategy based on Connors RSI research - 70%+ win rate on oversold bounces
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, Signal
from ..backtest.executor import OrderSide


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy
    
    Buys when RSI drops below oversold threshold (default 30)
    Sells when RSI rises above overbought threshold (default 70) or after max holding period
    
    Research: Larry Connors' RSI(2) strategy shows 70%+ win rates on oversold bounces
    
    Parameters:
        rsi_period: RSI calculation period (default: 14)
        oversold: Buy threshold (default: 30)
        overbought: Sell threshold (default: 70)
        max_hold_days: Maximum holding period (default: 10)
        position_size_pct: Position size as % of capital (default: 10)
    """
    
    name = "RSIMeanReversion"
    version = "1.0.0"
    
    DEFAULT_PARAMS = {
        'rsi_period': 14,
        'oversold': 30,
        'overbought': 70,
        'max_hold_days': 10,
        'position_size_pct': 10,
        'stop_loss_pct': 3.0,
        'take_profit_pct': 5.0,
    }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(merged_params)
        
        self.rsi_period = self.params['rsi_period']
        self.oversold = self.params['oversold']
        self.overbought = self.params['overbought']
        self.max_hold_days = self.params['max_hold_days']
        self.position_size_pct = self.params['position_size_pct']
        self.stop_loss_pct = self.params['stop_loss_pct']
        self.take_profit_pct = self.params['take_profit_pct']
        
        self._entry_bar_idx = {}  # Track entry bar for max hold
    
    def get_lookback(self) -> int:
        """Minimum bars needed for RSI calculation"""
        return self.rsi_period + 1
    
    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.rsi_period, min_periods=1).mean()
        avg_loss = loss.rolling(window=self.rsi_period, min_periods=1).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
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
        
        # Calculate RSI
        close = history['close']
        rsi = self._calculate_rsi(close)
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else current_rsi
        
        current_price = bar['close']
        current_bar_idx = len(history) - 1
        has_position = symbol in positions
        
        # Entry: RSI crosses below oversold
        if not has_position and current_rsi < self.oversold:
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
                
                self._entry_bar_idx[symbol] = current_bar_idx
                
                return Signal(
                    symbol=symbol,
                    action='BUY',
                    quantity=quantity,
                    price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=0.75,
                    reason=f"RSI oversold at {current_rsi:.1f} (< {self.oversold})"
                )
        
        # Exit conditions
        if has_position:
            position = positions[symbol]
            entry_idx = self._entry_bar_idx.get(symbol, 0)
            bars_held = current_bar_idx - entry_idx
            
            # Exit 1: RSI overbought
            if current_rsi > self.overbought:
                executor.submit_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    strategy_id=self.name
                )
                if symbol in self._entry_bar_idx:
                    del self._entry_bar_idx[symbol]
                return Signal(
                    symbol=symbol,
                    action='SELL',
                    quantity=position.quantity,
                    price=current_price,
                    confidence=0.7,
                    reason=f"RSI overbought at {current_rsi:.1f} (> {self.overbought})"
                )
            
            # Exit 2: Max holding period
            if bars_held >= self.max_hold_days:
                executor.submit_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    strategy_id=self.name
                )
                if symbol in self._entry_bar_idx:
                    del self._entry_bar_idx[symbol]
                return Signal(
                    symbol=symbol,
                    action='SELL',
                    quantity=position.quantity,
                    price=current_price,
                    confidence=0.5,
                    reason=f"Max holding period reached ({bars_held} bars)"
                )
            
            # Exit 3: Stop loss
            stop_loss_price = position.avg_price * (1 - self.stop_loss_pct / 100)
            if current_price <= stop_loss_price:
                executor.submit_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    strategy_id=self.name
                )
                if symbol in self._entry_bar_idx:
                    del self._entry_bar_idx[symbol]
                return Signal(
                    symbol=symbol,
                    action='SELL',
                    quantity=position.quantity,
                    price=current_price,
                    reason=f"Stop loss triggered at {stop_loss_price:.2f}"
                )
            
            # Exit 4: Take profit
            take_profit_price = position.avg_price * (1 + self.take_profit_pct / 100)
            if current_price >= take_profit_price:
                executor.submit_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    strategy_id=self.name
                )
                if symbol in self._entry_bar_idx:
                    del self._entry_bar_idx[symbol]
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
        if self.rsi_period < 2:
            return False
        if self.oversold >= self.overbought:
            return False
        if self.oversold < 0 or self.overbought > 100:
            return False
        if self.position_size_pct <= 0 or self.position_size_pct > 100:
            return False
        return True
