"""
Strategy Backtesting Engine
Tests all 9 trading strategies across different timeframes (3m, 5m, 15m, 30m).
Generates performance metrics and optimal timeframe recommendations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from config import settings
from core.indicators import ema, bollinger_bands


@dataclass
class BacktestResult:
    """Stores backtesting results for a strategy-timeframe combination."""
    strategy: str
    timeframe: str
    total_signals: int
    winning_signals: int
    losing_signals: int
    win_rate: float
    avg_return: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    avg_holding_period: float  # in candles


class StrategyBacktester:
    """
    Backtests all 9 trading strategies across different timeframes.
    """
    
    TIMEFRAMES = ["3m", "5m", "15m", "30m"]
    
    STRATEGIES = [
        "trend_finder",
        "breakout_detector", 
        "top10_buysell",
        "momentum",
        "mean_reversion",
        "gap_scanner",
        "relative_strength",
        "vwap",
        "sr_bounce"
    ]
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        
        # New Parquet DAL
        from core.lake_dal import get_lake_dal
        self.dal = get_lake_dal()
        
        # Results storage
        self.results: List[BacktestResult] = []
        self.optimal_timeframes: Dict[str, str] = {}
    
    def get_candles(self, symbol: str, interval: str, limit: int = 1000) -> pd.DataFrame:
        """Fetch candles from Parquet Lake (optimized)."""
        # Map UI timeframe to file structure
        # interval: 3m, 5m, 15m, 30m
        lf = self.dal.load_candles(symbol, interval, lazy=True)
        
        # Fetch last N candles
        df_pl = lf.tail(limit).collect()
        
        if df_pl.is_empty():
            return pd.DataFrame()
        
        # Convert to Pandas for compatibility with existing signal generators
        df = df_pl.to_pandas()
        if 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
        return df
    
    # ========== STRATEGY SIGNAL GENERATORS ==========
    
    def _generate_trend_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Trend Finder strategy signals (Vectorized)."""
        if len(df) < 50:
            return []
        
        close = df['close']
        ema20 = ema(close, 20)
        ema50 = ema(close, 50)
        
        # Conditions
        bullish = (close > ema20) & (ema20 > ema50) & (df['low'] <= ema20 * 1.01)
        bearish = (close < ema20) & (ema20 < ema50) & (df['high'] >= ema20 * 0.99)
        
        # Filter indices where signals occur (starting from index 50 to match original logic)
        mask = (bullish | bearish)
        # Ensure we don't signal before index 50
        mask.iloc[:50] = False
        
        signal_indices = np.where(mask)[0]
        
        signals = []
        for i in signal_indices:
            sig_type = 'BUY' if bullish.iloc[i] else 'SELL'
            price = close.iloc[i]
            
            signals.append({
                'idx': int(i),
                'type': sig_type,
                'entry': price,
                'target': price * (1.02 if sig_type == 'BUY' else 0.98),
                'stop': price * (0.98 if sig_type == 'BUY' else 1.02)
            })
            
        return signals
    
    def _generate_breakout_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Breakout Detector strategy signals (Vectorized)."""
        if len(df) < 20:
            return []
        
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']
        
        # Calculate rolling metrics
        high_20 = high.rolling(window=20).max().shift(1) # Previous 20 candles high
        low_20 = low.rolling(window=20).min().shift(1)   # Previous 20 candles low
        avg_vol = volume.rolling(window=20).mean().shift(1)
        
        # Conditions
        vol_condition = volume > avg_vol * 1.5
        buy_cond = (close > high_20) & vol_condition
        sell_cond = (close < low_20) & vol_condition
        
        mask = (buy_cond | sell_cond)
        mask.iloc[:20] = False
        
        signal_indices = np.where(mask)[0]
        
        signals = []
        for i in signal_indices:
            sig_type = 'BUY' if buy_cond.iloc[i] else 'SELL'
            price = close.iloc[i]
            ref_level = high_20.iloc[i] if sig_type == 'BUY' else low_20.iloc[i]
            
            signals.append({
                'idx': int(i),
                'type': sig_type,
                'entry': price,
                'target': price * (1.03 if sig_type == 'BUY' else 0.97),
                'stop': ref_level * (0.99 if sig_type == 'BUY' else 1.01)
            })
            
        return signals
    
    def _generate_momentum_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Momentum strategy signals using ROC (Vectorized)."""
        if len(df) < 20:
            return []
        
        close = df['close']
        roc10 = (close - close.shift(10)) / close.shift(10) * 100
        prev_roc = roc10.shift(1)
        
        buy_cond = (roc10 > 3) & (prev_roc <= 3)
        sell_cond = (roc10 < -3) & (prev_roc >= -3)
        
        mask = (buy_cond | sell_cond)
        mask.iloc[:20] = False
        
        signal_indices = np.where(mask)[0]
        
        signals = []
        for i in signal_indices:
            sig_type = 'BUY' if buy_cond.iloc[i] else 'SELL'
            price = close.iloc[i]
            
            signals.append({
                'idx': int(i),
                'type': sig_type,
                'entry': price,
                'target': price * (1.02 if sig_type == 'BUY' else 0.98),
                'stop': price * (0.98 if sig_type == 'BUY' else 1.02)
            })
        
        return signals
    
    def _generate_mean_reversion_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Mean reversion using Bollinger Bands (Vectorized)."""
        if len(df) < 20:
            return []
        
        close = df['close']
        middle, upper, lower = bollinger_bands(close, 20, 2.0)
        
        buy_cond = (close < lower)
        sell_cond = (close > upper)
        
        mask = (buy_cond | sell_cond)
        mask.iloc[:20] = False
        
        signal_indices = np.where(mask)[0]
        
        signals = []
        for i in signal_indices:
            sig_type = 'BUY' if buy_cond.iloc[i] else 'SELL'
            price = close.iloc[i]
            target = middle.iloc[i]
            ref_level = lower.iloc[i] if sig_type == 'BUY' else upper.iloc[i]
            
            signals.append({
                'idx': int(i),
                'type': sig_type,
                'entry': price,
                'target': target,
                'stop': ref_level * (0.98 if sig_type == 'BUY' else 1.02)
            })
            
        return signals
    
    def _generate_gap_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Gap scanner signals (Vectorized)."""
        if len(df) < 5:
            return []
        
        close = df['close']
        open_price = df['open']
        prev_close = close.shift(1)
        
        gap_pct = (open_price - prev_close) / prev_close * 100
        
        buy_cond = (gap_pct > 1.5)
        sell_cond = (gap_pct < -1.5)
        
        mask = (buy_cond | sell_cond)
        mask.iloc[0] = False # Can't signal on first candle
        
        signal_indices = np.where(mask)[0]
        
        signals = []
        for i in signal_indices:
            sig_type = 'BUY' if buy_cond.iloc[i] else 'SELL'
            price = close.iloc[i]
            pc = prev_close.iloc[i]
            
            signals.append({
                'idx': int(i),
                'type': sig_type,
                'entry': price,
                'target': price * (1.02 if sig_type == 'BUY' else 0.98),
                'stop': pc
            })
            
        return signals
    
    def _generate_rs_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Relative strength signals (Vectorized)."""
        if len(df) < 20:
            return []
        
        close = df['close']
        ret5 = (close - close.shift(5)) / close.shift(5) * 100
        ret20 = (close - close.shift(20)) / close.shift(20) * 100
        
        # Only BUY logic implemented in original
        buy_cond = (ret5 > 3) & (ret20 > 5)
        
        mask = buy_cond
        mask.iloc[:20] = False
        
        signal_indices = np.where(mask)[0]
        
        signals = []
        for i in signal_indices:
            price = close.iloc[i]
            signals.append({
                'idx': int(i),
                'type': 'BUY',
                'entry': price,
                'target': price * 1.03,
                'stop': price * 0.97
            })
            
        return signals
    
    def _generate_vwap_signals(self, df: pd.DataFrame) -> List[Dict]:
        """VWAP based signals (Vectorized)."""
        if len(df) < 10:
            return []
        
        close = df['close']
        tp = (df['high'] + df['low'] + close) / 3
        vwap = (tp * df['volume']).cumsum() / df['volume'].cumsum()
        
        prev_close = close.shift(1)
        prev_vwap = vwap.shift(1)
        
        # Cross above VWAP
        buy_cond = (close > vwap) & (prev_close <= prev_vwap)
        # Cross below VWAP
        sell_cond = (close < vwap) & (prev_close >= prev_vwap)
        
        mask = (buy_cond | sell_cond)
        mask.iloc[:10] = False
        
        signal_indices = np.where(mask)[0]
        
        signals = []
        for i in signal_indices:
            sig_type = 'BUY' if buy_cond.iloc[i] else 'SELL'
            price = close.iloc[i]
            vwap_val = vwap.iloc[i]
            
            signals.append({
                'idx': int(i),
                'type': sig_type,
                'entry': price,
                'target': price * (1.015 if sig_type == 'BUY' else 0.985),
                'stop': vwap_val * (0.99 if sig_type == 'BUY' else 1.01)
            })
            
        return signals
    
    def _generate_sr_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Support/Resistance bounce signals (Vectorized)."""
        if len(df) < 50:
            return []
        
        high = df['high']
        low = df['low']
        close = df['close']
        open_price = df['open']
        
        # Previous 20 candles high/low
        high_20 = high.rolling(window=20).max().shift(1)
        low_20 = low.rolling(window=20).min().shift(1)
        
        # Conditions
        buy_cond = (low <= low_20 * 1.01) & (close > open_price)
        sell_cond = (high >= high_20 * 0.99) & (close < open_price)
        
        mask = (buy_cond | sell_cond)
        mask.iloc[:50] = False
        
        signal_indices = np.where(mask)[0]
        
        signals = []
        for i in signal_indices:
            sig_type = 'BUY' if buy_cond.iloc[i] else 'SELL'
            price = close.iloc[i]
            h20 = high_20.iloc[i]
            l20 = low_20.iloc[i]
            target = (h20 + l20) / 2
            
            signals.append({
                'idx': int(i),
                'type': sig_type,
                'entry': price,
                'target': target,
                'stop': l20 * 0.98 if sig_type == 'BUY' else h20 * 1.02
            })
            
        return signals
    
    def get_signal_generator(self, strategy: str):
        """Get signal generator function for a strategy."""
        mapping = {
            "trend_finder": self._generate_trend_signals,
            "breakout_detector": self._generate_breakout_signals,
            "top10_buysell": self._generate_momentum_signals,  # Similar to momentum
            "momentum": self._generate_momentum_signals,
            "mean_reversion": self._generate_mean_reversion_signals,
            "gap_scanner": self._generate_gap_signals,
            "relative_strength": self._generate_rs_signals,
            "vwap": self._generate_vwap_signals,
            "sr_bounce": self._generate_sr_signals
        }
        return mapping.get(strategy)
    
    def backtest_signals(self, df: pd.DataFrame, signals: List[Dict], max_hold: int = 20) -> Dict:
        """
        Simulate trades based on signals.
        Returns performance metrics.
        """
        if not signals:
            return None
        
        trades = []
        
        for signal in signals:
            idx = signal['idx']
            if idx + max_hold >= len(df):
                continue
            
            entry = signal['entry']
            target = signal['target']
            stop = signal['stop']
            signal_type = signal['type']
            
            # Simulate trade
            for j in range(1, max_hold + 1):
                future_idx = idx + j
                if future_idx >= len(df):
                    break
                
                high = df['high'].iloc[future_idx]
                low = df['low'].iloc[future_idx]
                
                if signal_type == 'BUY':
                    if high >= target:
                        trades.append({'pnl': (target - entry) / entry * 100, 'hold': j, 'result': 'win'})
                        break
                    elif low <= stop:
                        trades.append({'pnl': (stop - entry) / entry * 100, 'hold': j, 'result': 'loss'})
                        break
                else:  # SELL
                    if low <= target:
                        trades.append({'pnl': (entry - target) / entry * 100, 'hold': j, 'result': 'win'})
                        break
                    elif high >= stop:
                        trades.append({'pnl': (entry - stop) / entry * 100, 'hold': j, 'result': 'loss'})
                        break
            else:
                # Exit at max hold
                exit_price = df['close'].iloc[min(idx + max_hold, len(df) - 1)]
                if signal_type == 'BUY':
                    pnl = (exit_price - entry) / entry * 100
                else:
                    pnl = (entry - exit_price) / entry * 100
                trades.append({'pnl': pnl, 'hold': max_hold, 'result': 'win' if pnl > 0 else 'loss'})
        
        if not trades:
            return None
        
        # Calculate metrics
        wins = sum(1 for t in trades if t['result'] == 'win')
        losses = len(trades) - wins
        returns = [t['pnl'] for t in trades]
        
        win_returns = [t['pnl'] for t in trades if t['result'] == 'win']
        loss_returns = [abs(t['pnl']) for t in trades if t['result'] == 'loss']
        
        # Sharpe (simplified - daily)
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Max drawdown
        cum_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cum_returns)
        drawdown = running_max - cum_returns
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Profit factor
        gross_profit = sum(win_returns) if win_returns else 0
        gross_loss = sum(loss_returns) if loss_returns else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            'total_signals': len(signals),
            'trades': len(trades),
            'wins': wins,
            'losses': losses,
            'win_rate': wins / len(trades) * 100 if trades else 0,
            'avg_return': np.mean(returns),
            'total_return': sum(returns),
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe,
            'profit_factor': profit_factor,
            'avg_hold': np.mean([t['hold'] for t in trades])
        }
    
    def backtest_strategy_timeframe(
        self,
        strategy: str,
        timeframe: str,
        symbols: List[str] = None,
        limit_per_symbol: int = 500
    ) -> BacktestResult:
        """
        Backtest a strategy on a specific timeframe across multiple symbols.
        """
        if symbols is None:
            from services.nifty500_fetcher import Nifty500Fetcher
            fetcher = Nifty500Fetcher()
            symbols = [s[0] for s in fetcher.get_all_symbols()[:50]]  # Limit for speed
        
        signal_gen = self.get_signal_generator(strategy)
        if not signal_gen:
            return None
        
        all_metrics = []
        
        for symbol in symbols:
            df = self.get_candles(symbol, timeframe, limit_per_symbol)
            if df.empty:
                continue
            
            signals = signal_gen(df)
            metrics = self.backtest_signals(df, signals)
            if metrics:
                all_metrics.append(metrics)
        
        if not all_metrics:
            return BacktestResult(
                strategy=strategy, timeframe=timeframe,
                total_signals=0, winning_signals=0, losing_signals=0,
                win_rate=0, avg_return=0, total_return=0,
                max_drawdown=0, sharpe_ratio=0, profit_factor=0, avg_holding_period=0
            )
        
        # Aggregate metrics
        return BacktestResult(
            strategy=strategy,
            timeframe=timeframe,
            total_signals=sum(m['total_signals'] for m in all_metrics),
            winning_signals=sum(m['wins'] for m in all_metrics),
            losing_signals=sum(m['losses'] for m in all_metrics),
            win_rate=np.mean([m['win_rate'] for m in all_metrics]),
            avg_return=np.mean([m['avg_return'] for m in all_metrics]),
            total_return=sum(m['total_return'] for m in all_metrics),
            max_drawdown=np.max([m['max_drawdown'] for m in all_metrics]),
            sharpe_ratio=np.mean([m['sharpe_ratio'] for m in all_metrics]),
            profit_factor=np.mean([m['profit_factor'] for m in all_metrics]),
            avg_holding_period=np.mean([m['avg_hold'] for m in all_metrics])
        )
    
    def run_full_backtest(self) -> Dict:
        """
        Run backtests for all strategies across all timeframes.
        Returns optimal timeframe for each strategy.
        """
        print("=" * 70)
        print("STRATEGY BACKTESTING ENGINE")
        print("=" * 70)
        print(f"Strategies: {len(self.STRATEGIES)}")
        print(f"Timeframes: {self.TIMEFRAMES}")
        print()
        
        for strategy in self.STRATEGIES:
            print(f"\n📊 Backtesting: {strategy}")
            best_result = None
            best_sharpe = -999
            
            for tf in self.TIMEFRAMES:
                print(f"  [{tf}] ", end="")
                result = self.backtest_strategy_timeframe(strategy, tf)
                self.results.append(result)
                
                print(f"Signals: {result.total_signals}, WR: {result.win_rate:.1f}%, Sharpe: {result.sharpe_ratio:.2f}")
                
                if result.sharpe_ratio > best_sharpe:
                    best_sharpe = result.sharpe_ratio
                    best_result = result
            
            if best_result:
                self.optimal_timeframes[strategy] = best_result.timeframe
                print(f"  ✅ Optimal: {best_result.timeframe} (Sharpe: {best_sharpe:.2f})")
        
        print("\n" + "=" * 70)
        print("OPTIMAL TIMEFRAMES")
        print("=" * 70)
        for strategy, tf in self.optimal_timeframes.items():
            print(f"  {strategy}: {tf}")
        
        return self.optimal_timeframes
    
    def generate_report(self) -> pd.DataFrame:
        """Generate a DataFrame report of all backtest results."""
        data = [{
            'Strategy': r.strategy,
            'Timeframe': r.timeframe,
            'Signals': r.total_signals,
            'Win Rate': f"{r.win_rate:.1f}%",
            'Avg Return': f"{r.avg_return:.2f}%",
            'Total Return': f"{r.total_return:.1f}%",
            'Max DD': f"{r.max_drawdown:.1f}%",
            'Sharpe': f"{r.sharpe_ratio:.2f}",
            'Profit Factor': f"{r.profit_factor:.2f}",
            'Avg Hold': f"{r.avg_holding_period:.1f}"
        } for r in self.results]
        
        return pd.DataFrame(data)
    
    def save_optimal_config(self, filepath: str = "optimal_timeframes.json"):
        """Save optimal timeframes to JSON config."""
        import json
        with open(filepath, 'w') as f:
            json.dump(self.optimal_timeframes, f, indent=2)
        print(f"💾 Saved optimal config to {filepath}")


# CLI interface
if __name__ == "__main__":
    backtester = StrategyBacktester()
    optimal = backtester.run_full_backtest()
    
    print("\n📋 Full Report:")
    report = backtester.generate_report()
    print(report.to_string())
    
    backtester.save_optimal_config()
