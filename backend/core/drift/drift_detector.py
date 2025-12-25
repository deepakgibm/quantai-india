"""
Drift Detection Module
Detect when live performance deviates from backtest expectations
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class DriftSeverity(Enum):
    """Severity level of detected drift"""
    NONE = "none"
    LOW = "low"  # Monitor
    MEDIUM = "medium"  # Alert
    HIGH = "high"  # Pause recommended
    CRITICAL = "critical"  # Auto-pause


@dataclass
class DriftAlert:
    """Represents a drift detection alert"""
    alert_id: str
    strategy_name: str
    drift_type: str  # sharpe, distribution, psi
    severity: DriftSeverity
    metric_name: str
    expected_value: float
    actual_value: float
    delta: float
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    requires_action: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'strategy_name': self.strategy_name,
            'drift_type': self.drift_type,
            'severity': self.severity.value,
            'metric_name': self.metric_name,
            'expected_value': round(self.expected_value, 4),
            'actual_value': round(self.actual_value, 4),
            'delta': round(self.delta, 4),
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'requires_action': self.requires_action
        }


@dataclass
class DriftCheckResult:
    """Complete drift check result"""
    strategy_name: str
    check_timestamp: datetime
    
    # Overall assessment
    has_drift: bool
    max_severity: DriftSeverity
    
    # Individual checks
    sharpe_drift: Optional[DriftAlert] = None
    distribution_drift: Optional[DriftAlert] = None
    psi_drift: Optional[DriftAlert] = None
    
    # All alerts
    alerts: List[DriftAlert] = field(default_factory=list)
    
    # Recommendations
    should_pause: bool = False
    should_rebacktest: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_name': self.strategy_name,
            'check_timestamp': self.check_timestamp.isoformat(),
            'has_drift': self.has_drift,
            'max_severity': self.max_severity.value,
            'alert_count': len(self.alerts),
            'alerts': [a.to_dict() for a in self.alerts],
            'should_pause': self.should_pause,
            'should_rebacktest': self.should_rebacktest
        }


class DriftDetector:
    """
    Detects performance drift between live and backtest results
    
    Metrics:
    - Rolling Sharpe delta
    - KS test for return distributions
    - PSI (Population Stability Index)
    """
    
    # Thresholds
    SHARPE_DELTA_LOW = 0.3
    SHARPE_DELTA_MEDIUM = 0.5
    SHARPE_DELTA_HIGH = 0.8
    
    KS_PVALUE_LOW = 0.1
    KS_PVALUE_MEDIUM = 0.05
    KS_PVALUE_HIGH = 0.01
    
    PSI_LOW = 0.1
    PSI_MEDIUM = 0.2
    PSI_HIGH = 0.25
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self._alert_counter = 0
    
    def check_drift(
        self,
        backtest_returns: List[float],
        live_returns: List[float],
        backtest_sharpe: float,
        live_sharpe: float
    ) -> DriftCheckResult:
        """
        Perform comprehensive drift check
        
        Args:
            backtest_returns: Historical backtest trade returns
            live_returns: Live trading returns (same period or recent)
            backtest_sharpe: Sharpe ratio from backtest
            live_sharpe: Sharpe ratio from live trading
            
        Returns:
            DriftCheckResult with all alerts and recommendations
        """
        alerts = []
        
        # 1. Sharpe ratio drift
        sharpe_alert = self._check_sharpe_drift(backtest_sharpe, live_sharpe)
        if sharpe_alert:
            alerts.append(sharpe_alert)
        
        # 2. Distribution drift (KS test)
        if len(live_returns) >= 10:
            dist_alert = self._check_distribution_drift(backtest_returns, live_returns)
            if dist_alert:
                alerts.append(dist_alert)
        
        # 3. PSI calculation
        if len(live_returns) >= 10:
            psi_alert = self._check_psi_drift(backtest_returns, live_returns)
            if psi_alert:
                alerts.append(psi_alert)
        
        # Determine overall severity
        has_drift = len(alerts) > 0
        max_severity = DriftSeverity.NONE
        
        for alert in alerts:
            if alert.severity.value > max_severity.value:
                max_severity = alert.severity
        
        # Recommendations
        should_pause = max_severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]
        should_rebacktest = max_severity in [DriftSeverity.MEDIUM, DriftSeverity.HIGH, DriftSeverity.CRITICAL]
        
        return DriftCheckResult(
            strategy_name=self.strategy_name,
            check_timestamp=datetime.utcnow(),
            has_drift=has_drift,
            max_severity=max_severity,
            sharpe_drift=sharpe_alert,
            distribution_drift=next((a for a in alerts if a.drift_type == 'distribution'), None),
            psi_drift=next((a for a in alerts if a.drift_type == 'psi'), None),
            alerts=alerts,
            should_pause=should_pause,
            should_rebacktest=should_rebacktest
        )
    
    def _check_sharpe_drift(
        self,
        backtest_sharpe: float,
        live_sharpe: float
    ) -> Optional[DriftAlert]:
        """Check for Sharpe ratio degradation"""
        delta = backtest_sharpe - live_sharpe
        
        if delta <= self.SHARPE_DELTA_LOW:
            return None
        
        # Determine severity
        if delta >= self.SHARPE_DELTA_HIGH:
            severity = DriftSeverity.HIGH
            message = f"Critical Sharpe degradation: {backtest_sharpe:.2f} → {live_sharpe:.2f}"
        elif delta >= self.SHARPE_DELTA_MEDIUM:
            severity = DriftSeverity.MEDIUM
            message = f"Significant Sharpe degradation detected"
        else:
            severity = DriftSeverity.LOW
            message = f"Minor Sharpe degradation observed"
        
        self._alert_counter += 1
        return DriftAlert(
            alert_id=f"DRIFT-{self._alert_counter:05d}",
            strategy_name=self.strategy_name,
            drift_type="sharpe",
            severity=severity,
            metric_name="sharpe_ratio",
            expected_value=backtest_sharpe,
            actual_value=live_sharpe,
            delta=delta,
            message=message,
            requires_action=severity in [DriftSeverity.MEDIUM, DriftSeverity.HIGH, DriftSeverity.CRITICAL]
        )
    
    def _check_distribution_drift(
        self,
        backtest_returns: List[float],
        live_returns: List[float]
    ) -> Optional[DriftAlert]:
        """Check for distribution shift using KS test"""
        # Kolmogorov-Smirnov test
        ks_stat, p_value = stats.ks_2samp(backtest_returns, live_returns)
        
        if p_value > self.KS_PVALUE_LOW:
            return None  # No significant difference
        
        # Determine severity based on p-value
        if p_value <= self.KS_PVALUE_HIGH:
            severity = DriftSeverity.HIGH
            message = f"Statistically significant distribution shift (p={p_value:.4f})"
        elif p_value <= self.KS_PVALUE_MEDIUM:
            severity = DriftSeverity.MEDIUM
            message = f"Moderate distribution shift detected (p={p_value:.4f})"
        else:
            severity = DriftSeverity.LOW
            message = f"Minor distribution shift observed (p={p_value:.4f})"
        
        self._alert_counter += 1
        return DriftAlert(
            alert_id=f"DRIFT-{self._alert_counter:05d}",
            strategy_name=self.strategy_name,
            drift_type="distribution",
            severity=severity,
            metric_name="ks_test_pvalue",
            expected_value=1.0,  # Expected: no difference (p=1)
            actual_value=p_value,
            delta=1.0 - p_value,
            message=message,
            requires_action=severity in [DriftSeverity.MEDIUM, DriftSeverity.HIGH]
        )
    
    def _check_psi_drift(
        self,
        backtest_returns: List[float],
        live_returns: List[float]
    ) -> Optional[DriftAlert]:
        """Check for Population Stability Index drift"""
        psi = self._calculate_psi(backtest_returns, live_returns)
        
        if psi < self.PSI_LOW:
            return None
        
        # Determine severity
        if psi >= self.PSI_HIGH:
            severity = DriftSeverity.HIGH
            message = f"High PSI indicates major distribution shift (PSI={psi:.3f})"
        elif psi >= self.PSI_MEDIUM:
            severity = DriftSeverity.MEDIUM
            message = f"Moderate PSI drift detected (PSI={psi:.3f})"
        else:
            severity = DriftSeverity.LOW
            message = f"Minor PSI drift observed (PSI={psi:.3f})"
        
        self._alert_counter += 1
        return DriftAlert(
            alert_id=f"DRIFT-{self._alert_counter:05d}",
            strategy_name=self.strategy_name,
            drift_type="psi",
            severity=severity,
            metric_name="psi",
            expected_value=0.0,
            actual_value=psi,
            delta=psi,
            message=message,
            requires_action=severity in [DriftSeverity.MEDIUM, DriftSeverity.HIGH]
        )
    
    def _calculate_psi(
        self,
        expected: List[float],
        actual: List[float],
        n_bins: int = 10
    ) -> float:
        """
        Calculate Population Stability Index
        
        PSI < 0.1: No significant shift
        PSI 0.1-0.2: Moderate shift
        PSI > 0.2: Significant shift
        """
        # Create bins from expected distribution
        min_val = min(min(expected), min(actual))
        max_val = max(max(expected), max(actual))
        
        bins = np.linspace(min_val - 0.001, max_val + 0.001, n_bins + 1)
        
        # Calculate proportions
        expected_counts, _ = np.histogram(expected, bins=bins)
        actual_counts, _ = np.histogram(actual, bins=bins)
        
        # Convert to proportions (avoid zero)
        expected_pct = (expected_counts + 1) / (len(expected) + n_bins)
        actual_pct = (actual_counts + 1) / (len(actual) + n_bins)
        
        # Calculate PSI
        psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
        
        return float(psi)
