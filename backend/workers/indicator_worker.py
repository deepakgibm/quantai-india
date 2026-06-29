"""
Indicator Worker - Multiprocessing-Based Background Computation
Runs indicator calculations in separate processes to avoid GIL contention.
"""

import multiprocessing as mp
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComputeTask:
    """Task for indicator computation."""
    symbol: str
    interval: str
    candles: List[Dict]  # List of OHLCV candles
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class ComputeResult:
    """Result from indicator computation."""
    symbol: str
    interval: str
    indicators: Dict[str, float]
    signals: List[str]
    snapshot: Dict[str, Any]
    compute_time_ms: float
    timestamp: float


def compute_indicators_process(task: ComputeTask) -> ComputeResult:
    """
    Compute all indicators for a symbol.
    This runs in a separate process (no GIL).
    """
    start = time.time()
    
    candles = task.candles
    if not candles or len(candles) < 1:
        return ComputeResult(
            symbol=task.symbol,
            interval=task.interval,
            indicators={},
            signals=[],
            snapshot={},
            compute_time_ms=0,
            timestamp=time.time()
        )
    
    import pandas as pd
    from core.scanner import indicator_utils
    
    df = pd.DataFrame(candles)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')
            
    close = df['close']
    high = df['high']
    low = df['low']
    
    # Compute indicators
    indicators = {}
    
    # SMA
    sma_20 = indicator_utils.sma(close, 20)
    indicators['sma_20'] = float(sma_20.iloc[-1]) if len(close) >= 20 else float(close.iloc[-1])
    sma_50 = indicator_utils.sma(close, 50)
    indicators['sma_50'] = float(sma_50.iloc[-1]) if len(close) >= 50 else float(indicators['sma_20'])
    
    # EMA
    indicators['ema_9'] = float(indicator_utils.ema(close, 9).iloc[-1])
    indicators['ema_21'] = float(indicator_utils.ema(close, 21).iloc[-1])
    indicators['ema_50'] = float(indicator_utils.ema(close, 50).iloc[-1])
    
    # RSI
    rsi_14 = indicator_utils.rsi(close, 14).iloc[-1]
    indicators['rsi_14'] = float(rsi_14) if not pd.isna(rsi_14) else 50.0
    
    # MACD
    macd_line, macd_signal, macd_hist = indicator_utils.macd(close, 12, 26, 9)
    indicators['macd_line'] = float(macd_line.iloc[-1])
    indicators['macd_signal'] = float(macd_signal.iloc[-1])
    indicators['macd_histogram'] = float(macd_hist.iloc[-1])
    
    # Bollinger Bands
    bb_middle, bb_upper, bb_lower = indicator_utils.bollinger_bands(close, 20, 2.0)
    indicators['bb_upper'] = float(bb_upper.iloc[-1]) if len(close) >= 20 else float(close.iloc[-1])
    indicators['bb_lower'] = float(bb_lower.iloc[-1]) if len(close) >= 20 else float(close.iloc[-1])
    indicators['bb_middle'] = float(bb_middle.iloc[-1]) if len(close) >= 20 else float(close.iloc[-1])
    
    # ATR
    atr_val = indicator_utils.atr(high, low, close, 14).iloc[-1]
    indicators['atr_14'] = float(atr_val) if len(close) >= 14 and not pd.isna(atr_val) else 0.0
    
    # Current price data
    indicators['current_close'] = float(close.iloc[-1])
    indicators['prev_close'] = float(close.iloc[-2]) if len(close) >= 2 else float(close.iloc[-1])
    indicators['change_pct'] = float(
        ((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100)
    ) if len(close) >= 2 and close.iloc[-2] > 0 else 0.0
    
    # Generate signals
    signals = []
    
    # RSI signals
    if indicators['rsi_14'] < 30:
        signals.append('RSI_OVERSOLD')
    elif indicators['rsi_14'] > 70:
        signals.append('RSI_OVERBOUGHT')
    
    # MACD signals
    if indicators['macd_histogram'] > 0:
        signals.append('MACD_BULLISH')
    else:
        signals.append('MACD_BEARISH')
    
    # EMA trend
    if indicators['ema_9'] > indicators['ema_21'] > indicators['ema_50']:
        signals.append('EMA_BULLISH_STACK')
    elif indicators['ema_9'] < indicators['ema_21'] < indicators['ema_50']:
        signals.append('EMA_BEARISH_STACK')
    
    # Bollinger signals
    if close.iloc[-1] < indicators['bb_lower']:
        signals.append('BB_OVERSOLD')
    elif close.iloc[-1] > indicators['bb_upper']:
        signals.append('BB_OVERBOUGHT')
    
    # Build snapshot
    snapshot = {
        'symbol': task.symbol,
        'interval': task.interval,
        'ltp': indicators['current_close'],
        'prev_close': indicators['prev_close'],
        'change_pct': round(indicators['change_pct'], 2),
        'indicators': {k: round(v, 4) for k, v in indicators.items()},
        'signals': signals,
        'bucket': _get_momentum_bucket(indicators['change_pct']),
        'momentum_bucket': _get_momentum_bucket(indicators['change_pct']),
        'momentum_score': _calculate_momentum_score(indicators['change_pct']),
        'trend': 'BULLISH' if 'EMA_BULLISH_STACK' in signals else 'BEARISH' if 'EMA_BEARISH_STACK' in signals else 'NEUTRAL',
        'updated_at': datetime.now().isoformat()
    }
    
    compute_time = (time.time() - start) * 1000
    
    return ComputeResult(
        symbol=task.symbol,
        interval=task.interval,
        indicators=indicators,
        signals=signals,
        snapshot=snapshot,
        compute_time_ms=round(compute_time, 2),
        timestamp=time.time()
    )


def _get_momentum_bucket(change_pct: float) -> str:
    """Map change to momentum bucket."""
    abs_change = abs(change_pct)
    is_bullish = change_pct >= 0
    
    if abs_change >= 5.0:
        return "EXTREME_BULLISH" if is_bullish else "EXTREME_BEARISH"
    elif abs_change >= 3.0:
        return "STRONG_BULLISH" if is_bullish else "STRONG_BEARISH"
    elif abs_change >= 1.0:
        return "MODERATE_BULLISH" if is_bullish else "MODERATE_BEARISH"
    return "NEUTRAL"


def _calculate_momentum_score(change_pct: float) -> int:
    """Calculate 0-100 score (Consistency check with RealTimeScannerEngine)."""
    abs_change = abs(change_pct)
    if abs_change >= 5.0: return 95 if change_pct > 0 else 5
    elif abs_change >= 4.0: return 85 if change_pct > 0 else 15
    elif abs_change >= 3.0: return 75 if change_pct > 0 else 25
    elif abs_change >= 2.0: return 65 if change_pct > 0 else 35
    elif abs_change >= 1.0: return 55 if change_pct > 0 else 45
    return 50


class IndicatorWorker:
    """
    Multiprocessing-based indicator worker.
    Runs computations in separate processes to avoid GIL.
    """
    
    def __init__(self, num_workers: int = None):
        self.num_workers = num_workers or max(1, mp.cpu_count() - 1)
        self._pool: Optional[mp.Pool] = None
        self._is_running = False
        self._compute_count = 0
        self._total_compute_time_ms = 0.0
    
    def start(self):
        """Start the worker pool."""
        if self._is_running:
            return
        
        try:
            self._pool = mp.Pool(processes=self.num_workers)
            self._is_running = True
            logger.info(f"Started indicator worker pool with {self.num_workers} processes")
        except Exception as e:
            logger.error(f"Failed to start worker pool: {e}")
            self._is_running = False
    
    def stop(self):
        """Stop the worker pool."""
        if self._pool:
            self._pool.close()
            self._pool.join()
            self._pool = None
        self._is_running = False
        logger.info("Stopped indicator worker pool")
    
    def compute_batch(self, tasks: List[ComputeTask]) -> List[ComputeResult]:
        """Compute indicators for multiple symbols in parallel."""
        start_time = time.perf_counter()
        
        if not self._is_running or not self._pool:
            # Fallback to single-process
            results = [compute_indicators_process(task) for task in tasks]
        else:
            try:
                results = self._pool.map(compute_indicators_process, tasks)
            except Exception as e:
                logger.error(f"Batch compute error: {e}")
                # Use metrics if available
                try:
                    from core.observability.metrics import get_metrics
                    get_metrics().record_worker_job("indicator_compute_batch", time.perf_counter() - start_time, False)
                except ImportError:
                    pass
                return []
        
        duration = time.perf_counter() - start_time
        
        # Update internal stats
        for result in results:
            self._compute_count += 1
            self._total_compute_time_ms += result.compute_time_ms
        
        # Record to Prometheus
        try:
            from core.observability.metrics import get_metrics
            get_metrics().record_worker_job("indicator_compute_batch", duration, True)
        except ImportError:
            pass
            
        return results
    
    def compute_single(self, task: ComputeTask) -> ComputeResult:
        """Compute indicators for a single symbol."""
        if not self._is_running or not self._pool:
            result = compute_indicators_process(task)
        else:
            try:
                result = self._pool.apply(compute_indicators_process, (task,))
            except Exception as e:
                logger.error(f"Single compute error: {e}")
                result = compute_indicators_process(task)
        
        self._compute_count += 1
        self._total_compute_time_ms += result.compute_time_ms
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        avg_time = (
            self._total_compute_time_ms / self._compute_count
        ) if self._compute_count > 0 else 0
        
        return {
            'is_running': self._is_running,
            'num_workers': self.num_workers,
            'compute_count': self._compute_count,
            'avg_compute_time_ms': round(avg_time, 2),
            'total_compute_time_ms': round(self._total_compute_time_ms, 2)
        }


# =============================================================================
# Global Worker Instance
# =============================================================================
_indicator_worker: Optional[IndicatorWorker] = None


def get_indicator_worker() -> IndicatorWorker:
    """Get the global indicator worker instance."""
    global _indicator_worker
    if _indicator_worker is None:
        _indicator_worker = IndicatorWorker()
    return _indicator_worker


def start_indicator_workers():
    """Start the indicator worker pool."""
    worker = get_indicator_worker()
    worker.start()


def stop_indicator_workers():
    """Stop the indicator worker pool."""
    global _indicator_worker
    if _indicator_worker:
        _indicator_worker.stop()
        _indicator_worker = None
