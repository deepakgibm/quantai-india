"""
Drift Monitor Module
Real-time monitoring and alert system for strategy drift
"""

import numpy as np
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import json

from .distribution_compare import DistributionCompare
from .drift_metrics import DriftMetricsCalculator, DriftMetrics
from .drift_detector import DriftDetector, DriftSeverity

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of drift alerts"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BOT_PAUSE = "bot_pause"
    REBACKTEST_REQUIRED = "rebacktest_required"


@dataclass
class DriftAlert:
    """A drift alert"""
    timestamp: datetime
    alert_type: AlertType
    strategy_name: str
    message: str
    metrics: Dict[str, Any]
    severity: DriftSeverity
    action_required: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'alert_type': self.alert_type.value,
            'strategy_name': self.strategy_name,
            'message': self.message,
            'metrics': self.metrics,
            'severity': self.severity.value,
            'action_required': self.action_required,
            'acknowledged': self.acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }


class DriftMonitor:
    """
    Real-time strategy drift monitor
    
    Features:
    - Continuous monitoring of live vs backtest performance
    - Multiple alert severity levels
    - Auto-trigger actions (pause, re-backtest)
    - Alert acknowledgment workflow
    """
    
    def __init__(
        self,
        strategy_name: str,
        check_interval_minutes: int = 60,
        auto_pause_on_critical: bool = True
    ):
        self.strategy_name = strategy_name
        self.check_interval = timedelta(minutes=check_interval_minutes)
        self.auto_pause_on_critical = auto_pause_on_critical
        
        # Components
        self.detector = DriftDetector()
        self.distribution_compare = DistributionCompare()
        self.metrics_calculator = DriftMetricsCalculator()
        
        # State
        self.is_paused = False
        self.last_check: Optional[datetime] = None
        self.backtest_returns: List[float] = []
        self.live_returns: List[float] = []
        self.alerts: List[DriftAlert] = []
        
        # Callbacks
        self._on_alert_callbacks: List[Callable[[DriftAlert], None]] = []
        self._on_pause_callbacks: List[Callable[[str], None]] = []
    
    def set_baseline(
        self,
        backtest_returns: List[float],
        backtest_sharpe: float
    ) -> None:
        """Set backtest baseline for comparison"""
        self.backtest_returns = backtest_returns
        self.backtest_sharpe = backtest_sharpe
        logger.info(f"Baseline set: {len(backtest_returns)} returns, Sharpe={backtest_sharpe:.2f}")
    
    def add_live_return(self, return_pct: float) -> Optional[DriftAlert]:
        """
        Add a new live trade return and check for drift
        
        Args:
            return_pct: Trade return as decimal (0.05 = 5%)
            
        Returns:
            Alert if drift detected, None otherwise
        """
        self.live_returns.append(return_pct)
        
        # Check if enough data for analysis
        if len(self.live_returns) < 10:
            return None
        
        # Rate limit checks
        now = datetime.now()
        if self.last_check and (now - self.last_check) < self.check_interval:
            return None
        
        self.last_check = now
        
        # Run drift check
        return self._check_drift()
    
    def _check_drift(self) -> Optional[DriftAlert]:
        """Perform drift analysis"""
        if not self.backtest_returns or len(self.live_returns) < 10:
            return None
        
        # Calculate live metrics
        live_metrics = self.metrics_calculator.calculate(self.live_returns)
        live_sharpe = live_metrics.rolling_sharpe
        
        # Run detector
        result = self.detector.check_drift(
            backtest_returns=self.backtest_returns,
            live_returns=self.live_returns,
            backtest_sharpe=self.backtest_sharpe,
            live_sharpe=live_sharpe
        )
        
        if not result.drift_detected:
            return None
        
        # Create alert based on severity
        alert = self._create_alert(result, live_metrics)
        self.alerts.append(alert)
        
        # Trigger callbacks
        for callback in self._on_alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
        
        # Auto-pause on critical
        if result.severity == DriftSeverity.CRITICAL and self.auto_pause_on_critical:
            self._pause_strategy("Critical drift detected")
        
        return alert
    
    def _create_alert(
        self,
        drift_result,
        live_metrics: DriftMetrics
    ) -> DriftAlert:
        """Create alert from drift result"""
        # Determine alert type
        if drift_result.severity == DriftSeverity.CRITICAL:
            alert_type = AlertType.BOT_PAUSE
            action = "PAUSE TRADING IMMEDIATELY"
        elif drift_result.severity == DriftSeverity.HIGH:
            alert_type = AlertType.REBACKTEST_REQUIRED
            action = "Re-run backtest with recent data"
        elif drift_result.severity == DriftSeverity.MEDIUM:
            alert_type = AlertType.WARNING
            action = "Monitor closely, consider parameter adjustment"
        else:
            alert_type = AlertType.INFO
            action = "No immediate action required"
        
        # Build message
        messages = []
        if drift_result.sharpe_degraded:
            messages.append(f"Sharpe degraded: {drift_result.sharpe_delta:.2f}")
        if drift_result.distribution_shifted:
            messages.append(f"Distribution shift: KS stat={drift_result.ks_statistic:.3f}")
        if drift_result.psi_warning:
            messages.append(f"PSI warning: {drift_result.psi:.3f}")
        
        return DriftAlert(
            timestamp=datetime.now(),
            alert_type=alert_type,
            strategy_name=self.strategy_name,
            message=" | ".join(messages) or "Drift detected",
            metrics=live_metrics.to_dict(),
            severity=drift_result.severity,
            action_required=action
        )
    
    def _pause_strategy(self, reason: str) -> None:
        """Pause the strategy"""
        self.is_paused = True
        logger.critical(f"Strategy {self.strategy_name} PAUSED: {reason}")
        
        for callback in self._on_pause_callbacks:
            try:
                callback(reason)
            except Exception as e:
                logger.error(f"Pause callback failed: {e}")
    
    def resume_strategy(self, resumed_by: str) -> None:
        """Resume a paused strategy"""
        if not self.is_paused:
            return
        
        self.is_paused = False
        logger.info(f"Strategy {self.strategy_name} RESUMED by {resumed_by}")
    
    def acknowledge_alert(
        self,
        alert_index: int,
        acknowledged_by: str
    ) -> bool:
        """Acknowledge an alert"""
        if alert_index >= len(self.alerts):
            return False
        
        alert = self.alerts[alert_index]
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now()
        
        return True
    
    def get_unacknowledged_alerts(self) -> List[DriftAlert]:
        """Get all unacknowledged alerts"""
        return [a for a in self.alerts if not a.acknowledged]
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitor status"""
        return {
            'strategy_name': self.strategy_name,
            'is_paused': self.is_paused,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'live_trade_count': len(self.live_returns),
            'total_alerts': len(self.alerts),
            'unacknowledged_alerts': len(self.get_unacknowledged_alerts()),
            'current_metrics': self.metrics_calculator.calculate(
                self.live_returns
            ).to_dict() if len(self.live_returns) >= 10 else None
        }
    
    def on_alert(self, callback: Callable[[DriftAlert], None]) -> None:
        """Register alert callback"""
        self._on_alert_callbacks.append(callback)
    
    def on_pause(self, callback: Callable[[str], None]) -> None:
        """Register pause callback"""
        self._on_pause_callbacks.append(callback)
    
    def export_alerts(self, filepath: str) -> None:
        """Export alerts to JSON file"""
        data = [a.to_dict() for a in self.alerts]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Exported {len(data)} alerts to {filepath}")
