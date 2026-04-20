"""
ML Training API Router

Exposes endpoints for:
- Checking training status (Celery task state + DragonflyDB progress)
- Starting a training job (dispatches Celery task)
- Stopping a running training job (revokes Celery task)
"""

import os
import json
import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from utils.rate_limit import rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ML Training"])

# IST timezone (UTC+5:30)
_IST = timezone(timedelta(hours=5, minutes=30))

# Status file path (backward compatibility with old UI polling)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
_STATUS_FILE = os.path.join(_PROJECT_ROOT, "data", "ml_status.json")

# Track active Celery task ID (replaces _active_pid)
# This is now managed via DragonflyDB for persistence across restarts
_CACHE_KEY_ACTIVE_TASK = "qai:ml:training:active_task_id"

def _get_active_task_id() -> Optional[str]:
    """Get the active task ID from Dragonfly cache."""
    try:
        from services.dragonfly_client import get_cache
        cache = get_cache()
        if cache.is_available():
            val = cache.get(_CACHE_KEY_ACTIVE_TASK)
            return val.decode("utf-8") if isinstance(val, bytes) else val
    except Exception:
        pass
    return None

def _set_active_task_id(task_id: Optional[str]):
    """Set or clear the active task ID in Dragonfly cache."""
    try:
        from services.dragonfly_client import get_cache
        cache = get_cache()
        if cache.is_available():
            if task_id:
                cache.set(_CACHE_KEY_ACTIVE_TASK, task_id, ttl=86400) # 24h safety TTL
            else:
                cache.delete(_CACHE_KEY_ACTIVE_TASK)
    except Exception:
        pass


def _is_market_open() -> bool:
    """Check if Indian stock market is currently open (09:15–15:30 IST, Mon–Fri)."""
    now = datetime.now(_IST)
    if now.weekday() >= 5:
        return False
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return start <= now <= end


def _safe_float(value, default: float = 0.0) -> float:
    """Sanitize float values — replace inf/nan with a safe default."""
    if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _read_status() -> dict:
    """Read the training status file (backward compat)."""
    try:
        if os.path.exists(_STATUS_FILE):
            with open(_STATUS_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, ValueError, IOError) as e:
        logger.warning(f"Failed to read status file: {e}")
    return {}


def _get_market_status() -> str:
    """Return human-readable market status."""
    now = datetime.now(_IST)
    if now.weekday() >= 5:
        return "WEEKEND"
    if _is_market_open():
        return "OPEN"
    hour = now.hour
    if hour < 9 or (hour == 9 and now.minute < 15):
        return "PRE_MARKET"
    return "CLOSED"


def _get_celery_task_state(task_id: str) -> dict:
    """Query Celery for task state and metadata."""
    try:
        from celery.result import AsyncResult
        from celery_app import celery_app
        
        result = AsyncResult(task_id, app=celery_app)
        state = result.state  # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE, REVOKED
        meta = result.info if isinstance(result.info, dict) else {}
        
        return {
            "celery_state": state,
            "meta": meta,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
        }
    except Exception as e:
        logger.warning(f"Failed to query Celery state: {e}")
        return {"celery_state": "UNKNOWN", "meta": {}}


@router.get("/train/status", dependencies=[Depends(rate_limit(120, 60, "training_status"))])
async def get_training_status():
    """
    Get current ML training status.
    
    Reads from Celery task state (primary) and DragonflyDB progress cache.
    Falls back to status file for backward compatibility.
    """
    active_task_id = _get_active_task_id()
    
    is_running = False
    metrics = {}
    
    # Primary: check Celery task state
    if active_task_id:
        celery_state = _get_celery_task_state(active_task_id)
        state = celery_state.get("celery_state", "UNKNOWN")
        meta = celery_state.get("meta", {})
        
        if state in ("STARTED", "PROGRESS"):
            is_running = True
            metrics = {
                "stage": meta.get("stage", "running"),
                "epoch": meta.get("epoch", 0),
                "total_epochs": meta.get("total_epochs", 0),
                "train_loss": _safe_float(meta.get("train_loss", 0.0)),
                "val_loss": _safe_float(meta.get("val_loss", 0.0)),
                "best_loss": _safe_float(meta.get("best_loss", 0.0)),
                "last_update": meta.get("last_update"),
            }
        elif state == "SUCCESS":
            is_running = False
            result_data = meta if meta else {}
            metrics = {
                "stage": "completed",
                "best_loss": _safe_float(result_data.get("best_loss", 0.0)),
                "last_update": datetime.now().isoformat(),
            }
            _set_active_task_id(None)
            active_task_id = None
        elif state in ("FAILURE", "REVOKED"):
            is_running = False
            metrics = {
                "stage": "error" if state == "FAILURE" else "stopped",
                "reason": str(meta) if state == "FAILURE" else "Revoked by user",
                "last_update": datetime.now().isoformat(),
            }
            _set_active_task_id(None)
            active_task_id = None
        elif state == "PENDING":
            # PENDING is Celery's default for unknown task IDs — it could
            # be genuinely queued OR a stale/revoked task that no longer exists.
            # We must verify by checking if any worker actually knows about it.
            pass  # Fall through to the orphan-adoption / discovery block below
    
    if not metrics:
        # Discover the REAL active training task from the Celery workers.
        # This handles: (a) stale cached task ID, (b) backend restart,
        # (c) task ID mismatch after revoke/restart.
        try:
            from celery_app import celery_app
            active = celery_app.control.inspect().active()
            if active:
                for node, tasks in active.items():
                    for task in tasks:
                        if task.get("name") == "tasks.ml_tasks.train_model":
                            discovered_id = task.get("id")
                            if discovered_id != active_task_id:
                                logger.info(f"Discovered active training task {discovered_id} "
                                            f"(was tracking: {active_task_id})")
                            active_task_id = discovered_id
                            _set_active_task_id(active_task_id)
                            # Get real state for this task
                            celery_state = _get_celery_task_state(active_task_id)
                            state = celery_state.get("celery_state", "UNKNOWN")
                            meta = celery_state.get("meta", {})
                            is_running = True
                            metrics = {
                                "stage": meta.get("stage", "running"),
                                "epoch": meta.get("epoch", 0),
                                "total_epochs": meta.get("total_epochs", 0),
                                "train_loss": _safe_float(meta.get("train_loss", 0.0)),
                                "val_loss": _safe_float(meta.get("val_loss", 0.0)),
                                "best_loss": _safe_float(meta.get("best_loss", 0.0)),
                                "last_update": meta.get("last_update"),
                            }
                            break
            # If no training task found in any worker, the cached ID is stale
            if not metrics and active_task_id:
                logger.info(f"Clearing stale task ID: {active_task_id}")
                _set_active_task_id(None)
                active_task_id = None
        except Exception as e:
            logger.warning(f"Failed to inspect active tasks: {e}")
    
    # Fallback: read status file if no Celery data
    if not metrics:
        status_data = _read_status()
        metrics = {
            "stage": status_data.get("stage", "idle"),
            "epoch": status_data.get("epoch", 0),
            "total_epochs": status_data.get("total_epochs", 0),
            "train_loss": _safe_float(status_data.get("train_loss", 0.0)),
            "val_loss": _safe_float(status_data.get("val_loss", 0.0)),
            "best_loss": _safe_float(status_data.get("best_loss", 0.0)),
            "last_update": status_data.get("last_update"),
            "reason": status_data.get("reason"),
        }
    
    return {
        "is_running": is_running,
        "task_id": active_task_id,
        "pid": active_task_id[:8] if active_task_id else None,
        "metrics": metrics,
        "market_status": _get_market_status(),
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/train/start", dependencies=[Depends(rate_limit(10, 60, "training_control"))])
async def start_training(
    epochs: int = Query(default=50, ge=1, le=500, description="Number of training epochs"),
    batch_size: int = Query(default=32, ge=8, le=256, description="Batch size for SGD"),
):
    """
    Start an ML training session via Celery task queue.
    
    Dispatches training to a Celery worker instead of launching a subprocess.
    Only one training session can run at a time.
    """
    active_task_id = _get_active_task_id()
    
    # Guard: don't start if already running
    if active_task_id:
        celery_state = _get_celery_task_state(active_task_id)
        if celery_state.get("celery_state") in ("STARTED", "PROGRESS", "PENDING"):
            return {
                "status": "error",
                "message": f"Training already running (task: {active_task_id}). Stop it first.",
                "task_id": active_task_id,
            }
        else:
            _set_active_task_id(None)  # Clean up stale task
    
    # Market hours warning
    market_warning = None
    if _is_market_open():
        market_warning = "Warning: Market is currently open. Training may impact inference latency."
    
    # Write initial status (backward compat)
    os.makedirs(os.path.dirname(_STATUS_FILE), exist_ok=True)
    try:
        with open(_STATUS_FILE, "w") as f:
            json.dump({
                "stage": "queued",
                "epoch": 0,
                "total_epochs": epochs,
                "last_update": datetime.now().isoformat(),
            }, f)
    except IOError as e:
        logger.error(f"Failed to write initial status: {e}")
    
    # Dispatch Celery task
    try:
        from tasks.ml_tasks import train_model
        
        result = train_model.delay(epochs=epochs, batch_size=batch_size)
        _set_active_task_id(result.id)
        
        logger.info(f"Training dispatched as Celery task: {result.id}")
        
        return {
            "status": "success",
            "message": "Training job queued successfully",
            "task_id": result.id,
            "config": {
                "epochs": epochs,
                "batch_size": batch_size,
            },
            "market_warning": market_warning,
        }
        
    except Exception as e:
        logger.error(f"Failed to dispatch training task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")


@router.post("/train/stop", dependencies=[Depends(rate_limit(10, 60, "training_control"))])
async def stop_training():
    """
    Stop the currently running training session.
    
    Revokes the Celery task (sends SIGTERM to worker process).
    """
    active_task_id = _get_active_task_id()
    
    if active_task_id is None:
        return {
            "status": "info",
            "message": "No training session is currently running.",
        }
    
    try:
        from celery_app import celery_app
        
        task_id = active_task_id
        
        # Revoke the task — terminate=True sends SIGTERM to the worker process
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
        
        _set_active_task_id(None)
        
        # Update status file
        try:
            with open(_STATUS_FILE, "w") as f:
                json.dump({
                    "stage": "stopped",
                    "reason": "Manual Stop (API)",
                    "last_update": datetime.now().isoformat(),
                }, f)
        except IOError:
            pass
        
        logger.info(f"Training task revoked: {task_id}")
        
        return {
            "status": "success",
            "message": f"Training stopped (task: {task_id})",
        }
        
    except Exception as e:
        logger.error(f"Failed to stop training: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop training: {str(e)}")
