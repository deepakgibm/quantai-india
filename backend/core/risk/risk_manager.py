import logging
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RiskConfig:
    """Configuration for risk management"""
    max_concentration: float = 0.20  # Max 20% per symbol
    risk_per_trade: float = 0.01    # Risk 1% of equity per trade
    atr_multiplier: float = 2.0      # 2x ATR for stop loss
    trailing_stop: bool = True
    active: bool = True

class RiskMode(str, Enum):
    FIXED_QUANTITY = "fixed_quantity"
    FIXED_AMOUNT = "fixed_amount"
    PERCENT_OF_CAPITAL = "percent_capital"
    ATR_BASED = "atr_based"
    KELLY = "kelly"
    VOLATILITY = "volatility"

@dataclass
class PositionSizeResult:
    quantity: int
    amount: float
    risk_per_trade: float
    stop_loss: float
    position_pct: float
    method: str

class RiskManager:
    """
    Centralized Risk Management Engine.
    Handles stop-loss calculation, position sizing, and compliance.
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        
    def calculate_atr_stop(self, entry_price: float, atr_value: float, side: str = "BUY") -> float:
        """Calculate initial stop loss level based on ATR."""
        multiplier = self.config.atr_multiplier
        if side.upper() == "BUY":
            return entry_price - (atr_value * multiplier)
        else:
            return entry_price + (atr_value * multiplier)
            
    def calculate_position_size(
        self,
        account_equity: float,
        entry_price: float,
        stop_loss: float,
        risk_per_trade_pct: float = 2.0,
        max_position_size_pct: float = 10.0,
        method: RiskMode = RiskMode.PERCENT_OF_CAPITAL,
        **kwargs
    ) -> PositionSizeResult:
        """
        Calculates position size with institutional safety gates.
        
        Args:
            account_equity: Net liquidated value of the account
            entry_price: Planned entry price
            stop_loss: Stop loss price
            risk_per_trade_pct: % of equity to risk if stop is hit
            max_position_size_pct: Max concentration allowed for one ticker
            method: Sizing method for calculation
        """
        # Safety Gate: Negative Equity
        if account_equity <= 1.0:
            logger.error("RiskManager: Critical error - Account equity is zero or negative.")
            return PositionSizeResult(0, 0.0, 0.0, stop_loss, 0.0, method)

        # Safety Gate: Zero Distance Risk
        risk_distance = abs(entry_price - stop_loss)
        if risk_distance < 0.01:
            logger.warning(f"RiskManager: Risk distance too small ({risk_distance}). Using default 2% buffer.")
            risk_distance = entry_price * 0.02
            stop_loss = entry_price - risk_distance

        # 1. Calculate Maximum Risk Amount (Rupees)
        max_risk_amount = account_equity * (risk_per_trade_pct / 100.0)

        # 2. Base Quantity based on Risk Distance
        if method == RiskMode.KELLY:
            win_rate = kwargs.get('win_rate', 0.5)
            avg_win = kwargs.get('avg_win', 0.02)
            avg_loss = kwargs.get('avg_loss', 0.01)
            b = abs(avg_win / avg_loss) if avg_loss > 0 else 1.0
            kelly_f = (win_rate * b - (1 - win_rate)) / b if b > 0 else 0.0
            fraction = max(min(kelly_f * 0.25, max_position_size_pct/100.0), 0.0)
            quantity = int((account_equity * fraction) / entry_price)
        
        elif method == RiskMode.ATR_BASED:
            atr = kwargs.get('atr', entry_price * 0.02)
            multiplier = kwargs.get('atr_multiplier', 2.0)
            stop_distance = atr * multiplier
            quantity = int(max_risk_amount / stop_distance) if stop_distance > 0 else 0
            stop_loss = entry_price - stop_distance
            
        elif method == RiskMode.VOLATILITY:
            vol = kwargs.get('volatility', 0.20)
            target_vol = kwargs.get('target_volatility', 0.15)
            weight = min(target_vol / vol, max_position_size_pct / 100.0) if vol > 0 else 0.0
            quantity = int((account_equity * weight) / entry_price)
            
        else: # Default PERCENT_OF_CAPITAL
            quantity = int(max_risk_amount / risk_distance)

        # 3. Institutional Concentration Cap
        max_allowed_value = account_equity * (max_position_size_pct / 100.0)
        actual_value = quantity * entry_price
        
        if actual_value > max_allowed_value:
            logger.info(f"RiskManager: Concentration cap hit. Reducing {quantity} -> {int(max_allowed_value / entry_price)}")
            quantity = int(max_allowed_value / entry_price)
            actual_value = quantity * entry_price

        return PositionSizeResult(
            quantity=max(quantity, 0),
            amount=float(actual_value),
            risk_per_trade=float(quantity * abs(entry_price - stop_loss)),
            stop_loss=float(stop_loss),
            position_pct=float(actual_value / account_equity),
            method=method.value
        )

    def validate_order(self, symbol: str, quantity: int, price: float, current_equity: float, current_positions: Dict[str, Any]) -> bool:
        """Check if an order violates concentration or overall risk limits."""
        # Check if new order would exceed max concentration
        new_notional = quantity * price
        
        # Calculate current concentration for this symbol
        existing_notional = 0
        if symbol in current_positions:
            pos = current_positions[symbol]
            existing_notional = pos.quantity * price # simplified
            
        total_notional = existing_notional + new_notional
        
        if total_notional > (current_equity * self.config.max_concentration):
            logger.warning(f"Risk Violation: Concentration for {symbol} would exceed {self.config.max_concentration*100}%")
            return False
            
        return True
