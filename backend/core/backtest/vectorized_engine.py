import polars as pl
import numpy as np
import os
import logging
import time
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .engine import BacktestConfig, BacktestMetrics, BacktestResult
from .executor import Trade, OrderSide
from core.duckdb_engine import engine as duckdb_engine

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
        
        total_return = final_equity - self.config.initial_capital
        total_return_pct = (df["cum_ret"][-1] - 1) * 100
        
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
        
        metrics = BacktestMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            cagr=0.0, # Implement CAGR calculation if needed
            max_drawdown=total_return * (max_dd_pct / 100), # placeholder
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            total_trades=len(trades),
            winning_trades=len([t for t in trades if t.net_pnl > 0]),
            losing_trades=len([t for t in trades if t.net_pnl <= 0]),
            win_rate=(len([t for t in trades if t.net_pnl > 0]) / len(trades) * 100) if trades else 0,
            profit_factor=0.0, # Implement profit factor
            avg_win=0.0,
            avg_loss=0.0,
            avg_trade_pnl=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            avg_holding_bars=0.0,
            final_equity=final_equity,
            peak_equity=peak_equity
        )
        
        # 7. Build Result
        import pandas as pd
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
        
        trades_list = []
        trade_count = 0
        
        # Match entries and exits (assuming one at a time for simplicity)
        for i in range(min(len(entries), len(exits))):
            entry_row = entries[i]
            exit_row = exits[i]
            trade_count += 1
            
            entry_price = float(entry_row["close"][0])
            exit_price = float(exit_row["close"][0])
            
            qty = int(self.config.initial_capital * 0.1 / entry_price) # Use 10% of capital for test qty
            if qty < 1: qty = 1
            
            gross_pnl = (exit_price - entry_price) * qty
            ret_pct = (exit_price / entry_price - 1) * 100
            
            trade = Trade(
                id=f"TRD-{trade_count:06d}",
                symbol=self.config.symbol,
                side=OrderSide.BUY, # Strategy is long-only for RSI mean reversion
                quantity=qty,
                entry_price=entry_price,
                entry_time=entry_row["timestamp"][0],
                entry_bar_index=int(entry_row["index"][0]),
                exit_price=exit_price,
                exit_time=exit_row["timestamp"][0],
                exit_bar_index=int(exit_row["index"][0]),
                gross_pnl=gross_pnl,
                transaction_costs=0.0, 
                net_pnl=gross_pnl,
                holding_bars=int(exit_row["index"][0] - entry_row["index"][0]),
                return_pct=ret_pct
            )
            trades_list.append(trade)
            
        return trades_list
