from fastapi import APIRouter, HTTPException
import json
from pathlib import Path

router = APIRouter()

TRACKER_PATH = Path(__file__).resolve().parents[3] / "etl" / "load_tracker.json"

@router.get("/etl/status", tags=["ETL"])
async def get_etl_status():
    """Return the current ETL load tracker JSON.
    If the tracker file does not exist, returns a 404.
    """
    if not TRACKER_PATH.exists():
        raise HTTPException(status_code=404, detail="ETL tracker not found")
    try:
        with open(TRACKER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
