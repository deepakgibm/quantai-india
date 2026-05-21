from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any
import logging
from database import get_read_db
from models import User
from utils.auth import get_current_user
from services.cache import get_cache_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Search"])

@router.get("/stocks")
async def search_stocks(
    q: str = Query(..., min_length=1, max_length=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Search stocks by symbol or company name (case-insensitive) in instrument_master.
    """
    try:
        # Check cache first
        cache_key = f"search:stocks:{q.lower().strip()}"
        cache = get_cache_manager()
        if cache.is_available():
            try:
                cached = cache.get(cache_key)
                if cached:
                    return cached
            except Exception as ce:
                logger.warning(f"Cache read error in search: {ce}")
        
        # Query DB
        # Match symbol OR company_name
        # Show symbol, company_name, exchange, sector, instrument_key
        search_query = f"%{q.strip().lower()}%"
        sql = text("""
            SELECT symbol, company_name, exchange, sector, instrument_key
            FROM instrument_master
            WHERE is_active = TRUE
              AND (LOWER(symbol) LIKE :q OR LOWER(company_name) LIKE :q)
            ORDER BY symbol ASC
            LIMIT 20
        """)
        
        result = await db.execute(sql, {"q": search_query})
        rows = result.all()
        
        results = []
        for r in rows:
            results.append({
                "symbol": r.symbol,
                "company_name": r.company_name,
                "exchange": r.exchange,
                "sector": r.sector,
                "instrument_key": r.instrument_key
            })
            
        response_data = {
            "results": results,
            "count": len(results)
        }
        
        # Set cache
        if cache.is_available():
            try:
                cache.set(cache_key, response_data, ttl=60)
            except Exception as ce:
                logger.warning(f"Cache write error in search: {ce}")
                
        return response_data
    except Exception as e:
        logger.error(f"Search API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
