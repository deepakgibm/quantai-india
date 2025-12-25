"""
Alert System API Router
API endpoints for drift alerts and notifications
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import logging

from database import get_db
from core.drift.drift_monitor import DriftMonitor, DriftAlert, AlertType
from core.drift.drift_detector import DriftSeverity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


# In-memory storage for monitors (in production, use Redis/DB)
_active_monitors: Dict[str, DriftMonitor] = {}


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertResponse(BaseModel):
    """Alert response model"""
    id: int
    timestamp: str
    alert_type: str
    strategy_name: str
    message: str
    severity: str
    action_required: str
    acknowledged: bool
    acknowledged_by: Optional[str] = None


class AlertAckRequest(BaseModel):
    """Alert acknowledgment request"""
    acknowledged_by: str


class CreateMonitorRequest(BaseModel):
    """Request to create a drift monitor"""
    strategy_name: str
    backtest_returns: List[float]
    backtest_sharpe: float
    check_interval_minutes: int = Field(60, ge=1, le=1440)
    auto_pause_on_critical: bool = True


class AddLiveReturnRequest(BaseModel):
    """Request to add live trading return"""
    strategy_name: str
    return_pct: float  # As decimal (0.05 = 5%)


class MonitorStatusResponse(BaseModel):
    """Monitor status response"""
    strategy_name: str
    is_paused: bool
    last_check: Optional[str]
    live_trade_count: int
    total_alerts: int
    unacknowledged_alerts: int


class AlertConfigRequest(BaseModel):
    """Alert configuration"""
    email_notifications: bool = False
    webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    pause_threshold: str = "critical"


# ============
# Endpoints
# ============

@router.post("/monitor/create")
async def create_monitor(request: CreateMonitorRequest):
    """
    Create a drift monitor for a strategy
    
    Sets up real-time monitoring with baseline from backtest
    """
    if request.strategy_name in _active_monitors:
        raise HTTPException(
            status_code=400,
            detail=f"Monitor for {request.strategy_name} already exists"
        )
    
    monitor = DriftMonitor(
        strategy_name=request.strategy_name,
        check_interval_minutes=request.check_interval_minutes,
        auto_pause_on_critical=request.auto_pause_on_critical
    )
    
    monitor.set_baseline(
        backtest_returns=request.backtest_returns,
        backtest_sharpe=request.backtest_sharpe
    )
    
    _active_monitors[request.strategy_name] = monitor
    
    return {
        "status": "success",
        "message": f"Monitor created for {request.strategy_name}",
        "baseline_trades": len(request.backtest_returns),
        "baseline_sharpe": request.backtest_sharpe
    }


@router.post("/monitor/add_return")
async def add_live_return(request: AddLiveReturnRequest):
    """
    Add a live trading return and check for drift
    
    Returns alert if drift detected
    """
    if request.strategy_name not in _active_monitors:
        raise HTTPException(
            status_code=404,
            detail=f"No monitor found for {request.strategy_name}"
        )
    
    monitor = _active_monitors[request.strategy_name]
    
    alert = monitor.add_live_return(request.return_pct)
    
    response = {
        "status": "success",
        "live_trade_count": len(monitor.live_returns),
        "is_paused": monitor.is_paused
    }
    
    if alert:
        response["alert"] = alert.to_dict()
    
    return response


@router.get("/monitor/{strategy_name}/status", response_model=MonitorStatusResponse)
async def get_monitor_status(strategy_name: str):
    """Get status of a drift monitor"""
    if strategy_name not in _active_monitors:
        raise HTTPException(
            status_code=404,
            detail=f"No monitor found for {strategy_name}"
        )
    
    monitor = _active_monitors[strategy_name]
    status = monitor.get_status()
    
    return MonitorStatusResponse(
        strategy_name=status['strategy_name'],
        is_paused=status['is_paused'],
        last_check=status['last_check'],
        live_trade_count=status['live_trade_count'],
        total_alerts=status['total_alerts'],
        unacknowledged_alerts=status['unacknowledged_alerts']
    )


@router.get("/monitor/{strategy_name}/alerts")
async def get_alerts(
    strategy_name: str,
    unacknowledged_only: bool = False
):
    """Get all alerts for a strategy"""
    if strategy_name not in _active_monitors:
        raise HTTPException(
            status_code=404,
            detail=f"No monitor found for {strategy_name}"
        )
    
    monitor = _active_monitors[strategy_name]
    
    if unacknowledged_only:
        alerts = monitor.get_unacknowledged_alerts()
    else:
        alerts = monitor.alerts
    
    return {
        "status": "success",
        "strategy_name": strategy_name,
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts)
    }


@router.post("/monitor/{strategy_name}/alerts/{alert_index}/acknowledge")
async def acknowledge_alert(
    strategy_name: str,
    alert_index: int,
    request: AlertAckRequest
):
    """Acknowledge an alert"""
    if strategy_name not in _active_monitors:
        raise HTTPException(
            status_code=404,
            detail=f"No monitor found for {strategy_name}"
        )
    
    monitor = _active_monitors[strategy_name]
    
    success = monitor.acknowledge_alert(alert_index, request.acknowledged_by)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {alert_index} not found"
        )
    
    return {
        "status": "success",
        "message": f"Alert {alert_index} acknowledged by {request.acknowledged_by}"
    }


@router.post("/monitor/{strategy_name}/pause")
async def pause_strategy(strategy_name: str, reason: str = "Manual pause"):
    """Manually pause a strategy"""
    if strategy_name not in _active_monitors:
        raise HTTPException(
            status_code=404,
            detail=f"No monitor found for {strategy_name}"
        )
    
    monitor = _active_monitors[strategy_name]
    monitor._pause_strategy(reason)
    
    return {
        "status": "success",
        "message": f"Strategy {strategy_name} paused",
        "reason": reason
    }


@router.post("/monitor/{strategy_name}/resume")
async def resume_strategy(strategy_name: str, resumed_by: str):
    """Resume a paused strategy"""
    if strategy_name not in _active_monitors:
        raise HTTPException(
            status_code=404,
            detail=f"No monitor found for {strategy_name}"
        )
    
    monitor = _active_monitors[strategy_name]
    monitor.resume_strategy(resumed_by)
    
    return {
        "status": "success",
        "message": f"Strategy {strategy_name} resumed by {resumed_by}"
    }


@router.delete("/monitor/{strategy_name}")
async def delete_monitor(strategy_name: str):
    """Delete a drift monitor"""
    if strategy_name not in _active_monitors:
        raise HTTPException(
            status_code=404,
            detail=f"No monitor found for {strategy_name}"
        )
    
    del _active_monitors[strategy_name]
    
    return {
        "status": "success",
        "message": f"Monitor for {strategy_name} deleted"
    }


@router.get("/monitors")
async def list_monitors():
    """List all active drift monitors"""
    try:
        monitors = []
        
        for name, monitor in _active_monitors.items():
            status = monitor.get_status()
            monitors.append({
                "strategy_name": name,
                "is_paused": status['is_paused'],
                "live_trade_count": status['live_trade_count'],
                "unacknowledged_alerts": status['unacknowledged_alerts']
            })
        
        return {
            "status": "success",
            "monitors": monitors,
            "count": len(monitors)
        }
    except Exception as e:
        logger.error(f"Error listing monitors: {e}")
        return {
            "status": "success",
            "monitors": [],
            "count": 0
        }


# Webhook notification (placeholder for external integrations)
@router.post("/webhook/test")
async def test_webhook(url: str, background_tasks: BackgroundTasks):
    """Test webhook notification"""
    import httpx
    
    async def send_webhook():
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    url,
                    json={
                        "type": "test",
                        "message": "QuantAI drift alert webhook test",
                        "timestamp": datetime.now().isoformat()
                    },
                    timeout=10.0
                )
        except Exception as e:
            logger.error(f"Webhook test failed: {e}")
    
    background_tasks.add_task(send_webhook)
    
    return {"status": "success", "message": f"Webhook test sent to {url}"}
