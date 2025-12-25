"""
Drift Metrics Module
Rolling and aggregate metrics for drift detection
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class RollingMetric:
    """A single rolling metric value"""
    timestamp: datetime
    value: float
    window_size: int
    sample_count: int


@dataclass
class DriftMetrics:
    """Collection of drift metrics"""
    # Sharpe metrics
    rolling_sharpe: float
    sharpe_z_score: float  # vs historical mean
    sharpe_percentile: float  # vs historical distribution
    
    # Return metrics
    rolling_return: float
    return_z_score: float
    cumulative_return: float
    
    # Volatility metrics
    rolling_volatility: float
    vol_ratio: float  # vs expected
    
    # Win rate
    rolling_win_rate: float
    win_rate_z_score: float
    
    # Drawdown
    current_drawdown: float
    max_rolling_drawdown: float
    
    # Timestamps
    window_start: datetime
    window_end: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sharpe': {
                'current': round(self.rolling_sharpe, 3),
                'z_score': round(self.sharpe_z_score, 2),
                'percentile': round(self.sharpe_percentile, 1)
            },
            'returns': {
                'rolling': round(self.rolling_return, 4),
                'z_score': round(self.return_z_score, 2),
                'cumulative': round(self.cumulative_return, 4)
            },
            'volatility': {
                'rolling': round(self.rolling_volatility, 4),
                'ratio_vs_expected': round(self.vol_ratio, 2)
            },
            'win_rate': {
                'current': round(self.rolling_win_rate, 2),
                'z_score': round(self.win_rate_z_score, 2)
            },
            'drawdown': {
                'current': round(self.current_drawdown, 4),
                'max_rolling': round(self.max_rolling_drawdown, 4)
            },
            'window': {
                'start': self.window_start.isoformat(),
                'end': self.window_end.isoformat()
            }
        }


class DriftMetricsCalculator:
    """
    Calculate rolling and aggregate metrics for drift detection
    
    Maintains historical baselines and computes z-scores
    """
    
    def __init__(
        self,
        window_days: int = 30,
        min_samples: int = 10,
        expected_sharpe: float = 1.0,
        expected_volatility: float = 0.15,  # 15% annual
        expected_win_rate: float = 0.5
    ):
        self.window_days = window_days
        self.min_samples = min_samples
        self.expected_sharpe = expected_sharpe
        self.expected_volatility = expected_volatility
        self.expected_win_rate = expected_win_rate
        
        # Historical values for z-score calculation
        self.historical_sharpes: deque = deque(maxlen=100)
        self.historical_returns: deque = deque(maxlen=100)
        self.historical_win_rates: deque = deque(maxlen=100)
        
        # Equity tracking
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.peak_equity: float = 0
    
    def calculate(
        self,
        returns: List[float],
        timestamps: Optional[List[datetime]] = None,
        win_flags: Optional[List[bool]] = None
    ) -> DriftMetrics:
        """
        Calculate drift metrics for given returns
        
        Args:
            returns: List of trade returns (as decimals, e.g., 0.05 for 5%)
            timestamps: Optional timestamps for each return
            win_flags: Optional list of True/False for wins/losses
        """
        returns_arr = np.array(returns)
        
        if len(returns_arr) < self.min_samples:
            logger.warning(f"Insufficient samples: {len(returns_arr)} < {self.min_samples}")
        
        # Timestamps
        now = datetime.now()
        if timestamps:
            window_end = max(timestamps)
            window_start = min(timestamps)
        else:
            window_end = now
            window_start = now - timedelta(days=self.window_days)
        
        # Rolling Sharpe
        mean_ret = np.mean(returns_arr)
        std_ret = np.std(returns_arr)
        rolling_sharpe = (mean_ret / (std_ret + 1e-8)) * np.sqrt(252)  # Annualized
        
        # Store for historical tracking
        self.historical_sharpes.append(rolling_sharpe)
        
        # Sharpe z-score
        if len(self.historical_sharpes) > 5:
            hist_mean = np.mean(list(self.historical_sharpes))
            hist_std = np.std(list(self.historical_sharpes))
            sharpe_z_score = (rolling_sharpe - hist_mean) / (hist_std + 1e-8)
        else:
            sharpe_z_score = (rolling_sharpe - self.expected_sharpe) / 0.5
        
        # Sharpe percentile
        if len(self.historical_sharpes) > 5:
            sharpe_percentile = stats.percentileofscore(
                list(self.historical_sharpes), rolling_sharpe
            )
        else:
            sharpe_percentile = 50.0
        
        # Return metrics
        rolling_return = mean_ret
        cumulative_return = np.prod(1 + returns_arr) - 1
        
        self.historical_returns.append(rolling_return)
        if len(self.historical_returns) > 5:
            ret_mean = np.mean(list(self.historical_returns))
            ret_std = np.std(list(self.historical_returns))
            return_z_score = (rolling_return - ret_mean) / (ret_std + 1e-8)
        else:
            return_z_score = 0.0
        
        # Volatility
        rolling_volatility = std_ret * np.sqrt(252)  # Annualized
        vol_ratio = rolling_volatility / (self.expected_volatility + 1e-8)
        
        # Win rate
        if win_flags is not None:
            rolling_win_rate = sum(win_flags) / len(win_flags) * 100
        else:
            rolling_win_rate = np.sum(returns_arr > 0) / len(returns_arr) * 100
        
        self.historical_win_rates.append(rolling_win_rate)
        if len(self.historical_win_rates) > 5:
            wr_mean = np.mean(list(self.historical_win_rates))
            wr_std = np.std(list(self.historical_win_rates))
            win_rate_z_score = (rolling_win_rate - wr_mean) / (wr_std + 1e-8)
        else:
            win_rate_z_score = (rolling_win_rate - self.expected_win_rate * 100) / 10
        
        # Drawdown
        equity = 1.0
        peak = 1.0
        max_dd = 0.0
        for ret in returns_arr:
            equity *= (1 + ret)
            peak = max(peak, equity)
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
        
        current_drawdown = (peak - equity) / peak
        
        return DriftMetrics(
            rolling_sharpe=rolling_sharpe,
            sharpe_z_score=sharpe_z_score,
            sharpe_percentile=sharpe_percentile,
            rolling_return=rolling_return,
            return_z_score=return_z_score,
            cumulative_return=cumulative_return,
            rolling_volatility=rolling_volatility,
            vol_ratio=vol_ratio,
            rolling_win_rate=rolling_win_rate,
            win_rate_z_score=win_rate_z_score,
            current_drawdown=current_drawdown,
            max_rolling_drawdown=max_dd,
            window_start=window_start,
            window_end=window_end
        )
    
    def get_baseline_summary(self) -> Dict[str, Any]:
        """Get summary of historical baselines"""
        return {
            'sharpe': {
                'mean': np.mean(list(self.historical_sharpes)) if self.historical_sharpes else 0,
                'std': np.std(list(self.historical_sharpes)) if self.historical_sharpes else 0,
                'count': len(self.historical_sharpes)
            },
            'returns': {
                'mean': np.mean(list(self.historical_returns)) if self.historical_returns else 0,
                'std': np.std(list(self.historical_returns)) if self.historical_returns else 0,
                'count': len(self.historical_returns)
            },
            'win_rate': {
                'mean': np.mean(list(self.historical_win_rates)) if self.historical_win_rates else 0,
                'std': np.std(list(self.historical_win_rates)) if self.historical_win_rates else 0,
                'count': len(self.historical_win_rates)
            }
        }


# Need scipy for percentileofscore
from scipy import stats
