"""
SEBI-Safe Audit & Reporting Module
Immutable decision logging and compliance reporting
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of trading decisions to log"""
    SIGNAL_GENERATED = "signal_generated"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    DRIFT_DETECTED = "drift_detected"
    MANUAL_OVERRIDE = "manual_override"


@dataclass
class DecisionLog:
    """Immutable log entry for a trading decision"""
    log_id: str
    timestamp: datetime
    decision_type: DecisionType
    strategy_name: str
    strategy_version: str
    
    # Decision details
    symbol: Optional[str] = None
    action: Optional[str] = None  # BUY, SELL, HOLD
    quantity: Optional[int] = None
    price: Optional[float] = None
    
    # Explainability
    reason: str = ""
    indicators_used: List[str] = field(default_factory=list)
    indicator_values: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    
    # Context
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    risk_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Integrity
    prev_log_hash: str = ""
    log_hash: str = ""
    
    def compute_hash(self) -> str:
        """Compute SHA-256 hash of log entry"""
        data = {
            'log_id': self.log_id,
            'timestamp': self.timestamp.isoformat(),
            'decision_type': self.decision_type.value,
            'strategy_name': self.strategy_name,
            'strategy_version': self.strategy_version,
            'symbol': self.symbol,
            'action': self.action,
            'quantity': self.quantity,
            'price': self.price,
            'reason': self.reason,
            'confidence': self.confidence,
            'prev_log_hash': self.prev_log_hash
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'log_id': self.log_id,
            'timestamp': self.timestamp.isoformat(),
            'decision_type': self.decision_type.value,
            'strategy_name': self.strategy_name,
            'strategy_version': self.strategy_version,
            'symbol': self.symbol,
            'action': self.action,
            'quantity': self.quantity,
            'price': self.price,
            'reason': self.reason,
            'indicators_used': self.indicators_used,
            'indicator_values': self.indicator_values,
            'confidence': self.confidence,
            'log_hash': self.log_hash
        }


class AuditLogger:
    """
    Immutable decision logging for SEBI compliance
    
    Features:
    - Tamper-evident chain (each log references previous hash)
    - Complete explainability
    - No forward-looking claims
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "audit_logs")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._logs: List[DecisionLog] = []
        self._log_counter = 0
        self._last_hash = "GENESIS"
    
    def log_decision(
        self,
        decision_type: DecisionType,
        strategy_name: str,
        strategy_version: str,
        symbol: Optional[str] = None,
        action: Optional[str] = None,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        reason: str = "",
        indicators_used: Optional[List[str]] = None,
        indicator_values: Optional[Dict[str, float]] = None,
        confidence: float = 0.0,
        market_conditions: Optional[Dict[str, Any]] = None,
        risk_parameters: Optional[Dict[str, Any]] = None
    ) -> DecisionLog:
        """
        Log a trading decision
        
        Returns the immutable log entry
        """
        self._log_counter += 1
        
        log = DecisionLog(
            log_id=f"LOG-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._log_counter:06d}",
            timestamp=datetime.utcnow(),
            decision_type=decision_type,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            reason=reason,
            indicators_used=indicators_used or [],
            indicator_values=indicator_values or {},
            confidence=confidence,
            market_conditions=market_conditions or {},
            risk_parameters=risk_parameters or {},
            prev_log_hash=self._last_hash
        )
        
        # Compute and set hash
        log.log_hash = log.compute_hash()
        self._last_hash = log.log_hash
        
        # Store
        self._logs.append(log)
        
        # Persist to file
        self._persist_log(log)
        
        logger.info(f"Decision logged: {log.log_id} - {decision_type.value}")
        
        return log
    
    def _persist_log(self, log: DecisionLog) -> None:
        """Persist log to file (append-only)"""
        date_str = log.timestamp.strftime('%Y-%m-%d')
        log_file = self.storage_path / f"audit_{date_str}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log.to_dict()) + '\n')
    
    def verify_chain_integrity(self) -> Tuple[bool, Optional[str]]:
        """Verify the integrity of the log chain"""
        if not self._logs:
            return True, None
        
        prev_hash = "GENESIS"
        
        for log in self._logs:
            # Check previous hash matches
            if log.prev_log_hash != prev_hash:
                return False, f"Chain broken at {log.log_id}: expected prev_hash {prev_hash}"
            
            # Verify current hash
            computed = log.compute_hash()
            if computed != log.log_hash:
                return False, f"Hash mismatch at {log.log_id}: computed {computed}, stored {log.log_hash}"
            
            prev_hash = log.log_hash
        
        return True, None
    
    def get_logs_for_period(
        self,
        start_date: datetime,
        end_date: datetime,
        strategy_name: Optional[str] = None
    ) -> List[DecisionLog]:
        """Get logs for a specific period"""
        filtered = [
            log for log in self._logs
            if start_date <= log.timestamp <= end_date
        ]
        
        if strategy_name:
            filtered = [log for log in filtered if log.strategy_name == strategy_name]
        
        return filtered


@dataclass
class AuditReport:
    """SEBI-compliant audit report"""
    report_id: str
    generated_at: datetime
    
    # Period
    start_date: datetime
    end_date: datetime
    
    # Strategy info
    strategy_name: str
    strategy_version: str
    
    # Summary
    total_decisions: int
    total_trades: int
    total_signals: int
    
    # Performance (historical only - no forward claims)
    realized_pnl: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    
    # Risk compliance
    risk_parameters_used: Dict[str, Any]
    stop_loss_triggered_count: int
    max_position_size_used: float
    
    # Integrity
    chain_verified: bool
    
    # Disclaimer
    disclaimer: str = (
        "DISCLAIMER: This report contains historical performance data. "
        "Past performance is not indicative of future results. "
        "All data is for informational purposes only and does not constitute investment advice."
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at.isoformat(),
            'period': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat()
            },
            'strategy': {
                'name': self.strategy_name,
                'version': self.strategy_version
            },
            'summary': {
                'total_decisions': self.total_decisions,
                'total_trades': self.total_trades,
                'total_signals': self.total_signals
            },
            'performance': {
                'realized_pnl': round(self.realized_pnl, 2),
                'win_rate': round(self.win_rate, 2),
                'max_drawdown': round(self.max_drawdown, 2),
                'sharpe_ratio': round(self.sharpe_ratio, 3)
            },
            'risk_compliance': {
                'parameters': self.risk_parameters_used,
                'stop_loss_triggered': self.stop_loss_triggered_count,
                'max_position_size': self.max_position_size_used
            },
            'chain_verified': self.chain_verified,
            'disclaimer': self.disclaimer
        }


class ReportGenerator:
    """Generate SEBI-compliant audit reports"""
    
    def __init__(self, audit_logger: AuditLogger):
        self.logger = audit_logger
        self._report_counter = 0
    
    def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        strategy_name: str,
        strategy_version: str,
        performance_metrics: Dict[str, float]
    ) -> AuditReport:
        """Generate a compliance report"""
        self._report_counter += 1
        
        # Get logs for period
        logs = self.logger.get_logs_for_period(start_date, end_date, strategy_name)
        
        # Count by type
        trades = [l for l in logs if l.decision_type in [
            DecisionType.ORDER_FILLED, DecisionType.POSITION_CLOSED
        ]]
        signals = [l for l in logs if l.decision_type == DecisionType.SIGNAL_GENERATED]
        stop_losses = [l for l in logs if l.decision_type == DecisionType.STOP_LOSS_TRIGGERED]
        
        # Verify chain
        is_valid, error = self.logger.verify_chain_integrity()
        
        # Get risk parameters from logs
        risk_params = {}
        for log in logs:
            if log.risk_parameters:
                risk_params.update(log.risk_parameters)
        
        return AuditReport(
            report_id=f"REPORT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._report_counter:04d}",
            generated_at=datetime.utcnow(),
            start_date=start_date,
            end_date=end_date,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            total_decisions=len(logs),
            total_trades=len(trades),
            total_signals=len(signals),
            realized_pnl=performance_metrics.get('realized_pnl', 0),
            win_rate=performance_metrics.get('win_rate', 0),
            max_drawdown=performance_metrics.get('max_drawdown', 0),
            sharpe_ratio=performance_metrics.get('sharpe_ratio', 0),
            risk_parameters_used=risk_params,
            stop_loss_triggered_count=len(stop_losses),
            max_position_size_used=performance_metrics.get('max_position_size', 0),
            chain_verified=is_valid
        )
