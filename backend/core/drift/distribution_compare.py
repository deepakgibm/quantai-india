"""
Distribution Comparison Module
Compare live vs backtest return distributions
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from scipy import stats
import logging

logger = logging.getLogger(__name__)


@dataclass
class DistributionComparisonResult:
    """Result of distribution comparison"""
    # KS Test
    ks_statistic: float
    ks_pvalue: float
    ks_significant: bool  # p < 0.05
    
    # Means comparison
    backtest_mean: float
    live_mean: float
    mean_diff: float
    mean_diff_pct: float
    
    # Volatility comparison
    backtest_std: float
    live_std: float
    std_ratio: float
    
    # Skewness comparison
    backtest_skew: float
    live_skew: float
    skew_diff: float
    
    # Kurtosis comparison
    backtest_kurtosis: float
    live_kurtosis: float
    kurtosis_diff: float
    
    # Percentile comparison
    percentile_diffs: Dict[int, float]  # 5th, 25th, 50th, 75th, 95th
    
    # Overall assessment
    distributions_similar: bool
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ks_test': {
                'statistic': round(self.ks_statistic, 4),
                'pvalue': round(self.ks_pvalue, 4),
                'significant': self.ks_significant
            },
            'mean': {
                'backtest': round(self.backtest_mean, 6),
                'live': round(self.live_mean, 6),
                'diff': round(self.mean_diff, 6),
                'diff_pct': round(self.mean_diff_pct, 2)
            },
            'volatility': {
                'backtest': round(self.backtest_std, 6),
                'live': round(self.live_std, 6),
                'ratio': round(self.std_ratio, 2)
            },
            'skewness': {
                'backtest': round(self.backtest_skew, 4),
                'live': round(self.live_skew, 4),
                'diff': round(self.skew_diff, 4)
            },
            'kurtosis': {
                'backtest': round(self.backtest_kurtosis, 4),
                'live': round(self.live_kurtosis, 4),
                'diff': round(self.kurtosis_diff, 4)
            },
            'percentile_diffs': self.percentile_diffs,
            'distributions_similar': self.distributions_similar,
            'warnings': self.warnings
        }


class DistributionCompare:
    """
    Compare return distributions between backtest and live trading
    
    Detects statistical differences that may indicate:
    - Strategy degradation
    - Market regime change
    - Implementation issues
    """
    
    def __init__(
        self,
        significance_level: float = 0.05,
        mean_threshold_pct: float = 50.0,  # Max mean diff %
        std_ratio_threshold: float = 2.0,  # Max vol ratio
        skew_threshold: float = 1.0,
        kurtosis_threshold: float = 2.0
    ):
        self.significance_level = significance_level
        self.mean_threshold_pct = mean_threshold_pct
        self.std_ratio_threshold = std_ratio_threshold
        self.skew_threshold = skew_threshold
        self.kurtosis_threshold = kurtosis_threshold
    
    def compare(
        self,
        backtest_returns: List[float],
        live_returns: List[float]
    ) -> DistributionComparisonResult:
        """
        Compare backtest vs live return distributions
        
        Args:
            backtest_returns: List of backtest trade returns
            live_returns: List of live trade returns
            
        Returns:
            Comparison result with statistics and warnings
        """
        bt = np.array(backtest_returns)
        live = np.array(live_returns)
        
        warnings = []
        
        # KS Test
        ks_stat, ks_pvalue = stats.ks_2samp(bt, live)
        ks_significant = ks_pvalue < self.significance_level
        
        if ks_significant:
            warnings.append(f"KS test significant (p={ks_pvalue:.4f}): distributions differ")
        
        # Means
        bt_mean = np.mean(bt)
        live_mean = np.mean(live)
        mean_diff = live_mean - bt_mean
        mean_diff_pct = abs(mean_diff / (abs(bt_mean) + 1e-8)) * 100
        
        if mean_diff_pct > self.mean_threshold_pct:
            warnings.append(f"Mean differs by {mean_diff_pct:.1f}%")
        
        # Standard deviation
        bt_std = np.std(bt)
        live_std = np.std(live)
        std_ratio = max(live_std, bt_std) / (min(live_std, bt_std) + 1e-8)
        
        if std_ratio > self.std_ratio_threshold:
            warnings.append(f"Volatility ratio {std_ratio:.2f}x exceeds threshold")
        
        # Skewness
        bt_skew = stats.skew(bt)
        live_skew = stats.skew(live)
        skew_diff = abs(live_skew - bt_skew)
        
        if skew_diff > self.skew_threshold:
            warnings.append(f"Skewness differs by {skew_diff:.2f}")
        
        # Kurtosis
        bt_kurtosis = stats.kurtosis(bt)
        live_kurtosis = stats.kurtosis(live)
        kurtosis_diff = abs(live_kurtosis - bt_kurtosis)
        
        if kurtosis_diff > self.kurtosis_threshold:
            warnings.append(f"Kurtosis differs by {kurtosis_diff:.2f}")
        
        # Percentile comparison
        percentiles = [5, 25, 50, 75, 95]
        bt_pcts = np.percentile(bt, percentiles)
        live_pcts = np.percentile(live, percentiles)
        percentile_diffs = {
            p: round(live_pcts[i] - bt_pcts[i], 6)
            for i, p in enumerate(percentiles)
        }
        
        # Overall assessment
        distributions_similar = len(warnings) == 0 and not ks_significant
        
        return DistributionComparisonResult(
            ks_statistic=ks_stat,
            ks_pvalue=ks_pvalue,
            ks_significant=ks_significant,
            backtest_mean=bt_mean,
            live_mean=live_mean,
            mean_diff=mean_diff,
            mean_diff_pct=mean_diff_pct,
            backtest_std=bt_std,
            live_std=live_std,
            std_ratio=std_ratio,
            backtest_skew=bt_skew,
            live_skew=live_skew,
            skew_diff=skew_diff,
            backtest_kurtosis=bt_kurtosis,
            live_kurtosis=live_kurtosis,
            kurtosis_diff=kurtosis_diff,
            percentile_diffs=percentile_diffs,
            distributions_similar=distributions_similar,
            warnings=warnings
        )
    
    def compute_wasserstein_distance(
        self,
        backtest_returns: List[float],
        live_returns: List[float]
    ) -> float:
        """
        Compute Wasserstein (Earth Mover's) distance
        
        More sensitive to distribution shape than KS test
        """
        bt = np.array(backtest_returns)
        live = np.array(live_returns)
        
        return stats.wasserstein_distance(bt, live)
    
    def compute_jensen_shannon_divergence(
        self,
        backtest_returns: List[float],
        live_returns: List[float],
        n_bins: int = 50
    ) -> float:
        """
        Compute Jensen-Shannon Divergence
        
        Symmetric version of KL divergence, bounded [0, 1]
        """
        bt = np.array(backtest_returns)
        live = np.array(live_returns)
        
        # Create histogram bins spanning both distributions
        all_data = np.concatenate([bt, live])
        bins = np.linspace(all_data.min(), all_data.max(), n_bins + 1)
        
        # Compute histograms
        bt_hist, _ = np.histogram(bt, bins=bins, density=True)
        live_hist, _ = np.histogram(live, bins=bins, density=True)
        
        # Add small epsilon for numerical stability
        bt_hist = bt_hist + 1e-10
        live_hist = live_hist + 1e-10
        
        # Normalize
        bt_hist = bt_hist / bt_hist.sum()
        live_hist = live_hist / live_hist.sum()
        
        # Average distribution
        m = (bt_hist + live_hist) / 2
        
        # KL divergences
        kl_bt = np.sum(bt_hist * np.log(bt_hist / m))
        kl_live = np.sum(live_hist * np.log(live_hist / m))
        
        # JS divergence
        js_div = (kl_bt + kl_live) / 2
        
        return float(js_div)
