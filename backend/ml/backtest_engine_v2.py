import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.services.feature_store import get_feature_store
from dataclasses import dataclass, asdict
import uuid
from database import SessionLocal
from backend.models import BacktestResult as DBBacktestResult

logger = logging.getLogger(__name__)

@dataclass
class Trade:
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    side: str # 'BUY' or 'SELL'
    size: float
    pnl_pct: float = 0.0
    pnl_val: float = 0.0
    status: str = 'OPEN' # 'OPEN', 'CLOSED'
    exit_reason: str = '' # 'TP', 'SL', 'TIME', 'SIGNAL'

class QuantAIBacktester:
    """
    Modern Backtesting Engine that consumes Feature Store Parquet data.
    Implements professional-grade trade simulation.
    """
    def __init__(self, 
                 initial_capital: float = 100000.0, 
                 risk_per_trade: float = 0.01, 
                 slippage_pct: float = 0.0005, 
                 comm_pct: float = 0.0002):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_per_trade = risk_per_trade # 1% of capital
        self.slippage_pct = slippage_pct
        self.comm_pct = comm_pct
        self.store = get_feature_store()
        self.run_id = str(uuid.uuid4())[:8]
        
    def run_backtest(self, 
                     symbol: str, 
                     timeframe: str, 
                     feature_version: str = "v1", 
                     strategy_logic: Any = None,
                     start_date: Any = None, 
                     end_date: Any = None) -> Dict[str, Any]:
        """
        Executes backtest for a specific symbol and timeframe.
        """
        # Ensure dates are strings for DuckDB
        if isinstance(start_date, (datetime, date)):
            start_date = start_date.isoformat()
        if isinstance(end_date, (datetime, date)):
            end_date = end_date.isoformat()
            
        # 1. Load Data from Feature Store via DuckDB
        df = self.store.query_features(
            symbols=[symbol], 
            timeframes=[timeframe], 
            feature_version=feature_version,
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            logger.warning(f"No data found for backtest: {symbol} {timeframe}")
            return {"error": "No data found"}
            
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 2. Simulation State
        trades: List[Trade] = []
        active_trade: Optional[Trade] = None
        equity_curve = [self.capital]
        
        # 3. Iterate through bars
        for i in range(len(df)):
            row = df.iloc[i]
            price = row['close']
            ts = row['timestamp']
            
            # Check for Exit if trade is active
            if active_trade:
                exit_result = self._check_exit(active_trade, row)
                if exit_result:
                    active_trade = self._close_trade(active_trade, exit_result['price'], ts, exit_result['reason'])
                    trades.append(active_trade)
                    active_trade = None
            
            # Check for Entry if no trade is active
            if not active_trade:
                signal = self._generate_signal(row, strategy_logic)
                if signal:
                    # Volatility-scaled sizing
                    # Size = (Capital * Risk%) / (Entry - StopDist)
                    # For simplicity, use ATR or 2% stop
                    stop_dist = price * 0.02 # 2% stop distance
                    if 'atr_14_pct' in row and not np.isnan(row['atr_14_pct']):
                        stop_dist = price * (row['atr_14_pct'] / 100.0) * 1.5
                    
                    risk_amt = self.capital * self.risk_per_trade
                    size = risk_amt / stop_dist if stop_dist > 0 else 0
                    
                    if size > 0:
                        # Entry with slippage
                        entry_price = price * (1 + self.slippage_pct) if signal == 'BUY' else price * (1 - self.slippage_pct)
                        active_trade = Trade(
                            symbol=symbol,
                            entry_time=ts,
                            exit_time=None,
                            entry_price=entry_price,
                            exit_price=None,
                            side=signal,
                            size=size,
                            status='OPEN'
                        )
            
            # Record Equity (approximate)
            current_equity = self.capital
            if active_trade:
                # Unrealized PnL
                pnl = (price - active_trade.entry_price) * active_trade.size if active_trade.side == 'BUY' else \
                      (active_trade.entry_price - price) * active_trade.size
                current_equity += pnl
            equity_curve.append(current_equity)
            
        # 4. Calculate Final Metrics
        return self._calculate_metrics(trades, equity_curve)

    def save_results_to_db(self, symbol: str, timeframe: str, start_date: str, end_date: str, metrics: Dict[str, Any]):
        """Persists backtest summary to PostgreSQL for auditing."""
        session = SessionLocal()
        try:
            db_result = DBBacktestResult(
                run_id=self.run_id,
                strategy_name="QuantAI_Redesign_V2",
                symbol=symbol,
                timeframe=timeframe,
                start_date=pd.to_datetime(start_date),
                end_date=pd.to_datetime(end_date),
                initial_capital=self.initial_capital,
                final_capital=self.capital,
                sharpe_ratio=metrics.get('sharpe_ratio', 0),
                max_drawdown=metrics.get('max_drawdown_pct', 0),
                total_trades=metrics.get('total_trades', 0),
                win_rate=metrics.get('win_rate', 0),
                metrics=metrics
            )
            session.add(db_result)
            session.commit()
            logger.info(f"💾 Backtest {self.run_id} saved to database.")
        except Exception as e:
            logger.error(f"Failed to save backtest results: {e}")
            session.rollback()
        finally:
            session.close()

    def _generate_signal(self, row, strategy_logic) -> Optional[str]:
        """
        Standardized signal generator using pre-computed features.
        Example: RSI < 30 -> BUY, RSI > 70 -> SELL
        """
        # Default Logic: RSI Mean Reversion
        if row['rsi_14'] < 0.3:
            return 'BUY'
        elif row['rsi_14'] > 0.7:
            return 'SELL'
        return None

    def _check_exit(self, trade: Trade, row) -> Optional[Dict]:
        """
        Check for SL/TP or Signal reversal.
        """
        price = row['close']
        
        # Simple Stop Loss / Take Profit
        if trade.side == 'BUY':
            if price <= trade.entry_price * 0.98: # 2% SL
                return {'price': trade.entry_price * 0.98, 'reason': 'SL'}
            if price >= trade.entry_price * 1.04: # 4% TP
                return {'price': trade.entry_price * 1.04, 'reason': 'TP'}
        else: # SELL
            if price >= trade.entry_price * 1.02:
                return {'price': trade.entry_price * 1.02, 'reason': 'SL'}
            if price <= trade.entry_price * 0.96:
                return {'price': trade.entry_price * 0.96, 'reason': 'TP'}
        
        return None

    def _close_trade(self, trade: Trade, price: float, ts: datetime, reason: str) -> Trade:
        # Exit with slippage
        exit_price = price * (1 - self.slippage_pct) if trade.side == 'BUY' else price * (1 + self.slippage_pct)
        
        pnl_val = (exit_price - trade.entry_price) * trade.size if trade.side == 'BUY' else \
                  (trade.entry_price - exit_price) * trade.size
        
        # Subtract commissions
        comm = (trade.entry_price * trade.size + exit_price * trade.size) * self.comm_pct
        pnl_val -= comm
        
        trade.exit_price = exit_price
        trade.exit_time = ts
        trade.pnl_val = pnl_val
        trade.pnl_pct = (pnl_val / (trade.entry_price * trade.size)) * 100
        trade.status = 'CLOSED'
        trade.exit_reason = reason
        
        self.capital += pnl_val
        return trade

    def _calculate_metrics(self, trades: List[Trade], equity_curve: List[float]) -> Dict[str, Any]:
        if not trades:
            return {"total_trades": 0, "final_equity": self.capital}
            
        pnls = [t.pnl_val for t in trades]
        wins = [p for p in pnls if p > 0]
        
        equity_series = pd.Series(equity_curve)
        returns = equity_series.pct_change().dropna()
        
        # Performance Metrics
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        win_rate = len(wins) / len(trades) * 100
        
        # Sharpe Ratio (Daily-like annualized)
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        
        # Max Drawdown
        roll_max = equity_series.cummax()
        drawdown = (equity_series - roll_max) / roll_max
        max_dd = drawdown.min() * 100
        
        return {
            "total_trades": len(trades),
            "win_rate": round(win_rate, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "final_equity": round(self.capital, 2),
            "equity_curve_raw": equity_curve,
            "trades": [asdict(t) for t in trades]
        }
