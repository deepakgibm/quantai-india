"""
Replay Engine Infrastructure
Implements sequential stepping and historical playback simulation.
"""

import pandas as pd
from typing import Dict, Any, Optional
from ..strategy.base import UnifiedStrategy, SignalResult
from ..portfolio.tracker import PortfolioTracker
from ..risk.manager import UnifiedRiskManager

# Cost structures
from core.backtest.costs import CostCalculator, CostConfig, OrderSide


class HistoricalReplayEngine:
    """
    Replay-ready simulation runner.
    Allows stepped sequential walk-through of price ticks/candles.
    """

    def __init__(
        self,
        strategy: UnifiedStrategy,
        df: pd.DataFrame,
        initial_capital: float = 1000000.0,
        cost_config: Optional[CostConfig] = None
    ):
        self.strategy = strategy
        self.df = strategy.preload_indicators(df)
        self.initial_capital = initial_capital
        
        self.portfolio = PortfolioTracker(initial_capital)
        self.cost_calculator = CostCalculator(cost_config or CostConfig())
        self.risk_manager = UnifiedRiskManager()
        
        self.current_idx = 0
        self.max_idx = len(df)
        self.history_timestamps = []
        self.equity_history = []
        self.pending_orders = []

    def has_next(self) -> bool:
        return self.current_idx < self.max_idx

    def step(self) -> Dict[str, Any]:
        """
        Processes a single candle/bar.
        Moves simulation forward by one step.
        """
        if not self.has_next():
            return {"status": "completed", "portfolio": self.get_state()}

        bar = self.df.iloc[self.current_idx]
        timestamp = bar['timestamp']
        close_price = float(bar['close'])
        open_price = float(bar['open'])
        
        self.history_timestamps.append(timestamp)

        # 1. Execute orders placed on the previous bar (executed at current bar's open)
        for order in self.pending_orders:
            symbol = order["symbol"]
            side = order["side"]
            qty = order["quantity"]
            
            slip = open_price * self.cost_calculator.config.slippage_rate
            fill_price = open_price + slip if side == OrderSide.BUY else open_price - slip
            
            costs = self.cost_calculator.calculate(fill_price, qty, side, is_intraday=False)

            if side == OrderSide.BUY:
                self.portfolio.enter_position(
                    symbol=symbol,
                    quantity=qty,
                    price=fill_price,
                    timestamp=timestamp,
                    bar_idx=self.current_idx,
                    stop_loss=order.get("stop_loss"),
                    take_profit=order.get("take_profit"),
                    txn_cost=costs.total
                )
            else:
                self.portfolio.exit_position(
                    symbol=symbol,
                    price=fill_price,
                    timestamp=timestamp,
                    bar_idx=self.current_idx,
                    txn_cost=costs.total,
                    reason=order.get("reason", "SIGNAL")
                )

        self.pending_orders.clear()

        # 2. Mark-to-market
        self.portfolio.update_mark_to_market({"STOCK": close_price})

        # 3. Check active risk
        risk_triggered = None
        if "STOCK" in self.portfolio.positions:
            pos = self.portfolio.positions["STOCK"]
            risk_sig = self.strategy.evaluate_risk(bar, pos, {})
            
            if pos.take_profit and bar['high'] >= pos.take_profit:
                risk_sig = SignalResult(
                    timestamp=timestamp,
                    signal=SignalType.EXIT,
                    price=pos.take_profit,
                    reason="TAKE_PROFIT_TRIGGERED"
                )

            if risk_sig and risk_sig.signal == SignalType.EXIT:
                risk_triggered = risk_sig
                self.pending_orders.append({
                    "symbol": "STOCK",
                    "side": OrderSide.SELL,
                    "quantity": pos.quantity,
                    "reason": risk_sig.reason
                })
                # Set temporary quantity zero to prevent duplicate trades
                self.portfolio.positions["STOCK"].quantity = 0

        # 4. Generate next signals if no active risk occurred
        signal = None
        if not risk_triggered:
            history = self.df.iloc[:self.current_idx+1]
            signal = self.strategy.on_bar(bar, history, self.portfolio.positions, self)
            
            if "STOCK" not in self.portfolio.positions and signal and signal.signal == SignalType.BUY:
                atr = bar.get("atr") if "atr" in bar else (close_price * 0.02)
                stops_res = self.risk_manager.calculate_stops_and_size(
                    equity=self.portfolio.get_equity(),
                    price=close_price,
                    risk_pct=2.0,
                    risk_mode="percent_capital",
                    atr=atr
                )
                if stops_res["quantity"] > 0:
                    self.pending_orders.append({
                        "symbol": "STOCK",
                        "side": OrderSide.BUY,
                        "quantity": stops_res["quantity"],
                        "stop_loss": stops_res["stop_loss"],
                        "take_profit": stops_res["take_profit"],
                        "reason": "REPLAY_ENTRY"
                    })
            elif "STOCK" in self.portfolio.positions and signal and (signal.signal == SignalType.SELL or signal.signal == SignalType.EXIT):
                pos = self.portfolio.positions["STOCK"]
                self.pending_orders.append({
                    "symbol": "STOCK",
                    "side": OrderSide.SELL,
                    "quantity": pos.quantity,
                    "reason": "REPLAY_EXIT"
                })

        self.equity_history.append(self.portfolio.get_equity())
        self.current_idx += 1

        return {
            "status": "active",
            "current_bar": {
                "timestamp": str(timestamp),
                "open": open_price,
                "high": float(bar['high']),
                "low": float(bar['low']),
                "close": close_price,
                "volume": float(bar['volume'])
            },
            "signal": signal.to_dict() if signal else None,
            "risk_triggered": risk_triggered.to_dict() if risk_triggered else None,
            "portfolio": self.get_state()
        }

    def get_state(self) -> Dict[str, Any]:
        pos_list = []
        for sym, pos in self.portfolio.positions.items():
            if pos.quantity > 0:
                pos_list.append({
                    "symbol": sym,
                    "quantity": pos.quantity,
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "stop_loss": pos.stop_loss,
                    "take_profit": pos.take_profit
                })
        return {
            "cash": round(self.portfolio.cash, 2),
            "equity": round(self.portfolio.get_equity(), 2),
            "positions": pos_list,
            "trades_count": len(self.portfolio.trades),
            "current_step": self.current_idx,
            "total_steps": self.max_idx
        }
