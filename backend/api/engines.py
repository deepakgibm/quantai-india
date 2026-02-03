
from fastapi import APIRouter, Depends
from models import User
from utils.auth import get_current_user
import time
import psutil

router = APIRouter(tags=["System Engines"])

@router.get("/performance")
async def get_engine_performance(current_user: User = Depends(get_current_user)):
    """System performance metrics for frontend dashboard."""
    return {
        "status": "success",
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "scanner_lag_ms": 120, # Mock or measure real lag
        "timestamp": time.time()
    }
