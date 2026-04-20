"""
Backtest Runner for Experiment Lab
Main engine for executing strategy backtests.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import hashlib

from ..registry import StrategyRegistry
from ..lab_strategies.base import SignalType, SignalResult
from core.risk.risk_manager import RiskManager, RiskMode
from .metrics_calculator import MetricsCalculator, BacktestMetrics, TradeRecord


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""
    symbol: str
    strategy_ids: List[int]
    timeframe: str  # 5m, 15m, 30m, 1H, 1D
    start_date: str
    end_date: str
    initial_capital: float = 1000000
    risk_mode: str = "percent_capital"
    risk_percent: float = 2.0
    max_holding_bars: int = 20
    
    def to_cache_key(self) -> str:
        """Generate cache key for this config."""
        data = f"{self.symbol}_{self.strategy_ids}_{self.timeframe}_{self.start_date}_{self.end_date}_{self.initial_capital}_{self.risk_mode}"
        return hashlib.md5(data.encode()).hexdigest()


@dataclass
class BacktestRun:
    """Result of a single backtest run."""
    strategy_id: int
    strategy_name: str
    category: str
    metrics: BacktestMetrics
    config: BacktestConfig
    run_time_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "category": self.category,
            "metrics": self.metrics.to_dict(),
            "config": {
                "symbol": self.config.symbol,
                "timeframe": self.config.timeframe,
                "start_date": self.config.start_date,
                "end_date": self.config.end_date,
                "initial_capital": self.config.initial_capital,
            },
            "run_time_seconds": round(self.run_time_seconds, 2)
        }


class ExperimentRunner:
    """
    Main backtest execution engine for the Strategy Experiment Lab.
    Simulates trades based on strategy signals using OHLCV data.
    """
    
    # Result cache
    _cache: Dict[str, BacktestRun] = {}
    
    def __init__(self, db_fetcher=None):
        """
        Initialize the experiment runner.
        
        Args:
            db_fetcher: Optional database fetcher for OHLCV data
        """
        self.db_fetcher = db_fetcher
        self.registry = StrategyRegistry()
    
    def get_ohlcv_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for backtesting.
        Uses database or generates sample data for testing.
        """
        # 1. Try Feature Store (Parquet/DuckDB) - FASTEST
        try:
            from services.feature_store import get_feature_store
            store = get_feature_store()
            
            # Normalize timeframe (e.g. 1D -> 1d)
            tf_norm = timeframe.lower()
            
            df = store.query_features(
                symbols=[symbol], 
                timeframes=[tf_norm],
                start_date=start_date,
                end_date=end_date
            )
            
            if df is not None and not df.empty:
                # Ensure timestamp format is consistent for backtesting engine
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                
                # Verify required columns exist
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                if all(col in df.columns for col in required_cols):
                    print(f"✅ Loaded {len(df)} rows from Feature Store (Parquet)")
                    return df
        except Exception as e:
            print(f"Feature Store fetch failed: {e}")

        # 2. Try DB Fetcher (Postgres) - FALLBACK
        if self.db_fetcher:
            try:
                df = self.db_fetcher.get_historical_data(
                    symbol=symbol,
                    interval=timeframe,
                    start_date=start_date,
                    end_date=end_date
                )
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                print(f"DB fetch failed: {e}")
        
        # 3. Try Service Fetcher (Postgres) - FALLBACK
        try:
            from services.db_data_fetcher import DBDataFetcher
            fetcher = DBDataFetcher()
            df = fetcher.get_stock_data(symbol, timeframe, start_date, end_date)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"Service fetch failed: {e}")
        
        # 4. Generate sample data if no data available
        return self._generate_sample_data(symbol, start_date, end_date, timeframe)
    
    def _generate_sample_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str
    ) -> pd.DataFrame:
        """Generate sample OHLCV data for testing."""
        # Determine number of bars based on timeframe
        freq_map = {
            "5m": "5T", "15m": "15T", "30m": "30T",
            "1H": "1H", "1h": "1H", "1D": "1D", "1d": "1D"
        }
        freq = freq_map.get(timeframe, "1D")
        
        dates = pd.date_range(start=start_date, end=end_date, freq=freq)
        if len(dates) < 100:
            dates = pd.date_range(start=start_date, periods=500, freq=freq)
        
        np.random.seed(hash(symbol) % 2**32)
        
        # Generate realistic price data
        initial_price = 1000 + np.random.random() * 2000
        returns = np.random.randn(len(dates)) * 0.015  # 1.5% daily volatility
        prices = initial_price * np.cumprod(1 + returns)
        
        # Generate OHLC from prices
        df = pd.DataFrame(index=dates)
        df['close'] = prices
        df['open'] = df['close'].shift(1).fillna(initial_price)
        df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.abs(np.random.randn(len(dates))) * 0.005)
        df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.abs(np.random.randn(len(dates))) * 0.005)
        df['volume'] = np.random.randint(100000, 5000000, len(dates))
        
        return df
    
    def run_backtest(
        self,
        config: BacktestConfig
    ) -> List[BacktestRun]:
        """
        Run backtest for specified strategies.
        
        Args:
            config: BacktestConfig with all parameters
            
        Returns:
            List of BacktestRun results
        """
        import time
        results = []
        
        # Fetch data once for all strategies
        df = self.get_ohlcv_data(
            config.symbol,
            config.timeframe,
            config.start_date,
            config.end_date
        )
        
        if df is None or df.empty:
            raise ValueError(f"No data available for {config.symbol}")
        
        # Pre-calculate ATR once for all strategies (used for position sizing)
        from ..indicators.technical import TechnicalIndicators
        atr_series = TechnicalIndicators.atr(df, 14)
        
        # Run each strategy
        total_strategies = len(config.strategy_ids)
        for idx, strategy_id in enumerate(config.strategy_ids):
            print(f"[{idx+1}/{total_strategies}] Running strategy ID: {strategy_id}...")
            cache_key = f"{config.to_cache_key()}_{strategy_id}"
            
            # Check cache
            if cache_key in self._cache:
                results.append(self._cache[cache_key])
                continue
            
            start_time = time.time()
            
            # Get strategy
            strategy = self.registry.instantiate(strategy_id)
            if not strategy:
                continue
            
            # Generate signals
            signals = strategy.generate_signals(df)
            
            # Simulate trades
            trades = self._simulate_trades(
                df=df,
                signals=signals,
                initial_capital=config.initial_capital,
                risk_mode=RiskMode(config.risk_mode),
                risk_percent=config.risk_percent,
                max_holding_bars=config.max_holding_bars,
                atr_series=atr_series
            )
            
            # Calculate metrics
            calculator = MetricsCalculator(initial_capital=config.initial_capital)
            metrics = calculator.calculate(trades)
            
            run_time = time.time() - start_time
            
            # Get strategy info from catalog
            catalog_entry = next(
                (s for s in self.registry.get_catalog() if s['id'] == strategy_id),
                {"name": strategy.info.name, "category": "Unknown"}
            )
            
            result = BacktestRun(
                strategy_id=strategy_id,
                strategy_name=catalog_entry['name'],
                category=catalog_entry['category'],
                metrics=metrics,
                config=config,
                run_time_seconds=run_time
            )
            
            # Cache result
            self._cache[cache_key] = result
            results.append(result)
        
        return results
    
    def _simulate_trades(
        self,
        df: pd.DataFrame,
        signals: List[SignalResult],
        initial_capital: float,
        risk_mode: RiskMode,
        risk_percent: float,
        max_holding_bars: int,
        atr_series: Optional[pd.Series] = None
    ) -> List[TradeRecord]:
        """
        Simulate trades from signals.
        
        Rules:
        - Long-only (Phase 1)
        - One active trade at a time
        - Exit on: Target, Stop Loss, Signal Exit, Max Hold
        """
        if not signals:
            return []
        
        trades = []
        risk_manager = RiskManager()
        
        current_capital = initial_capital
        in_position = False
        entry_signal: Optional[SignalResult] = None
        entry_bar_idx: int = 0
        quantity: int = 0
        
        # Convert signals to dict by timestamp for quick lookup
        signal_map = {s.timestamp: s for s in signals}
        
        # Iterate through data
        for i in range(len(df)):
            timestamp = df.index[i]
            price = df['close'].iloc[i]
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            
            if not in_position:
                # Look for entry signal
                if timestamp in signal_map:
                    signal = signal_map[timestamp]
                    if signal.signal == SignalType.BUY:
                        # Enter long position
                        atr = None
                        if atr_series is not None:
                            atr = atr_series.iloc[i]
                        elif i >= 14:
                            # Fallback if no pre-calculated series
                            tr = pd.concat([
                                df['high'].iloc[i-14:i] - df['low'].iloc[i-14:i],
                                abs(df['high'].iloc[i-14:i] - df['close'].iloc[i-15:i-1].values),
                                abs(df['low'].iloc[i-14:i] - df['close'].iloc[i-15:i-1].values)
                            ], axis=1).max(axis=1)
                            atr = tr.mean()
                        
                        pos_result = risk_manager.calculate_position_size(
                            account_equity=current_capital,
                            entry_price=price,
                            stop_loss=signal.stop_loss or (price - (atr * 2) if atr else price * 0.98),
                            risk_per_trade_pct=risk_percent,
                            method=RiskMode(risk_mode),
                            atr=atr
                        )
                        
                        if pos_result.quantity > 0 and pos_result.amount <= current_capital:
                            in_position = True
                            entry_signal = signal
                            entry_bar_idx = i
                            quantity = pos_result.quantity
            
            else:
                # Check exit conditions
                bars_held = i - entry_bar_idx
                should_exit = False
                exit_price = price
                exit_reason = ""
                
                # Check stop loss
                if entry_signal.stop_loss and low <= entry_signal.stop_loss:
                    should_exit = True
                    exit_price = entry_signal.stop_loss
                    exit_reason = "STOP"
                
                # Check take profit
                elif entry_signal.take_profit and high >= entry_signal.take_profit:
                    should_exit = True
                    exit_price = entry_signal.take_profit
                    exit_reason = "TARGET"
                
                # Check for exit signal
                elif timestamp in signal_map:
                    signal = signal_map[timestamp]
                    if signal.signal == SignalType.SELL or signal.signal == SignalType.EXIT:
                        should_exit = True
                        exit_price = price
                        exit_reason = "SIGNAL"
                
                # Check max holding period
                elif bars_held >= max_holding_bars:
                    should_exit = True
                    exit_price = price
                    exit_reason = "MAX_HOLD"
                
                if should_exit:
                    # Record trade
                    pnl = (exit_price - entry_signal.price) * quantity
                    pnl_percent = ((exit_price - entry_signal.price) / entry_signal.price) * 100
                    
                    trades.append(TradeRecord(
                        entry_time=entry_signal.timestamp,
                        exit_time=timestamp,
                        signal_type="BUY",
                        entry_price=entry_signal.price,
                        exit_price=exit_price,
                        quantity=quantity,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        holding_bars=bars_held,
                        exit_reason=exit_reason
                    ))
                    
                    # Update capital
                    current_capital += pnl
                    
                    # Reset position
                    in_position = False
                    entry_signal = None
        
        return trades
    
    def clear_cache(self):
        """Clear the result cache."""
        self._cache.clear()


__all__ = ['BacktestConfig', 'BacktestRun', 'ExperimentRunner']
