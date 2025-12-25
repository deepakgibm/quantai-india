"""
Strategy Backtesting Engine
Tests all 9 trading strategies across different timeframes (3m, 5m, 15m, 30m).
Generates performance metrics and optimal timeframe recommendations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from config import settings


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
        
        # Results storage
        self.results: List[BacktestResult] = []
        self.optimal_timeframes: Dict[str, str] = {}
    
    def get_candles(self, symbol: str, interval: str, limit: int = 1000) -> pd.DataFrame:
        """Fetch intraday candles from database."""
        from services.intraday_loader import IntradayCandle
        
        session = self._Session()
        try:
            candles = session.query(IntradayCandle).filter(
                IntradayCandle.symbol == symbol,
                IntradayCandle.interval == interval
            ).order_by(desc(IntradayCandle.timestamp)).limit(limit).all()
            
            if not candles:
                return pd.DataFrame()
            
            data = [{
                'timestamp': c.timestamp, 'open': c.open, 'high': c.high,
                'low': c.low, 'close': c.close, 'volume': c.volume
            } for c in reversed(candles)]
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            return df
        finally:
            session.close()
    
    # ========== STRATEGY SIGNAL GENERATORS ==========
    
    def _generate_trend_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Trend Finder strategy signals."""
        if len(df) < 50:
            return []
        
        signals = []
        df = df.copy()
        df['ema20'] = df['close'].ewm(span=20).mean()
        df['ema50'] = df['close'].ewm(span=50).mean()
        
        for i in range(50, len(df)):
            # Bullish: price > EMA20 > EMA50 and pullback to EMA20
            if (df['close'].iloc[i] > df['ema20'].iloc[i] > df['ema50'].iloc[i] and
                df['low'].iloc[i] <= df['ema20'].iloc[i] * 1.01):
                signals.append({
                    'idx': i, 'type': 'BUY',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 1.02,
                    'stop': df['close'].iloc[i] * 0.98
                })
            # Bearish: price < EMA20 < EMA50
            elif (df['close'].iloc[i] < df['ema20'].iloc[i] < df['ema50'].iloc[i] and
                  df['high'].iloc[i] >= df['ema20'].iloc[i] * 0.99):
                signals.append({
                    'idx': i, 'type': 'SELL',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 0.98,
                    'stop': df['close'].iloc[i] * 1.02
                })
        
        return signals
    
    def _generate_breakout_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Breakout Detector strategy signals."""
        if len(df) < 20:
            return []
        
        signals = []
        df = df.copy()
        
        for i in range(20, len(df)):
            high_20 = df['high'].iloc[i-20:i].max()
            low_20 = df['low'].iloc[i-20:i].min()
            avg_vol = df['volume'].iloc[i-20:i].mean()
            
            # Breakout above 20-period high with volume
            if df['close'].iloc[i] > high_20 and df['volume'].iloc[i] > avg_vol * 1.5:
                signals.append({
                    'idx': i, 'type': 'BUY',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 1.03,
                    'stop': high_20 * 0.99
                })
            # Breakdown below 20-period low
            elif df['close'].iloc[i] < low_20 and df['volume'].iloc[i] > avg_vol * 1.5:
                signals.append({
                    'idx': i, 'type': 'SELL',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 0.97,
                    'stop': low_20 * 1.01
                })
        
        return signals
    
    def _generate_momentum_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Momentum strategy signals using ROC."""
        if len(df) < 20:
            return []
        
        signals = []
        df = df.copy()
        df['roc10'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10) * 100
        
        for i in range(20, len(df)):
            if df['roc10'].iloc[i] > 3 and df['roc10'].iloc[i-1] <= 3:
                signals.append({
                    'idx': i, 'type': 'BUY',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 1.02,
                    'stop': df['close'].iloc[i] * 0.98
                })
            elif df['roc10'].iloc[i] < -3 and df['roc10'].iloc[i-1] >= -3:
                signals.append({
                    'idx': i, 'type': 'SELL',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 0.98,
                    'stop': df['close'].iloc[i] * 1.02
                })
        
        return signals
    
    def _generate_mean_reversion_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Mean reversion using Bollinger Bands."""
        if len(df) < 20:
            return []
        
        signals = []
        df = df.copy()
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['upper'] = df['sma20'] + 2 * df['std20']
        df['lower'] = df['sma20'] - 2 * df['std20']
        
        for i in range(20, len(df)):
            if df['close'].iloc[i] < df['lower'].iloc[i]:
                signals.append({
                    'idx': i, 'type': 'BUY',
                    'entry': df['close'].iloc[i],
                    'target': df['sma20'].iloc[i],
                    'stop': df['lower'].iloc[i] * 0.98
                })
            elif df['close'].iloc[i] > df['upper'].iloc[i]:
                signals.append({
                    'idx': i, 'type': 'SELL',
                    'entry': df['close'].iloc[i],
                    'target': df['sma20'].iloc[i],
                    'stop': df['upper'].iloc[i] * 1.02
                })
        
        return signals
    
    def _generate_gap_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Gap scanner signals."""
        if len(df) < 5:
            return []
        
        signals = []
        df = df.copy()
        
        for i in range(1, len(df)):
            prev_close = df['close'].iloc[i-1]
            curr_open = df['open'].iloc[i]
            gap_pct = (curr_open - prev_close) / prev_close * 100
            
            if gap_pct > 1.5:  # Gap up
                signals.append({
                    'idx': i, 'type': 'BUY',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 1.02,
                    'stop': prev_close
                })
            elif gap_pct < -1.5:  # Gap down
                signals.append({
                    'idx': i, 'type': 'SELL',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 0.98,
                    'stop': prev_close
                })
        
        return signals
    
    def _generate_rs_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Relative strength signals."""
        if len(df) < 20:
            return []
        
        signals = []
        df = df.copy()
        df['ret5'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5) * 100
        df['ret20'] = (df['close'] - df['close'].shift(20)) / df['close'].shift(20) * 100
        
        for i in range(20, len(df)):
            if df['ret5'].iloc[i] > 3 and df['ret20'].iloc[i] > 5:
                signals.append({
                    'idx': i, 'type': 'BUY',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 1.03,
                    'stop': df['close'].iloc[i] * 0.97
                })
        
        return signals
    
    def _generate_vwap_signals(self, df: pd.DataFrame) -> List[Dict]:
        """VWAP based signals."""
        if len(df) < 10:
            return []
        
        signals = []
        df = df.copy()
        df['tp'] = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (df['tp'] * df['volume']).cumsum() / df['volume'].cumsum()
        
        for i in range(10, len(df)):
            if df['close'].iloc[i] > df['vwap'].iloc[i] and df['close'].iloc[i-1] <= df['vwap'].iloc[i-1]:
                signals.append({
                    'idx': i, 'type': 'BUY',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 1.015,
                    'stop': df['vwap'].iloc[i] * 0.99
                })
            elif df['close'].iloc[i] < df['vwap'].iloc[i] and df['close'].iloc[i-1] >= df['vwap'].iloc[i-1]:
                signals.append({
                    'idx': i, 'type': 'SELL',
                    'entry': df['close'].iloc[i],
                    'target': df['close'].iloc[i] * 0.985,
                    'stop': df['vwap'].iloc[i] * 1.01
                })
        
        return signals
    
    def _generate_sr_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Support/Resistance bounce signals."""
        if len(df) < 50:
            return []
        
        signals = []
        df = df.copy()
        
        for i in range(50, len(df)):
            high_20 = df['high'].iloc[i-20:i].max()
            low_20 = df['low'].iloc[i-20:i].min()
            
            # Near support and bouncing
            if df['low'].iloc[i] <= low_20 * 1.01 and df['close'].iloc[i] > df['open'].iloc[i]:
                signals.append({
                    'idx': i, 'type': 'BUY',
                    'entry': df['close'].iloc[i],
                    'target': (high_20 + low_20) / 2,
                    'stop': low_20 * 0.98
                })
            # Near resistance and rejecting
            elif df['high'].iloc[i] >= high_20 * 0.99 and df['close'].iloc[i] < df['open'].iloc[i]:
                signals.append({
                    'idx': i, 'type': 'SELL',
                    'entry': df['close'].iloc[i],
                    'target': (high_20 + low_20) / 2,
                    'stop': high_20 * 1.02
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
