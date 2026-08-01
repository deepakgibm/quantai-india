from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging
from database import get_read_db
from models import User
from utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Search"])

# Global cache for in-memory stock records
_all_stocks_cache = None

async def ensure_stocks_loaded(db: AsyncSession):
    """
    Ensures active instruments and their Nifty index mapping are preloaded into memory.
    Saves database queries on every keystroke by doing it once at first request.
    """
    global _all_stocks_cache
    if _all_stocks_cache is not None:
        return _all_stocks_cache

    try:
        logger.info("Preloading active stock list from PostgreSQL...")
        
        # 1. Fetch active NSE instruments
        q1 = text("""
            SELECT symbol, company_name, exchange, sector, instrument_key
            FROM instrument_master
            WHERE is_active = TRUE AND exchange = 'NSE' AND series IN ('EQ', 'INDEX')
        """)
        res1 = await db.execute(q1)
        instruments = res1.all()
        
        # 2. Fetch index constituents
        q2 = text("""
            SELECT DISTINCT inst.symbol, im.index_name
            FROM index_master im
            JOIN index_constituent ic ON ic.index_id = im.index_id
            JOIN instrument_master inst ON ic.instrument_id = inst.instrument_id
            WHERE ic.removed_at IS NULL
              AND inst.is_active = TRUE
        """)
        res2 = await db.execute(q2)
        constituents = res2.all()
        
        # Map symbol -> index list
        index_map = {}
        for symbol, index_name in constituents:
            if symbol not in index_map:
                index_map[symbol] = []
            index_map[symbol].append(index_name)
            
        # Prioritize NIFTY index membership
        index_priority = ["NIFTY 50", "NIFTY NEXT 50", "NIFTY 100", "NIFTY 200", "NIFTY 500"]
        
        def get_best_index(indices):
            if not indices:
                return None
            for p in index_priority:
                for ind in indices:
                    if p.lower() in ind.lower():
                        return p
            return indices[0]
            
        stocks = []
        for r in instruments:
            indices = index_map.get(r.symbol, [])
            best_index = get_best_index(indices)
            stocks.append({
                "symbol": r.symbol,
                "company_name": r.company_name or "",
                "name": r.company_name or "",  # alias for frontend
                "exchange": r.exchange,
                "sector": r.sector or "N/A",
                "instrument_key": r.instrument_key,
                "index": best_index
            })
            
        _all_stocks_cache = stocks
        logger.info(f"Successfully preloaded {len(_all_stocks_cache)} stocks into memory.")
        return _all_stocks_cache
    except Exception as e:
        logger.error(f"Failed to preload stocks: {e}")
        return []

@router.get("/stocks")
async def search_stocks(
    q: str = Query(..., min_length=1, max_length=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Search stocks by symbol or company name (case-insensitive) using preloaded in-memory index.
    Fuzzy/prefix matching with instant latency.
    """
    try:
        q_clean = q.strip().lower()
        if not q_clean:
            return {"results": [], "count": 0}
            
        # Ensure cache is filled
        stocks = await ensure_stocks_loaded(db)
        
        # Smart ranking buckets
        exact_matches = []
        symbol_prefix_matches = []
        company_prefix_matches = []
        contains_matches = []
        fuzzy_matches = []
        
        for s in stocks:
            sym_lower = s["symbol"].lower()
            name_lower = s["company_name"].lower()
            
            if sym_lower == q_clean:
                exact_matches.append(s)
            elif sym_lower.startswith(q_clean):
                symbol_prefix_matches.append(s)
            elif name_lower.startswith(q_clean):
                company_prefix_matches.append(s)
            elif q_clean in sym_lower or q_clean in name_lower:
                contains_matches.append(s)
            else:
                # Fuzzy match: query characters appear in order in the symbol
                it = iter(sym_lower)
                if all(c in it for c in q_clean):
                    fuzzy_matches.append(s)
                    
        # Sort buckets alphabetically by symbol
        exact_matches.sort(key=lambda x: x["symbol"])
        symbol_prefix_matches.sort(key=lambda x: x["symbol"])
        company_prefix_matches.sort(key=lambda x: x["symbol"])
        contains_matches.sort(key=lambda x: x["symbol"])
        fuzzy_matches.sort(key=lambda x: x["symbol"])
        
        merged_results = exact_matches + symbol_prefix_matches + company_prefix_matches + contains_matches + fuzzy_matches
        
        # Limit to 50 results
        final_results = merged_results[:50]
        
        return {
            "results": final_results,
            "count": len(final_results)
        }
    except Exception as e:
        logger.error(f"Search API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
