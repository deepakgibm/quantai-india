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
    
    # Extract price data
    closes = [c.get('close', 0) for c in candles]
    highs = [c.get('high', 0) for c in candles]
    lows = [c.get('low', 0) for c in candles]
    volumes = [c.get('volume', 0) for c in candles]
    
    # Compute indicators
    indicators = {}
    
    # SMA
    indicators['sma_20'] = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
    indicators['sma_50'] = sum(closes[-50:]) / 50 if len(closes) >= 50 else indicators['sma_20']
    
    # EMA
    indicators['ema_9'] = _ema(closes, 9)
    indicators['ema_21'] = _ema(closes, 21)
    indicators['ema_50'] = _ema(closes, 50)
    
    # RSI
    indicators['rsi_14'] = _rsi(closes, 14)
    
    # MACD
    ema_12 = _ema(closes, 12)
    ema_26 = _ema(closes, 26)
    indicators['macd_line'] = ema_12 - ema_26
    indicators['macd_signal'] = indicators['macd_line'] * 0.9  # Simplified
    indicators['macd_histogram'] = indicators['macd_line'] - indicators['macd_signal']
    
    # Bollinger Bands
    sma = indicators['sma_20']
    if len(closes) >= 20:
        variance = sum((x - sma) ** 2 for x in closes[-20:]) / 20
        std = variance ** 0.5
        indicators['bb_upper'] = sma + (2 * std)
        indicators['bb_lower'] = sma - (2 * std)
        indicators['bb_middle'] = sma
    else:
        indicators['bb_upper'] = closes[-1]
        indicators['bb_lower'] = closes[-1]
        indicators['bb_middle'] = closes[-1]
    
    # ATR
    if len(highs) >= 14:
        tr_values = []
        for i in range(-14, 0):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_values.append(tr)
        indicators['atr_14'] = sum(tr_values) / 14
    else:
        indicators['atr_14'] = 0
    
    # Current price data
    indicators['current_close'] = closes[-1]
    indicators['prev_close'] = closes[-2] if len(closes) >= 2 else closes[-1]
    indicators['change_pct'] = (
        (closes[-1] - closes[-2]) / closes[-2] * 100
    ) if len(closes) >= 2 and closes[-2] > 0 else 0
    
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
    if closes[-1] < indicators['bb_lower']:
        signals.append('BB_OVERSOLD')
    elif closes[-1] > indicators['bb_upper']:
        signals.append('BB_OVERBOUGHT')
    
    # Build snapshot
    snapshot = {
        'symbol': task.symbol,
        'interval': task.interval,
        'ltp': closes[-1],
        'prev_close': indicators['prev_close'],
        'change_pct': round(indicators['change_pct'], 2),
        'indicators': {k: round(v, 4) for k, v in indicators.items()},
        'signals': signals,
        'momentum_bucket': _get_momentum_bucket(indicators['change_pct']),
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


def _ema(data: List[float], period: int) -> float:
    """Exponential Moving Average."""
    if len(data) < period:
        return data[-1] if data else 0.0
    
    multiplier = 2 / (period + 1)
    ema = sum(data[:period]) / period
    
    for price in data[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema


def _rsi(closes: List[float], period: int = 14) -> float:
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return 50.0
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


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
