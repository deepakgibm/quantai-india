"""
Unified Risk Engine
Centralized position sizing and stop loss calculations.
"""

from typing import Optional, Dict, Any

from core.risk.risk_manager import RiskManager, RiskConfig, RiskMode


class UnifiedRiskManager:
    """
    Central risk control module.
    Encapsulates stop levels, targets, position sizing calculations, and concentration caps.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self.manager = RiskManager(self.config)

    def calculate_stops_and_size(
        self,
        equity: float,
        price: float,
        risk_pct: float = 2.0,
        risk_mode: str = "percent_capital",
        atr: Optional[float] = None,
        stop_loss_override: Optional[float] = None,
        take_profit_multiplier: float = 2.0,
        max_concentration_pct: float = 10.0
    ) -> Dict[str, Any]:
        """
        Compute position quantity, stop-loss and take-profit target prices.
        """
        # Convert string to RiskMode enum
        try:
            mode_enum = RiskMode(risk_mode)
        except ValueError:
            mode_enum = RiskMode.PERCENT_OF_CAPITAL

        # Default stop loss if not provided
        if stop_loss_override:
            sl = stop_loss_override
        elif atr and atr > 0:
            sl = price - (atr * self.config.atr_multiplier)
        else:
            sl = price * 0.98  # Default 2% stop loss

        # Calculate position size
        size_res = self.manager.calculate_position_size(
            account_equity=equity,
            entry_price=price,
            stop_loss=sl,
            risk_per_trade_pct=risk_pct,
            max_position_size_pct=max_concentration_pct,
            method=mode_enum,
            atr=atr or (price * 0.02)
        )

        # Calculate take profit based on risk-reward multiplier
        risk_distance = abs(price - size_res.stop_loss)
        tp = price + (risk_distance * take_profit_multiplier)

        return {
            "quantity": size_res.quantity,
            "amount": size_res.amount,
            "stop_loss": size_res.stop_loss,
            "take_profit": tp,
            "risk_per_trade": size_res.risk_per_trade,
            "position_pct": size_res.position_pct
        }
