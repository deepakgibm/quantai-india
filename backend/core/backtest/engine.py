"""
Backtesting Engine
Main orchestrator for running backtests with strategies
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass, field
import hashlib
import json
import logging

from .data_handler import DataHandler
from .executor import Executor, Trade
from .costs import CostCalculator, CostConfig

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for a backtest run"""
    symbol: str
    start_date: date
    end_date: date
    initial_capital: float = 1000000.0
    is_intraday: bool = False
    cost_config: Optional[CostConfig] = None


@dataclass
class BacktestMetrics:
    """Performance metrics from a backtest"""
    # Returns
    total_return: float
    total_return_pct: float
    cagr: float
    
    # Risk
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Trades
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    avg_trade_pnl: float
    largest_win: float
    largest_loss: float
    avg_holding_bars: float
    
    # Equity
    final_equity: float
    peak_equity: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_return': round(self.total_return, 2),
            'total_return_pct': round(self.total_return_pct, 2),
            'cagr': round(self.cagr, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'max_drawdown_pct': round(self.max_drawdown_pct, 2),
            'sharpe_ratio': round(self.sharpe_ratio, 3),
            'sortino_ratio': round(self.sortino_ratio, 3),
            'calmar_ratio': round(self.calmar_ratio, 3),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate, 2),
            'profit_factor': round(self.profit_factor, 2),
            'avg_win': round(self.avg_win, 2),
            'avg_loss': round(self.avg_loss, 2),
            'avg_trade_pnl': round(self.avg_trade_pnl, 2),
            'largest_win': round(self.largest_win, 2),
            'largest_loss': round(self.largest_loss, 2),
            'avg_holding_bars': round(self.avg_holding_bars, 1),
            'final_equity': round(self.final_equity, 2),
            'peak_equity': round(self.peak_equity, 2),
        }


@dataclass
class BacktestResult:
    """Complete result of a backtest run"""
    # Configuration
    config: BacktestConfig
    strategy_name: str
    strategy_params: Dict[str, Any]
    strategy_hash: str
    
    # Results
    metrics: BacktestMetrics
    trades: List[Trade]
    equity_curve: pd.DataFrame
    
    # Metadata
    run_id: str
    run_at: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API"""
        return {
            'run_id': self.run_id,
            'strategy_name': self.strategy_name,
            'strategy_params': self.strategy_params,
            'strategy_hash': self.strategy_hash,
            'config': {
                'symbol': self.config.symbol,
                'start_date': self.config.start_date.isoformat(),
                'end_date': self.config.end_date.isoformat(),
                'initial_capital': self.config.initial_capital,
                'is_intraday': self.config.is_intraday,
            },
            'metrics': self.metrics.to_dict(),
            'trade_count': len(self.trades),
            'run_at': self.run_at.isoformat(),
            'duration_seconds': round(self.duration_seconds, 2),
        }


class BacktestEngine:
    """
    Production-grade backtesting engine
    
    Features:
    - Candle-by-candle execution
    - Next-bar fills (no lookahead)
    - Realistic transaction costs
    - Same strategy interface as live trading
    - Deterministic results
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        
        cost_config = config.cost_config or CostConfig()
        self.cost_calculator = CostCalculator(cost_config)
        
        self.data_handler = DataHandler()
        self.executor = Executor(
            initial_capital=config.initial_capital,
            cost_calculator=self.cost_calculator,
            is_intraday=config.is_intraday
        )
        
        self._equity_history: List[Dict] = []
        self._run_counter = 0
    
    def load_data(self, df: pd.DataFrame) -> None:
        """Load data from DataFrame"""
        self.data_handler.load_from_dataframe(df, self.config.symbol)
    
    def load_data_from_db(self, db_session: Any) -> None:
        """Load data from database"""
        self.data_handler.load_from_database(
            symbol=self.config.symbol,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            db_session=db_session
        )
    
    def run(self, strategy: Any) -> BacktestResult:
        """
        Run backtest with a strategy
        
        Args:
            strategy: Strategy instance with generate_signals method
            
        Returns:
            BacktestResult with all metrics and trades
        """
        import time
        start_time = time.time()
        
        # Reset state
        self.executor.reset()
        self._equity_history.clear()
        self.data_handler.reset()
        
        # Generate strategy hash
        strategy_hash = self._generate_strategy_hash(strategy)
        
        # Run bar-by-bar simulation
        logger.info(f"Starting backtest: {strategy.__class__.__name__} on {self.config.symbol}")
        
        # Strategy initialization hook (e.g., for pre-calculating indicators)
        if hasattr(strategy, 'on_init'):
            strategy.on_init(self.data_handler.data)
        
        # Run bar-by-bar simulation
        for bar_index, bar in enumerate(self.data_handler):
            # 1. Process any pending orders from previous bar
            filled_orders = self.executor.process_bar(bar, bar_index)
            
            # 2. Get historical data up to current bar (no lookahead)
            history = self.data_handler.get_history(lookback=200)
            
            # 3. Generate signals from strategy
            signals = strategy.on_bar(
                bar=bar,
                history=history,
                positions=self.executor.positions,
                executor=self.executor
            )
            
            # 4. Record equity
            current_price = bar['close']
            equity = self.executor.get_equity({self.config.symbol: current_price})
            
            self._equity_history.append({
                'date': bar.name if hasattr(bar, 'name') else datetime.now(),
                'equity': equity,
                'cash': self.executor.cash,
                'position_value': equity - self.executor.cash,
                'bar_index': bar_index
            })
        
        # Calculate metrics
        equity_df = pd.DataFrame(self._equity_history)
        equity_df.set_index('date', inplace=True)
        
        metrics = self._calculate_metrics(equity_df)
        
        # Generate run ID
        self._run_counter += 1
        run_id = f"BT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._run_counter:04d}"
        
        duration = time.time() - start_time
        
        result = BacktestResult(
            config=self.config,
            strategy_name=strategy.__class__.__name__,
            strategy_params=getattr(strategy, 'params', {}),
            strategy_hash=strategy_hash,
            metrics=metrics,
            trades=self.executor.trades.copy(),
            equity_curve=equity_df,
            run_id=run_id,
            duration_seconds=duration
        )
        
        logger.info(f"Backtest complete: {len(self.executor.trades)} trades, "
                    f"Return: {metrics.total_return_pct:.2f}%, "
                    f"Sharpe: {metrics.sharpe_ratio:.2f}")
        
        return result
    
    def _calculate_metrics(self, equity_df: pd.DataFrame) -> BacktestMetrics:
        """Calculate all performance metrics"""
        equity = equity_df['equity'].values
        trades = self.executor.trades
        
        initial = self.config.initial_capital
        final = equity[-1] if len(equity) > 0 else initial
        
        # Returns
        total_return = final - initial
        total_return_pct = (total_return / initial) * 100
        
        # CAGR
        if len(equity_df) > 1:
            years = (equity_df.index[-1] - equity_df.index[0]).days / 365.25
            if years > 0:
                cagr = ((final / initial) ** (1 / years) - 1) * 100
            else:
                cagr = 0.0
        else:
            cagr = 0.0
        
        # Drawdown
        peak = np.maximum.accumulate(equity)
        drawdown = equity - peak
        max_dd = abs(drawdown.min()) if len(drawdown) > 0 else 0
        max_dd_pct = (max_dd / peak[np.argmin(drawdown)]) * 100 if peak[np.argmin(drawdown)] > 0 else 0
        
        # Daily returns for Sharpe/Sortino
        returns = pd.Series(equity).pct_change().dropna()
        
        if len(returns) > 0 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe = 0.0
        
        # Sortino (downside deviation)
        downside = returns[returns < 0]
        if len(downside) > 0 and downside.std() > 0:
            sortino = (returns.mean() / downside.std()) * np.sqrt(252)
        else:
            sortino = 0.0
        
        # Calmar
        if max_dd_pct > 0:
            calmar = cagr / max_dd_pct
        else:
            calmar = 0.0
        
        # Trade analysis
        total_trades = len(trades)
        if total_trades > 0:
            pnls = [t.net_pnl for t in trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            
            winning_trades = len(wins)
            losing_trades = len(losses)
            win_rate = (winning_trades / total_trades) * 100
            
            avg_win = np.mean(wins) if wins else 0
            avg_loss = abs(np.mean(losses)) if losses else 0
            
            gross_profit = sum(wins)
            gross_loss = abs(sum(losses))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
            
            avg_trade = np.mean(pnls)
            largest_win = max(pnls) if pnls else 0
            largest_loss = min(pnls) if pnls else 0
            avg_holding = np.mean([t.holding_bars for t in trades])
        else:
            winning_trades = losing_trades = 0
            win_rate = avg_win = avg_loss = 0
            profit_factor = avg_trade = 0
            largest_win = largest_loss = 0
            avg_holding = 0
        
        return BacktestMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            cagr=cagr,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_trade_pnl=avg_trade,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_holding_bars=avg_holding,
            final_equity=final,
            peak_equity=max(peak) if len(peak) > 0 else initial
        )
    
    def _generate_strategy_hash(self, strategy: Any) -> str:
        """Generate deterministic hash for strategy version"""
        data = {
            'name': strategy.__class__.__name__,
            'params': getattr(strategy, 'params', {}),
            'code_version': getattr(strategy, 'version', '1.0.0')
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]
