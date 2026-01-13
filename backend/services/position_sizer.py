"""
Position Sizing Engine
Calculates optimal position sizes based on risk parameters
"""
import numpy as np
import pandas as pd
from typing import Optional, Dict
from datetime import datetime, timedelta

from database import AsyncSessionLocal
from models_alpha import StockData
from sqlalchemy import select, desc


class PositionSizer:
    """Calculate optimal position sizes using various methods"""
    
    def __init__(self, account_value: float, risk_config: 'RiskConfig'):
        self.account_value = account_value
        self.risk_config = risk_config
    
    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate position size using Kelly Criterion
        
        Formula: f = (p * b - q) / b
        where:
            f = fraction of capital to bet
            p = probability of win
            b = ratio of avg_win to avg_loss
            q = probability of loss (1 - p)
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade size
            avg_loss: Average losing trade size
        
        Returns:
            Position size as fraction of account (capped at max_position_size)
        """
        if avg_loss == 0:
            return 0.0
        
        p = win_rate
        q = 1 - win_rate
        b = abs(avg_win / avg_loss)
        
        # Kelly percentage
        kelly_pct = (p * b - q) / b
        
        # Use fractional Kelly (typically 25-50% of full Kelly for safety)
        fractional_kelly = kelly_pct * 0.25
        
        # Cap at max position size
        return min(max(fraction al_kelly, 0), self.risk_config.max_position_size)
    
    async def atr_based_sizing(
        self,
        symbol: str,
        entry_price: float,
        atr_multiplier: Optional[float] = None
    ) -> Dict:
        """
        Calculate position size based on ATR (Average True Range)
        
        Risk per trade = account_value * risk_per_trade
        Position size = risk_per_trade / (ATR * atr_multiplier)
        
        Args:
            symbol: Stock symbol
            entry_price: Planned entry price
            atr_multiplier: Multiplier for ATR (default from config)
        
        Returns:
            Dict with position details
        """
        atr_multiplier = atr_multiplier or self.risk_config.atr_multiplier
        
        # Get recent ATR
        atr = await self._get_current_atr(symbol)
        
        if atr is None or atr == 0:
            # Fallback to fixed percentage if ATR unavailable
            return self.fixed_fractional(entry_price)
        
        # Calculate risk amount
        risk_amount = self.account_value * self.risk_config.risk_per_trade
        
        # Stop distance in price
        stop_distance = atr * atr_multiplier
        
        # Position size in shares
        shares = int(risk_amount / stop_distance)
        
        # Calculate actual position value
        position_value = shares * entry_price
        position_pct = position_value / self.account_value
        
        # Cap at max position size
        if position_pct > self.risk_config.max_position_size:
            max_value = self.account_value * self.risk_config.max_position_size
            shares = int(max_value / entry_price)
            position_value = shares * entry_price
            position_pct = position_value / self.account_value
        
        # Calculate stop loss price
        stop_loss = entry_price - stop_distance
        
        return {
            'shares': shares,
            'position_value': position_value,
            'position_pct': position_pct,
            'risk_amount': risk_amount,
            'stop_loss': stop_loss,
            'atr': atr,
            'stop_distance': stop_distance
        }
    
    def volatility_based(
        self,
        symbol: str,
        entry_price: float,
        volatility: float,
        target_volatility: float = 0.15
    ) -> Dict:
        """
        Calculate position size to target specific portfolio volatility
        
        Args:
            symbol: Stock symbol
            entry_price: Planned entry price
            volatility: Stock's volatility (annualized std dev)
            target_volatility: Target portfolio volatility
        
        Returns:
            Dict with position details
        """
        # Position weight to achieve target volatility
        # weight = target_vol / asset_vol
        if volatility == 0:
            return self.fixed_fractional(entry_price)
        
        weight = min(target_volatility / volatility, self.risk_config.max_position_size)
        
        position_value = self.account_value * weight
        shares = int(position_value / entry_price)
        
        return {
            'shares': shares,
            'position_value': shares * entry_price,
            'position_pct': weight,
            'volatility': volatility,
            'target_volatility': target_volatility
        }
    
    def fixed_fractional(
        self,
        entry_price: float,
        fraction: Optional[float] = None
    ) -> Dict:
        """
        Simple fixed fractional position sizing
        
        Args:
            entry_price: Planned entry price
            fraction: Fraction of account to allocate (default from config)
        
        Returns:
            Dict with position details
        """
        fraction = fraction or self.risk_config.max_position_size
        
        position_value = self.account_value * fraction
        shares = int(position_value / entry_price)
        
        return {
            'shares': shares,
            'position_value': shares * entry_price,
            'position_pct': fraction
        }
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        method: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Calculate position size using configured method
        
        Args:
            symbol: Stock symbol
            entry_price: Planned entry price
            method: Sizing method ('atr', 'kelly', 'fixed', 'volatility')
            **kwargs: Additional parameters for specific methods
        
        Returns:
            Dict with position sizing details
        """
        method = method or self.risk_config.position_sizing_method
        
        if method == 'kelly':
            # Need historical win rate and avg win/loss
            win_rate = kwargs.get('win_rate', 0.5)
            avg_win = kwargs.get('avg_win', 0.02)
            avg_loss = kwargs.get('avg_loss', 0.01)
            fraction = self.kelly_criterion(win_rate, avg_win, avg_loss)
            return self.fixed_fractional(entry_price, fraction)
        
        elif method == 'atr':
            return self.atr_based_sizing(symbol, entry_price)
        
        elif method == 'volatility':
            volatility = kwargs.get('volatility', 0.20)
            return self.volatility_based(symbol, entry_price, volatility)
        
        else:  # 'fixed' or default
            return self.fixed_fractional(entry_price)
    
    async def _get_current_atr(self, symbol: str, period: int = 14) -> Optional[float]:
        """Get current ATR value from database"""
        try:
            async with AsyncSessionLocal() as session:
                # Get recent data
                result = await session.execute(
                    select(StockData)
                    .where(StockData.symbol == symbol)
                    .order_by(desc(StockData.timestamp))
                    .limit(period + 1)
                )
                data = result.scalars().all()
                
                if len(data) < period:
                    return None
                
                # Calculate ATR
                df = pd.DataFrame([{
                    'high': d.high,
                    'low': d.low,
                    'close': d.close
                } for d in reversed(data)])
                
                # True Range
                hl = df['high'] - df['low']
                hc = abs(df['high'] - df['close'].shift(1))
                lc = abs(df['low'] - df['close'].shift(1))
                
                tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
                atr = tr.ewm(span=period, adjust=False).mean().iloc[-1]
                
                return float(atr)
        
        except Exception as e:
            print(f"Error calculating ATR for {symbol}: {e}")
            return None


# Example usage

