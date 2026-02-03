from fastapi import APIRouter, HTTPException
import subprocess
import os
import signal
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/v1/ml", tags=["ML Training"])
logger = logging.getLogger(__name__)

# Global state to track training process
# In a multi-worker environment (gunicorn), this would need to be in Redis/Database
# For local dev/single process, we use a module-level variable
_training_process: Optional[subprocess.Popen] = None
STATUS_FILE = Path("data/ml_status.json")

@router.post("/train/start")
async def start_training(epochs: int = 50, batch_size: int = 32):
    global _training_process
    
    if _training_process and _training_process.poll() is None:
        return {"status": "error", "message": "Training is already running"}
        
    cmd = [
        "python", 
        "backend/ml/production_training.py", 
        "--epochs", str(epochs), 
        "--batch", str(batch_size)
    ]
    
    try:
        # Create data dir if not exists
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Start the process in the background
        # We use a new process group to allow killing the entire group later if needed
        _training_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        
        return {
            "status": "success", 
            "message": "Training started", 
            "pid": _training_process.pid
        }
    except Exception as e:
        logger.error(f"Failed to start training: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train/stop")
async def stop_training():
    global _training_process
    
    if not _training_process or _training_process.poll() is not None:
        return {"status": "error", "message": "No active training process found"}
        
    try:
        pid = _training_process.pid
        # Graceful termination
        if os.name == 'nt':
            # On Windows, we send CTRL_BREAK_EVENT
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        else:
            _training_process.terminate()
            
        # Wait a bit
        try:
            _training_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _training_process.kill()
            
        _training_process = None
        return {"status": "success", "message": f"Training process {pid} stopped"}
    except Exception as e:
        logger.error(f"Failed to stop training: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/train/status")
async def get_training_status():
    is_running = False
    pid = None
    
    if _training_process and _training_process.poll() is None:
        is_running = True
        pid = _training_process.pid
        
    status_data = {}
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r") as f:
                status_data = json.load(f)
        except:
            pass
            
    return {
        "is_running": is_running,
        "pid": pid,
        "metrics": status_data,
        "market_status": "CLOSED" if not is_market_hours() else "OPEN",
        "timestamp": datetime.now().isoformat()
    }

def is_market_hours():
    """Simple check for NSE market hours (09:15 - 15:30 IST)."""
    # Note: Backend likely runs in UTC or IST depending on env. 
    # For now, we assume this is called with local server time.
    now = datetime.now()
    if now.weekday() >= 5: # Weekend
        return False
    
    # IST conversion logic if needed, but for simplicity:
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    return start <= now <= end
