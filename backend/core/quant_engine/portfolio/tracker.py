"""
Unified Portfolio and Position Tracker
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class PositionState:
    """Tracks state of an individual position."""
    def __init__(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        entry_time: Any,
        entry_bar_idx: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.entry_bar_idx = entry_bar_idx
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.current_price = entry_price
        self.unrealized_pnl = 0.0

    def update(self, price: float):
        self.current_price = price
        self.unrealized_pnl = (price - self.entry_price) * self.quantity


class PortfolioTracker:
    """
    Simulates portfolio state including cash, positions, and history of completed trades.
    """

    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, PositionState] = {}
        self.trades: List[Dict[str, Any]] = []

    def get_equity(self) -> float:
        """
        Calculate total equity = cash + sum(unrealized position values).
        """
        position_value = sum(pos.quantity * pos.current_price for pos in self.positions.values())
        return self.cash + position_value

    def enter_position(
        self,
        symbol: str,
        quantity: int,
        price: float,
        timestamp: Any,
        bar_idx: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        txn_cost: float = 0.0
    ) -> bool:
        """
        Record position entry. Deducts transaction costs and capital.
        """
        cost = (price * quantity) + txn_cost
        if cost > self.cash:
            # Insufficient buying power
            return False
            
        self.cash -= cost
        self.positions[symbol] = PositionState(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            entry_time=timestamp,
            entry_bar_idx=bar_idx,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        return True

    def exit_position(
        self,
        symbol: str,
        price: float,
        timestamp: Any,
        bar_idx: int,
        txn_cost: float = 0.0,
        reason: str = "SIGNAL"
    ) -> float:
        """
        Record position exit. Computes PnL and adds proceeds to cash.
        """
        if symbol not in self.positions:
            return 0.0
            
        pos = self.positions[symbol]
        gross_proceeds = price * pos.quantity
        net_proceeds = gross_proceeds - txn_cost
        
        self.cash += net_proceeds
        
        pnl = net_proceeds - ((pos.entry_price * pos.quantity) + txn_cost)
        pnl_percent = (pnl / (pos.entry_price * pos.quantity)) * 100.0
        
        trade = {
            "symbol": symbol,
            "entry_time": pos.entry_time,
            "exit_time": timestamp,
            "entry_price": pos.entry_price,
            "exit_price": price,
            "quantity": pos.quantity,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "holding_bars": bar_idx - pos.entry_bar_idx,
            "exit_reason": reason
        }
        self.trades.append(trade)
        del self.positions[symbol]
        return pnl

    def update_mark_to_market(self, prices: Dict[str, float]):
        """Update current asset prices and adjust unrealized PnL."""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].update(price)

    def reset(self):
        self.cash = self.initial_capital
        self.positions.clear()
        self.trades.clear()
