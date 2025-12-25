"""
Strategy Versioning System
Immutable version control with SHA-256 checksums
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import logging
import pickle
import os

logger = logging.getLogger(__name__)


class StrategyStatus(Enum):
    """Strategy deployment status"""
    DRAFT = "draft"  # Initial creation
    BACKTESTED = "backtested"  # Passed backtest
    VALIDATED = "validated"  # Passed WFA
    APPROVED = "approved"  # Approved for live
    LIVE = "live"  # Currently live trading
    RETIRED = "retired"  # No longer in use
    REJECTED = "rejected"  # Failed validation


@dataclass
class StrategyVersion:
    """Immutable strategy version"""
    name: str
    version_number: str  # Semantic versioning: 1.0.0
    version_hash: str  # SHA-256 of params + code
    
    # Configuration
    params: Dict[str, Any]
    param_hash: str  # Hash of just parameters
    
    # Optional ML model
    model_checksum: Optional[str] = None
    model_path: Optional[str] = None
    
    # Status
    status: StrategyStatus = StrategyStatus.DRAFT
    
    # Performance metrics (from testing)
    backtest_metrics: Optional[Dict[str, float]] = None
    wfa_metrics: Optional[Dict[str, float]] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    notes: str = ""
    
    # Audit trail
    status_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'version_number': self.version_number,
            'version_hash': self.version_hash,
            'params': self.params,
            'param_hash': self.param_hash,
            'model_checksum': self.model_checksum,
            'status': self.status.value,
            'backtest_metrics': self.backtest_metrics,
            'wfa_metrics': self.wfa_metrics,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'notes': self.notes
        }


class VersionManager:
    """
    Manages strategy versions with immutable checksums
    
    Features:
    - SHA-256 hashing of strategy code + parameters
    - Model checksum for ML strategies
    - Deployment gating workflow
    - Version history tracking
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or "strategy_versions"
        self._versions: Dict[str, List[StrategyVersion]] = {}
        
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
    
    def create_version(
        self,
        name: str,
        params: Dict[str, Any],
        code_version: str = "1.0.0",
        model_path: Optional[str] = None,
        created_by: str = "system",
        notes: str = ""
    ) -> StrategyVersion:
        """
        Create a new strategy version
        
        Args:
            name: Strategy name
            params: Strategy parameters
            code_version: Strategy code version
            model_path: Optional path to ML model file
            created_by: Username/system
            notes: Optional notes
            
        Returns:
            New StrategyVersion with computed checksums
        """
        # Compute parameter hash
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        
        # Compute version hash (params + code version)
        version_data = {
            'name': name,
            'params': params,
            'code_version': code_version
        }
        version_str = json.dumps(version_data, sort_keys=True)
        version_hash = hashlib.sha256(version_str.encode()).hexdigest()[:16]
        
        # Compute model checksum if provided
        model_checksum = None
        if model_path and os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                model_checksum = hashlib.sha256(f.read()).hexdigest()[:16]
        
        # Determine version number
        existing_versions = self._versions.get(name, [])
        if existing_versions:
            # Increment patch version
            last_version = existing_versions[-1].version_number
            parts = last_version.split('.')
            parts[-1] = str(int(parts[-1]) + 1)
            version_number = '.'.join(parts)
        else:
            version_number = "1.0.0"
        
        # Create version
        version = StrategyVersion(
            name=name,
            version_number=version_number,
            version_hash=version_hash,
            params=params,
            param_hash=param_hash,
            model_checksum=model_checksum,
            model_path=model_path,
            created_by=created_by,
            notes=notes
        )
        
        # Store version
        if name not in self._versions:
            self._versions[name] = []
        self._versions[name].append(version)
        
        logger.info(f"Created strategy version: {name} v{version_number} (hash: {version_hash})")
        
        return version
    
    def get_version(
        self,
        name: str,
        version_number: Optional[str] = None,
        version_hash: Optional[str] = None
    ) -> Optional[StrategyVersion]:
        """Get a specific strategy version"""
        if name not in self._versions:
            return None
        
        versions = self._versions[name]
        
        if version_hash:
            for v in versions:
                if v.version_hash == version_hash:
                    return v
        elif version_number:
            for v in versions:
                if v.version_number == version_number:
                    return v
        else:
            # Return latest
            return versions[-1] if versions else None
        
        return None
    
    def get_all_versions(self, name: str) -> List[StrategyVersion]:
        """Get all versions of a strategy"""
        return self._versions.get(name, [])
    
    def get_live_version(self, name: str) -> Optional[StrategyVersion]:
        """Get currently live version of a strategy"""
        for v in self._versions.get(name, []):
            if v.status == StrategyStatus.LIVE:
                return v
        return None
    
    def update_status(
        self,
        version: StrategyVersion,
        new_status: StrategyStatus,
        reason: str = "",
        updated_by: str = "system"
    ) -> bool:
        """
        Update strategy status with audit trail
        
        Returns True if status transition is valid
        """
        # Valid transitions
        valid_transitions = {
            StrategyStatus.DRAFT: [StrategyStatus.BACKTESTED, StrategyStatus.REJECTED],
            StrategyStatus.BACKTESTED: [StrategyStatus.VALIDATED, StrategyStatus.REJECTED],
            StrategyStatus.VALIDATED: [StrategyStatus.APPROVED, StrategyStatus.REJECTED],
            StrategyStatus.APPROVED: [StrategyStatus.LIVE, StrategyStatus.REJECTED],
            StrategyStatus.LIVE: [StrategyStatus.RETIRED],
            StrategyStatus.REJECTED: [StrategyStatus.DRAFT],  # Can retry
            StrategyStatus.RETIRED: []  # Terminal state
        }
        
        if new_status not in valid_transitions.get(version.status, []):
            logger.warning(f"Invalid status transition: {version.status.value} -> {new_status.value}")
            return False
        
        # Record history
        version.status_history.append({
            'from_status': version.status.value,
            'to_status': new_status.value,
            'timestamp': datetime.utcnow().isoformat(),
            'updated_by': updated_by,
            'reason': reason
        })
        
        # Update status
        old_status = version.status
        version.status = new_status
        
        logger.info(f"Strategy {version.name} v{version.version_number}: "
                   f"{old_status.value} -> {new_status.value}")
        
        return True
    
    def record_backtest_results(
        self,
        version: StrategyVersion,
        metrics: Dict[str, float]
    ) -> None:
        """Record backtest metrics for a version"""
        version.backtest_metrics = metrics
        
        # Auto-transition if passed
        if self._passed_backtest(metrics):
            self.update_status(version, StrategyStatus.BACKTESTED, "Backtest passed")
        else:
            self.update_status(version, StrategyStatus.REJECTED, "Backtest failed constraints")
    
    def record_wfa_results(
        self,
        version: StrategyVersion,
        metrics: Dict[str, float]
    ) -> None:
        """Record walk-forward analysis metrics"""
        version.wfa_metrics = metrics
        
        # Auto-transition if passed
        if self._passed_wfa(metrics):
            self.update_status(version, StrategyStatus.VALIDATED, "WFA passed")
        else:
            self.update_status(version, StrategyStatus.REJECTED, "WFA failed constraints")
    
    def _passed_backtest(self, metrics: Dict[str, float]) -> bool:
        """Check if backtest results pass minimum criteria"""
        if metrics.get('sharpe_ratio', 0) < 0.5:
            return False
        if metrics.get('max_drawdown_pct', 100) > 25:
            return False
        if metrics.get('win_rate', 0) < 35:
            return False
        if metrics.get('total_trades', 0) < 10:
            return False
        return True
    
    def _passed_wfa(self, metrics: Dict[str, float]) -> bool:
        """Check if WFA results pass minimum criteria"""
        if metrics.get('robustness_ratio', 0) < 0.5:
            return False
        if metrics.get('consistency', 0) < 50:
            return False
        return True
    
    def verify_integrity(self, version: StrategyVersion) -> bool:
        """Verify version hash integrity"""
        # Recompute hash
        version_data = {
            'name': version.name,
            'params': version.params,
            'code_version': version.version_number.split('.')[0] + ".0.0"
        }
        version_str = json.dumps(version_data, sort_keys=True)
        computed_hash = hashlib.sha256(version_str.encode()).hexdigest()[:16]
        
        # Compare
        if computed_hash != version.version_hash:
            logger.error(f"Version integrity check failed for {version.name} v{version.version_number}")
            return False
        
        return True
