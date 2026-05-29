"""
Layer 2: High-Fidelity Event-Driven Execution Engine
Runs stateful simulation sequentially bar-by-bar.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import time

from ..strategy.base import UnifiedStrategy, SignalType, SignalResult
from ..portfolio.tracker import PortfolioTracker
from ..risk.manager import UnifiedRiskManager
from ..metrics.calculator import UnifiedMetricsCalculator

# Re-use existing CostCalculator from the standard backtest module
from core.backtest.costs import CostCalculator, CostConfig, OrderSide


class EventDrivenExecutionEngine:
    """
    Fidelity-focused bar-by-bar execution simulator.
    Simulates realistic order fills at next bar open, slippage, and NSE brokerage.
    """

    def __init__(self, initial_capital: float = 1000000.0, cost_config: Optional[CostConfig] = None):
        self.initial_capital = initial_capital
        self.cost_calculator = CostCalculator(cost_config or CostConfig())
        self.risk_manager = UnifiedRiskManager()

    def run(
        self,
        strategy: UnifiedStrategy,
        df: pd.DataFrame,
        risk_pct: float = 2.0,
        risk_mode: str = "percent_capital"
    ) -> Dict[str, Any]:
        """
        Runs the bar-by-bar sequential backtest.
        """
        start_time = time.time()

        # 1. Preload strategy technical indicators
        df_indicators = strategy.preload_indicators(df)
        
        # Initialize portfolio state
        portfolio = PortfolioTracker(self.initial_capital)
        equity_curve = [self.initial_capital]
        timestamps = []

        # Order queue: stores orders placed on current bar, executed on next bar
        pending_orders: List[Dict[str, Any]] = []

        # Loop sequentially over each bar
        for idx in range(len(df_indicators)):
            bar = df_indicators.iloc[idx]
            timestamp = bar['timestamp']
            close_price = float(bar['close'])
            open_price = float(bar['open'])
            timestamps.append(timestamp)

            # --- A. EXECUTE PENDING ORDERS (At next-bar open) ---
            for order in pending_orders:
                symbol = order["symbol"]
                side = order["side"]
                qty = order["quantity"]
                
                # Slippage model on Open price
                slip = open_price * self.cost_calculator.config.slippage_rate
                fill_price = open_price + slip if side == OrderSide.BUY else open_price - slip
                
                # Transaction charges
                costs = self.cost_calculator.calculate(
                    price=fill_price,
                    quantity=qty,
                    side=side,
                    is_intraday=False
                )

                if side == OrderSide.BUY:
                    portfolio.enter_position(
                        symbol=symbol,
                        quantity=qty,
                        price=fill_price,
                        timestamp=timestamp,
                        bar_idx=idx,
                        stop_loss=order.get("stop_loss"),
                        take_profit=order.get("take_profit"),
                        txn_cost=costs.total
                    )
                else:
                    portfolio.exit_position(
                        symbol=symbol,
                        price=fill_price,
                        timestamp=timestamp,
                        bar_idx=idx,
                        txn_cost=costs.total,
                        reason=order.get("reason", "SIGNAL")
                    )

            # Clear executed pending list
            pending_orders.clear()

            # --- B. UPDATE PORTFOLIO MARK-TO-MARKET ---
            portfolio.update_mark_to_market({"STOCK": close_price})

            # --- C. CHECK ACTIVE POSITION RISK (Stop Loss / Take Profit) ---
            if "STOCK" in portfolio.positions:
                pos = portfolio.positions["STOCK"]
                # Run standard risk assessment using strategy or manager
                risk_sig = strategy.evaluate_risk(bar, pos, {})
                
                # Check Take Profit
                if pos.take_profit and bar['high'] >= pos.take_profit:
                    risk_sig = SignalResult(
                        timestamp=timestamp,
                        signal=SignalType.EXIT,
                        price=pos.take_profit,
                        reason="TAKE_PROFIT_TRIGGERED"
                    )

                if risk_sig and risk_sig.signal == SignalType.EXIT:
                    pending_orders.append({
                        "symbol": "STOCK",
                        "side": OrderSide.SELL,
                        "quantity": pos.quantity,
                        "reason": risk_sig.reason
                    })
                    # Mark to avoid double evaluation
                    portfolio.positions["STOCK"].quantity = 0

            # --- D. EVALUATE STRATEGY ENTRY / EXIT RULES ---
            if "STOCK" not in portfolio.positions and not pending_orders:
                # Look for buying opportunities
                history = df_indicators.iloc[:idx+1]
                sig_res = strategy.on_bar(bar, history, portfolio.positions, self)
                if sig_res and sig_res.signal == SignalType.BUY:
                    # Calculate risk-managed sizing
                    # Fetch ATR or defaults
                    atr = bar.get("atr") if "atr" in bar else (close_price * 0.02)
                    stops_res = self.risk_manager.calculate_stops_and_size(
                        equity=portfolio.get_equity(),
                        price=close_price,
                        risk_pct=risk_pct,
                        risk_mode=risk_mode,
                        atr=atr
                    )
                    
                    if stops_res["quantity"] > 0:
                        pending_orders.append({
                            "symbol": "STOCK",
                            "side": OrderSide.BUY,
                            "quantity": stops_res["quantity"],
                            "stop_loss": stops_res["stop_loss"],
                            "take_profit": stops_res["take_profit"],
                            "reason": "STRATEGY_ENTRY"
                        })
            
            elif "STOCK" in portfolio.positions and portfolio.positions["STOCK"].quantity > 0 and not pending_orders:
                # Look for exit signs
                history = df_indicators.iloc[:idx+1]
                sig_res = strategy.on_bar(bar, history, portfolio.positions, self)
                if sig_res and (sig_res.signal == SignalType.SELL or sig_res.signal == SignalType.EXIT):
                    pos = portfolio.positions["STOCK"]
                    pending_orders.append({
                        "symbol": "STOCK",
                        "side": OrderSide.SELL,
                        "quantity": pos.quantity,
                        "reason": "STRATEGY_EXIT"
                    })

            # Record final equity for this bar
            equity_curve.append(portfolio.get_equity())

        # Clean final trailing point
        if len(equity_curve) > len(timestamps):
            equity_curve = equity_curve[1:]

        # Calculate final statistics
        duration = time.time() - start_time
        ts_list = [str(x) for x in timestamps]
        metrics = UnifiedMetricsCalculator.calculate_performance_summary(
            trades=portfolio.trades,
            equity_curve=equity_curve,
            timestamps=ts_list,
            initial_capital=self.initial_capital
        )
        
        metrics["run_time_seconds"] = round(duration, 4)
        return metrics
