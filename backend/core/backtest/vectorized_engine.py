import polars as pl
import numpy as np
import os
import logging
import time
from datetime import datetime
from typing import Any, List

from .engine import BacktestConfig, BacktestMetrics, BacktestResult
from .executor import Trade, OrderSide
from .costs import CostCalculator

logger = logging.getLogger(__name__)

class VectorizedBacktestEngine:
    """
    High-performance backtesting engine using Polars.
    Expects strategy conditions to be vectorized.
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.data_dir = "data/parquet"
        
    def load_data(self) -> pl.DataFrame:
        """Loads data from Hive-partitioned Parquet datalake using Polars."""
        # Convert interval to minutes for path lookup
        tf = "1" if self.config.is_intraday else "1440"
        
        # Target specific folder to minimize schema conflicts across different symbols
        path = f"{self.data_dir}/symbol={self.config.symbol}/timeframe={tf}"
        
        if not os.path.exists(path):
            logger.error(f"Parquet directory not found: {path}")
            return pl.DataFrame()
            
        # Scan files in this specific partition
        # Using glob to get all files in subfolders (year/month/day)
        df = pl.scan_parquet(f"{path}/**/*.parquet")
        
        # Apply date filters lazily
        df = df.filter(
            (pl.col("candle_ts") >= datetime.combine(self.config.start_date, datetime.min.time())) &
            (pl.col("candle_ts") <= datetime.combine(self.config.end_date, datetime.max.time()))
        )
        
        # Ensure consistent types for OHLCV
        df = df.with_columns([
            pl.col("open").cast(pl.Float64),
            pl.col("high").cast(pl.Float64),
            pl.col("low").cast(pl.Float64),
            pl.col("close").cast(pl.Float64),
            pl.col("volume").cast(pl.Float64)
        ])
        
        return df.collect()

    def run(self, strategy: Any) -> BacktestResult:
        """Runs the vectorized backtest."""
        start_time = time.time()
        
        # 1. Load Data
        df = self.load_data()
        if df.is_empty():
            raise ValueError(f"No data found for {self.config.symbol}")
            
        # Ensure column matches: rename candle_ts to timestamp for engine logic
        if "candle_ts" in df.columns and "timestamp" not in df.columns:
            df = df.rename({"candle_ts": "timestamp"})
            
        # 2. Compute Indicators and Signals
        df = strategy.compute_indicators(df)
        df = strategy.generate_signals(df)
        
        # 3. Calculate Strategy Returns
        # ... logic ...
        df = df.with_columns([
            pl.col("close").pct_change().shift(-1).alias("next_ret")
        ]).fill_null(0)
        
        df = df.with_columns([
            pl.col("signal").shift(1).fill_null(0).alias("position")
        ])
        
        # 4. Compute Daily Returns and Equity Curve
        df = df.with_columns([
            (pl.col("position") * pl.col("close").pct_change()).alias("strategy_ret")
        ]).fill_null(0)
        
        df = df.with_columns([
            (1 + pl.col("strategy_ret")).cum_prod().alias("cum_ret")
        ])
        
        # 5. Apply Risk Management (Stops)
        if self.config.risk_config and self.config.risk_config.active:
            df = self._apply_vectorized_risk(df)
            
        # 6. Extract Trades
        trades = self._extract_trades(df)
        
        # 7. Calculate Metrics
        final_equity = self.config.initial_capital * df["cum_ret"][-1]
        peak_equity = self.config.initial_capital * df["cum_ret"].max()
        
        total_costs = sum(t.transaction_costs for t in trades)
        final_equity = final_equity - total_costs
        total_return = final_equity - self.config.initial_capital
        total_return_pct = (final_equity / self.config.initial_capital - 1) * 100
        
        # Sharpe (simplified)
        returns = df["strategy_ret"].to_numpy()
        sharpe = 0.0
        if returns.std() > 0:
            ann_factor = 252 * (375 if self.config.is_intraday else 1) # ~375 mins in NSE day
            sharpe = (returns.mean() / returns.std()) * np.sqrt(ann_factor)
            
        # Drawdown
        cum_ret = df["cum_ret"].to_numpy()
        running_max = np.maximum.accumulate(cum_ret)
        drawdown = cum_ret / running_max - 1
        max_dd_pct = abs(drawdown.min()) * 100
        
        # CAGR (Compound Annual Growth Rate)
        cagr = 0.0
        if len(df) > 1:
            try:
                timestamps = df["timestamp"].to_list()
                from datetime import datetime, date
                def to_dt(val):
                    if isinstance(val, (datetime, date)):
                        return val
                    return datetime.fromisoformat(str(val))
                start_dt = to_dt(timestamps[0])
                end_dt = to_dt(timestamps[-1])
                diff_days = (end_dt - start_dt).days if hasattr(end_dt - start_dt, "days") else (end_dt - start_dt).total_seconds() / 86400.0
                years = max(0.001, diff_days / 365.25)
                if final_equity > 0 and self.config.initial_capital > 0:
                    cagr = (final_equity / self.config.initial_capital) ** (1.0 / years) - 1.0
            except Exception as ex:
                logger.error(f"Error calculating CAGR: {ex}")
                cagr = total_return_pct / 100.0

        # Sortino Ratio (downside risk)
        sortino = 0.0
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            ann_factor = 252 * (375 if self.config.is_intraday else 1)
            sortino = (returns.mean() / downside_returns.std()) * np.sqrt(ann_factor)
        elif returns.mean() > 0:
            sortino = 99.0

        # Calmar Ratio
        calmar = 0.0
        if max_dd_pct > 0:
            calmar = (cagr * 100.0) / max_dd_pct

        # Trade statistics
        wins = [t.net_pnl for t in trades if t.net_pnl > 0]
        losses = [abs(t.net_pnl) for t in trades if t.net_pnl <= 0]
        
        profit_factor = 0.0
        if sum(losses) > 0:
            profit_factor = sum(wins) / sum(losses)
        elif sum(wins) > 0:
            profit_factor = 999.0
            
        avg_win = float(np.mean(wins)) if wins else 0.0
        avg_loss = float(np.mean(losses)) if losses else 0.0
        avg_trade_pnl = float(np.mean([t.net_pnl for t in trades])) if trades else 0.0
        largest_win = float(max(wins)) if wins else 0.0
        largest_loss = float(-max(losses)) if losses else 0.0
        avg_holding_bars = float(np.mean([t.holding_bars for t in trades])) if trades else 0.0

        metrics = BacktestMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            cagr=cagr * 100.0, # in percent
            max_drawdown=self.config.initial_capital * (max_dd_pct / 100.0),
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=(len(wins) / len(trades) * 100.0) if trades else 0.0,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_trade_pnl=avg_trade_pnl,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_holding_bars=avg_holding_bars,
            final_equity=final_equity,
            peak_equity=peak_equity
        )
        
        # 7. Build Result
        equity_curve_pd = df.select(["timestamp", "cum_ret"]).to_pandas()
        equity_curve_pd["equity"] = equity_curve_pd["cum_ret"] * self.config.initial_capital
        equity_curve_pd.set_index("timestamp", inplace=True)
        
        run_id = f"VBT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return BacktestResult(
            config=self.config,
            strategy_name=strategy.__class__.__name__,
            strategy_params=strategy.params,
            strategy_hash="vbt_hash",
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve_pd,
            run_id=run_id,
            duration_seconds=time.time() - start_time
        )

    def _apply_vectorized_risk(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply ATR stops and trailing stops in a vectorized manner."""
        risk = self.config.risk_config
        if not risk: return df
        
        # 1. Calculate ATR
        df = df.with_columns([
            (pl.col("high") - pl.col("low")).alias("tr1"),
            (pl.col("high") - pl.col("close").shift(1)).abs().alias("tr2"),
            (pl.col("low") - pl.col("close").shift(1)).abs().alias("tr3")
        ])
        df = df.with_columns(
            pl.max_horizontal(["tr1", "tr2", "tr3"]).alias("tr")
        )
        df = df.with_columns(
            pl.col("tr").rolling_mean(window_size=14).alias("atr")
        )
        
        # 2. Initial Stop Loss at Entry
        # Note: Vectorized stop-loss is an approximation. If price hits SL, we exit.
        # For simplicity, we filter signals based on price action
        
        if risk.trailing_stop:
            # Vectorized Trailing Stop Logic:
            # We need to identify bars where position == 1 and calculate high since entry
            # This is complex in pure Polars but achievable with cum_max if we reset at entries
            pass # TODO: Enhanced trailing stop logic implementation
            
        return df

    def _extract_trades(self, df: pl.DataFrame) -> List[Trade]:
        """Convert position transitions into Trade objects."""
        # Simple logic: entries where position 0->1, exits where 1->0
        df = df.with_columns([
            pl.col("position").diff().fill_null(0).alias("pos_change"),
            pl.arange(0, len(df)).alias("index")
        ])
        
        entries = df.filter(pl.col("pos_change") > 0)
        exits = df.filter(pl.col("pos_change") < 0)
        
        entries_dicts = entries.to_dicts()
        exits_dicts = exits.to_dicts()
        
        trades_list = []
        trade_count = 0
        
        calculator = CostCalculator()
        
        # Match entries and exits (assuming one at a time for simplicity)
        for i in range(min(len(entries_dicts), len(exits_dicts))):
            entry_row = entries_dicts[i]
            exit_row = exits_dicts[i]
            trade_count += 1
            
            entry_price = float(entry_row["close"])
            exit_price = float(exit_row["close"])
            
            qty = int(self.config.initial_capital * 0.1 / entry_price) # Use 10% of capital for test qty
            if qty < 1: qty = 1
            
            # Compute transaction costs using CostCalculator
            is_intraday = self.config.is_intraday
            entry_costs = calculator.calculate(entry_price, qty, OrderSide.BUY, is_intraday=is_intraday)
            exit_costs = calculator.calculate(exit_price, qty, OrderSide.SELL, is_intraday=is_intraday)
            total_costs = entry_costs.total + exit_costs.total
            
            gross_pnl = (exit_price - entry_price) * qty
            net_pnl = gross_pnl - total_costs
            ret_pct = (exit_price / entry_price - 1) * 100
            
            trade = Trade(
                id=f"TRD-{trade_count:06d}",
                symbol=self.config.symbol,
                side=OrderSide.BUY, # Strategy is long-only for RSI mean reversion
                quantity=qty,
                entry_price=entry_price,
                entry_time=entry_row["timestamp"],
                entry_bar_index=int(entry_row["index"]),
                exit_price=exit_price,
                exit_time=exit_row["timestamp"],
                exit_bar_index=int(exit_row["index"]),
                gross_pnl=gross_pnl,
                transaction_costs=total_costs, 
                net_pnl=net_pnl,
                holding_bars=int(exit_row["index"] - entry_row["index"]),
                return_pct=ret_pct
            )
            trades_list.append(trade)
            
        return trades_list
