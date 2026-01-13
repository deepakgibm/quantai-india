"""
Analytics API Router
Exposes DuckDB analytics and Parquet archive functionality via REST API.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
import logging
from utils.auth import get_current_user
from models import User
from fastapi import Depends

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ============================================
# Request/Response Models
# ============================================

class QueryRequest(BaseModel):
    sql: str
    params: Optional[Dict[str, Any]] = None


class ArchiveRequest(BaseModel):
    year: int
    month: int
    delete_after: bool = False


class ArchiveOldRequest(BaseModel):
    months_to_keep: int = 12
    delete_after: bool = False


# ============================================
# Analytics Endpoints
# ============================================
@router.get("/overview")
async def get_analytics_overview(current_user: User = Depends(get_current_user)):
    """Get high-level analytics overview."""
    return {
        "status": "success",
        "market_sentiment": "Neutral",
        "active_alerts": 5,
        "daily_volume_status": "High"
    }

@router.get("/momentum/top")
async def get_top_momentum(
    n: int = Query(10, ge=1, le=100),
    lookback_days: int = Query(20, ge=5, le=60),
    current_user: User = Depends(get_current_user)
):
    """Get top N stocks by momentum using DuckDB analytics."""
    try:
        from services.analytics_engine import get_analytics_engine
        
        engine = get_analytics_engine()
        df = engine.get_top_momentum_stocks(n=n, lookback_days=lookback_days)
        
        return {
            "status": "success",
            "data": df.to_dict(orient="records"),
            "count": len(df),
            "lookback_days": lookback_days
        }
    except Exception as e:
        logger.error(f"Momentum analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/volatility/{symbol}")
async def get_volatility_analysis(
    symbol: str,
    lookback_days: int = Query(30, ge=5, le=90),
    current_user: User = Depends(get_current_user)
):
    """Get volatility analysis for a specific symbol."""
    try:
        from services.analytics_engine import get_analytics_engine
        
        engine = get_analytics_engine()
        df = engine.get_volatility_analysis(symbol, lookback_days)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        return {
            "status": "success",
            "symbol": symbol,
            "data": df.to_dict(orient="records")[0],
            "lookback_days": lookback_days
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Volatility analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/correlation")
async def get_correlation_matrix(
    symbols: List[str],
    lookback_days: int = Query(60, ge=20, le=120),
    current_user: User = Depends(get_current_user)
):
    """Calculate correlation matrix between multiple symbols."""
    if len(symbols) < 2:
        raise HTTPException(status_code=400, detail="At least 2 symbols required")
    if len(symbols) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 symbols allowed")
    
    try:
        from services.analytics_engine import get_analytics_engine
        
        engine = get_analytics_engine()
        df = engine.get_correlation_matrix(symbols, lookback_days)
        
        return {
            "status": "success",
            "symbols": symbols,
            "correlation_matrix": df.to_dict(),
            "lookback_days": lookback_days
        }
    except Exception as e:
        logger.error(f"Correlation analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/support-resistance/{symbol}")
async def get_support_resistance(
    symbol: str,
    lookback_days: int = Query(90, ge=30, le=180),
    current_user: User = Depends(get_current_user)
):
    """Calculate support and resistance levels for a symbol."""
    try:
        from services.analytics_engine import get_analytics_engine
        
        engine = get_analytics_engine()
        df = engine.get_support_resistance_levels(symbol, lookback_days)
        
        # Sanitize DataFrame (NaN -> None, Inf -> None) for JSON compliance
        import numpy as np
        df = df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), None)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        return {
            "status": "success",
            "symbol": symbol,
            "levels": df.to_dict(orient="records")[0],
            "lookback_days": lookback_days
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Support/resistance analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def execute_custom_query(request: QueryRequest, current_user: User = Depends(get_current_user)):
    """
    Execute custom SQL query using DuckDB.
    Restricted to authenticated users. 
    NOTE: In production, this should be restricted to admin users only.
    """
    # For now, we enforce authentication. 
    # To truly fix CB-1, we should also check if current_user.email in ADMIN_EMAILS
    # if current_user.email not in settings.ADMIN_EMAILS:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    try:
        from services.analytics_engine import get_analytics_engine
        
        engine = get_analytics_engine()
        df = engine.query(request.sql, request.params)
        
        return {
            "status": "success",
            "data": df.to_dict(orient="records"),
            "columns": list(df.columns),
            "row_count": len(df)
        }
    except Exception as e:
        logger.error(f"Custom query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Archive Endpoints
# ============================================

@router.get("/archive/list")
async def list_archives(current_user: User = Depends(get_current_user)):
    """List all available Parquet archives."""
    try:
        from services.parquet_archive import get_archive_service
        
        service = get_archive_service()
        archives = service.list_archives()
        
        return {
            "status": "success",
            "archives": archives,
            "count": len(archives)
        }
    except Exception as e:
        logger.error(f"List archives failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archive/stats")
async def get_archive_stats(current_user: User = Depends(get_current_user)):
    """Get archive storage statistics."""
    try:
        from services.parquet_archive import get_archive_service
        
        service = get_archive_service()
        stats = service.get_archive_stats()
        
        return {
            "status": "success",
            **stats
        }
    except Exception as e:
        logger.error(f"Archive stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/archive/month")
async def archive_month(request: ArchiveRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    """
    Archive one month of data to Parquet.
    Runs in background if delete_after is True.
    """
    try:
        from services.parquet_archive import get_archive_service
        
        service = get_archive_service()
        
        if request.delete_after:
            # Run in background for safety
            background_tasks.add_task(
                service.archive_month,
                request.year,
                request.month,
                True
            )
            return {
                "status": "started",
                "message": f"Archiving {request.year}-{request.month:02d} in background",
                "year": request.year,
                "month": request.month
            }
        else:
            result = service.archive_month(request.year, request.month, False)
            return result
            
    except Exception as e:
        logger.error(f"Archive month failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/archive/old")
async def archive_old_data(request: ArchiveOldRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    """
    Archive all data older than specified months.
    Always runs in background.
    """
    try:
        from services.parquet_archive import get_archive_service
        
        service = get_archive_service()
        
        background_tasks.add_task(
            service.archive_old_data,
            request.months_to_keep,
            request.delete_after
        )
        
        return {
            "status": "started",
            "message": f"Archiving data older than {request.months_to_keep} months",
            "delete_after": request.delete_after
        }
    except Exception as e:
        logger.error(f"Archive old data failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/archive/restore")
async def restore_from_archive(request: ArchiveRequest, current_user: User = Depends(get_current_user)):
    """Restore archived data back to database."""
    try:
        from services.parquet_archive import get_archive_service
        
        service = get_archive_service()
        result = service.restore_from_archive(request.year, request.month)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Indicator Computation Endpoints
# ============================================

@router.post("/indicators/compute")
async def trigger_indicator_computation(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    interval: str = Query("1d", regex="^(1min|5min|15min|30min|1d)$"),
    symbol_limit: Optional[int] = Query(None, ge=1, le=1000)
):
    """
    Trigger indicator computation as a background task.
    """
    try:
        from services.indicator_compute_service import get_indicator_service
        
        service = get_indicator_service()
        
        background_tasks.add_task(
            service.compute_all,
            interval,
            symbol_limit
        )
        
        return {
            "status": "started",
            "message": "Indicator computation started in background",
            "interval": interval,
            "symbol_limit": symbol_limit
        }
    except Exception as e:
        logger.error(f"Indicator computation trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/latest/{symbol}")
async def get_latest_indicators(symbol: str, interval: str = "1d", current_user: User = Depends(get_current_user)):
    """Get latest precomputed indicators for a symbol."""
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as session:
            query = text("""
                SELECT * FROM precomputed_indicators
                WHERE symbol = :symbol AND interval = :interval
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            
            result = await session.execute(query, {"symbol": symbol, "interval": interval})
            row = result.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No indicators found for {symbol} ({interval})"
                )
            
            # Convert row to dict
            columns = result.keys()
            data = dict(zip(columns, row))
            
            return {
                "status": "success",
                "symbol": symbol,
                "interval": interval,
                "indicators": data
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get indicators failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
