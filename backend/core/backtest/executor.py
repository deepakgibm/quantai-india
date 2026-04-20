"""
Order Executor for Backtesting
Simulates order execution with realistic fills
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
import pandas as pd
import logging

from .costs import CostCalculator, OrderSide, TransactionCost
from core.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"


class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    """Represents a trading order"""
    id: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Execution details (filled after execution)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: float = 0.0
    transaction_cost: Optional[TransactionCost] = None
    filled_at: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    strategy_id: Optional[str] = None
    signal_bar_index: int = 0


@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    quantity: int
    avg_price: float
    side: OrderSide
    entry_time: datetime
    entry_bar_index: int
    unrealized_pnl: float = 0.0
    stop_loss: Optional[float] = None
    highest_price: float = 0.0  # Used for trailing stops
    
    def update_pnl(self, current_price: float) -> None:
        """Update unrealized P&L"""
        if self.side == OrderSide.BUY:
            self.unrealized_pnl = (current_price - self.avg_price) * self.quantity
            self.highest_price = max(self.highest_price, current_price)
        else:
            self.unrealized_pnl = (self.avg_price - current_price) * self.quantity
            self.highest_price = min(self.highest_price, current_price) if self.highest_price > 0 else current_price


@dataclass
class Trade:
    """Represents a completed round-trip trade"""
    id: str
    symbol: str
    side: OrderSide  # Entry side
    quantity: int
    entry_price: float
    entry_time: datetime
    entry_bar_index: int
    exit_price: float
    exit_time: datetime
    exit_bar_index: int
    gross_pnl: float
    transaction_costs: float
    net_pnl: float
    holding_bars: int
    return_pct: float


class Executor:
    """
    Simulates order execution for backtesting
    
    Features:
    - Next-bar execution (no lookahead)
    - Realistic slippage and costs
    - Position tracking
    - Trade logging
    """
    
    def __init__(
        self,
        initial_capital: float = 1000000.0,
        cost_calculator: Optional[CostCalculator] = None,
        is_intraday: bool = False
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.cost_calculator = cost_calculator or CostCalculator()
        self.risk_manager = RiskManager() # Default, can be updated later
        self.is_intraday = is_intraday
        
        # State
        self.positions: Dict[str, Position] = {}
        self.pending_orders: List[Order] = []
        self.filled_orders: List[Order] = []
        self.trades: List[Trade] = []
        self._order_counter = 0
        self._trade_counter = 0
        self._current_bar_index = 0
    
    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        strategy_id: Optional[str] = None
    ) -> Order:
        """
        Submit an order to be executed on next bar
        """
        self._order_counter += 1
        order = Order(
            id=f"ORD-{self._order_counter:06d}",
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            strategy_id=strategy_id,
            signal_bar_index=self._current_bar_index
        )
        self.pending_orders.append(order)
        logger.debug(f"Order submitted: {order.id} {side.value} {quantity} {symbol}")
        return order
    
    def process_bar(self, bar: pd.Series, bar_index: int) -> List[Order]:
        """
        Process pending orders against current bar
        Orders are filled at NEXT bar's open (next-bar execution)
        
        Args:
            bar: Current bar with OHLCV data
            bar_index: Index of current bar
            
        Returns:
            List of filled orders
        """
        self._current_bar_index = bar_index
        filled = []
        remaining = []
        
        for order in self.pending_orders:
            # Skip orders placed on current bar (next-bar rule)
            if order.signal_bar_index == bar_index:
                remaining.append(order)
                continue
            
            # Try to fill the order
            fill_price = self._get_fill_price(order, bar)
            
            if fill_price is not None:
                self._execute_order(order, fill_price, bar, bar_index)
                filled.append(order)
            else:
                remaining.append(order)
        
        self.pending_orders = remaining
        
        # Update unrealized P&L and Check Stops for all positions
        current_price = bar['close']
        for symbol, pos in list(self.positions.items()):
            pos.update_pnl(current_price)
            
            # Check for Stop Loss Trigger (simplified market execution at bar high/low)
            if pos.stop_loss:
                triggered = False
                if pos.side == OrderSide.BUY and bar['low'] <= pos.stop_loss:
                    triggered = True
                elif pos.side == OrderSide.SELL and bar['high'] >= pos.stop_loss:
                    triggered = True
                
                if triggered:
                    logger.info(f"Stop Loss Triggered for {symbol} at {pos.stop_loss:.2f}")
                    # Execute immediate exit
                    exit_order = Order(
                        id=f"SL-{self._order_counter:06d}",
                        symbol=symbol,
                        side=OrderSide.SELL if pos.side == OrderSide.BUY else OrderSide.BUY,
                        quantity=pos.quantity,
                        order_type=OrderType.MARKET,
                        signal_bar_index=bar_index
                    )
                    self._execute_order(exit_order, pos.stop_loss, bar, bar_index)
        
        return filled
    
    def _get_fill_price(self, order: Order, bar: pd.Series) -> Optional[float]:
        """
        Determine fill price based on order type and bar data
        Returns None if order cannot be filled
        """
        open_price = bar['open']
        high = bar['high']
        low = bar['low']
        
        if order.order_type == OrderType.MARKET:
            # Market orders fill at open with slippage
            slippage = open_price * self.cost_calculator.config.slippage_rate
            if order.side == OrderSide.BUY:
                return open_price + slippage
            else:
                return open_price - slippage
        
        elif order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY:
                # Buy limit fills if low <= limit price
                if low <= order.limit_price:
                    return min(open_price, order.limit_price)
            else:
                # Sell limit fills if high >= limit price
                if high >= order.limit_price:
                    return max(open_price, order.limit_price)
        
        elif order.order_type == OrderType.STOP_LOSS:
            if order.side == OrderSide.SELL:
                # Stop loss to sell triggers if low <= stop price
                if low <= order.stop_price:
                    return order.stop_price
            else:
                # Stop loss to buy triggers if high >= stop price
                if high >= order.stop_price:
                    return order.stop_price
        
        return None
    
    def _execute_order(
        self,
        order: Order,
        fill_price: float,
        bar: pd.Series,
        bar_index: int
    ) -> None:
        """Execute an order at the given price"""
        # Calculate transaction costs
        cost = self.cost_calculator.calculate(
            price=fill_price,
            quantity=order.quantity,
            side=order.side,
            is_intraday=self.is_intraday,
            avg_volume=bar.get('volume')
        )
        
        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = fill_price
        order.transaction_cost = cost
        order.filled_at = bar.name if hasattr(bar, 'name') else datetime.now()
        
        # Update cash and positions
        turnover = fill_price * order.quantity
        
        if order.side == OrderSide.BUY:
            self.cash -= (turnover + cost.total)
            self._add_to_position(order, bar_index)
        else:
            self.cash += (turnover - cost.total)
            self._close_position(order, bar, bar_index)
        
        self.filled_orders.append(order)
        logger.debug(f"Order filled: {order.id} @ {fill_price:.2f}, cost: {cost.total:.2f}")
    
    def _add_to_position(self, order: Order, bar_index: int) -> None:
        """Add to or create a position"""
        symbol = order.symbol
        
        if symbol in self.positions:
            pos = self.positions[symbol]
            # Average up/down
            total_qty = pos.quantity + order.quantity
            pos.avg_price = (pos.avg_price * pos.quantity + order.filled_price * order.quantity) / total_qty
            pos.quantity = total_qty
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=order.quantity,
                avg_price=order.filled_price,
                side=order.side,
                entry_time=order.filled_at,
                entry_bar_index=bar_index
            )
    
    def _close_position(self, order: Order, bar: pd.Series, bar_index: int) -> None:
        """Close or reduce a position, creating a trade record"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            logger.warning(f"Attempted to close non-existent position: {symbol}")
            return
        
        pos = self.positions[symbol]
        
        # Calculate trade P&L
        if pos.side == OrderSide.BUY:
            gross_pnl = (order.filled_price - pos.avg_price) * order.quantity
        else:
            gross_pnl = (pos.avg_price - order.filled_price) * order.quantity
        
        # Estimate entry costs
        entry_cost = self.cost_calculator.calculate(
            pos.avg_price, order.quantity, OrderSide.BUY, self.is_intraday
        )
        total_costs = entry_cost.total + order.transaction_cost.total
        net_pnl = gross_pnl - total_costs
        
        # Create trade record
        self._trade_counter += 1
        trade = Trade(
            id=f"TRD-{self._trade_counter:06d}",
            symbol=symbol,
            side=pos.side,
            quantity=order.quantity,
            entry_price=pos.avg_price,
            entry_time=pos.entry_time,
            entry_bar_index=pos.entry_bar_index,
            exit_price=order.filled_price,
            exit_time=order.filled_at,
            exit_bar_index=bar_index,
            gross_pnl=gross_pnl,
            transaction_costs=total_costs,
            net_pnl=net_pnl,
            holding_bars=bar_index - pos.entry_bar_index,
            return_pct=(net_pnl / (pos.avg_price * order.quantity)) * 100
        )
        self.trades.append(trade)
        
        # Update or remove position
        if order.quantity >= pos.quantity:
            del self.positions[symbol]
        else:
            pos.quantity -= order.quantity
    
    def get_equity(self, current_prices: Dict[str, float]) -> float:
        """Calculate total equity (cash + position values)"""
        equity = self.cash
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                equity += current_prices[symbol] * pos.quantity
        return equity
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for a symbol"""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """Check if there's an open position for symbol"""
        return symbol in self.positions
    
    def cancel_pending_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel pending orders, optionally for a specific symbol"""
        cancelled = 0
        remaining = []
        
        for order in self.pending_orders:
            if symbol is None or order.symbol == symbol:
                order.status = OrderStatus.CANCELLED
                cancelled += 1
            else:
                remaining.append(order)
        
        self.pending_orders = remaining
        return cancelled
    
    def reset(self) -> None:
        """Reset executor state"""
        self.cash = self.initial_capital
        self.positions.clear()
        self.pending_orders.clear()
        self.filled_orders.clear()
        self.trades.clear()
        self._order_counter = 0
        self._trade_counter = 0
        self._current_bar_index = 0
