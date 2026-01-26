"""
Position Manager and Risk Modes for Experiment Lab
Handles position sizing based on different risk models.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class RiskMode(str, Enum):
    """Position sizing risk modes."""
    FIXED_QUANTITY = "fixed_quantity"       # Fixed number of shares
    FIXED_AMOUNT = "fixed_amount"           # Fixed rupee amount per trade
    PERCENT_OF_CAPITAL = "percent_capital"  # Percentage of current capital
    ATR_BASED = "atr_based"                 # ATR-based dynamic sizing


@dataclass
class PositionSize:
    """Result of position sizing calculation."""
    quantity: int
    amount: float
    risk_per_trade: float
    stop_loss_distance: float
    position_value: float


class PositionSizer:
    """
    Calculates position sizes based on different risk modes.
    """
    
    def __init__(
        self,
        initial_capital: float,
        risk_mode: RiskMode = RiskMode.PERCENT_OF_CAPITAL,
        fixed_quantity: int = 100,
        fixed_amount: float = 100000,
        risk_percent: float = 2.0,  # 2% of capital per trade
        atr_risk_multiplier: float = 1.0
    ):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_mode = risk_mode
        self.fixed_quantity = fixed_quantity
        self.fixed_amount = fixed_amount
        self.risk_percent = risk_percent
        self.atr_risk_multiplier = atr_risk_multiplier
    
    def update_capital(self, new_capital: float):
        """Update current capital after trades."""
        self.current_capital = new_capital
    
    def calculate_position(
        self,
        entry_price: float,
        stop_loss: Optional[float] = None,
        atr: Optional[float] = None
    ) -> PositionSize:
        """
        Calculate position size based on risk mode.
        
        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price (optional)
            atr: Average True Range (optional, required for ATR mode)
            
        Returns:
            PositionSize with quantity and related metrics
        """
        if self.risk_mode == RiskMode.FIXED_QUANTITY:
            quantity = self.fixed_quantity
            amount = quantity * entry_price
            
        elif self.risk_mode == RiskMode.FIXED_AMOUNT:
            quantity = int(self.fixed_amount / entry_price)
            amount = quantity * entry_price
            
        elif self.risk_mode == RiskMode.PERCENT_OF_CAPITAL:
            amount = self.current_capital * (self.risk_percent / 100)
            quantity = int(amount / entry_price)
            amount = quantity * entry_price
            
        elif self.risk_mode == RiskMode.ATR_BASED:
            if atr is None:
                # Fallback to percent mode if no ATR
                amount = self.current_capital * (self.risk_percent / 100)
                quantity = int(amount / entry_price)
            else:
                # Risk amount per trade
                risk_amount = self.current_capital * (self.risk_percent / 100)
                # Stop distance is ATR * multiplier
                stop_distance = atr * self.atr_risk_multiplier
                # Quantity = Risk / Stop Distance
                quantity = int(risk_amount / stop_distance) if stop_distance > 0 else 0
            amount = quantity * entry_price
        
        else:
            quantity = 1
            amount = entry_price
        
        # Calculate stop loss distance
        if stop_loss:
            stop_loss_distance = abs(entry_price - stop_loss)
        elif atr:
            stop_loss_distance = atr * 2
        else:
            stop_loss_distance = entry_price * 0.02  # Default 2%
        
        # Risk per trade
        risk_per_trade = quantity * stop_loss_distance
        
        return PositionSize(
            quantity=max(quantity, 1),  # Minimum 1 share
            amount=amount,
            risk_per_trade=risk_per_trade,
            stop_loss_distance=stop_loss_distance,
            position_value=quantity * entry_price
        )
    
    def get_max_affordable_quantity(self, price: float) -> int:
        """Get maximum quantity that can be bought with current capital."""
        return int(self.current_capital / price)


__all__ = ['RiskMode', 'PositionSize', 'PositionSizer']
