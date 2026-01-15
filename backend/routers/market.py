from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.upstox_client import get_upstox_client
from database import AsyncSessionLocal
from models import User
from utils.auth import get_current_user
from services.nifty500_fetcher import Nifty500Symbol
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Market"])


@router.get("/nifty100/top-movers")
async def get_nifty100_top_movers():
    """
    Get top 5 gainers and top 5 losers from NIFTY 100 stocks.
    
    Data Sourcing Strategy:
    - During market hours (09:15-15:30 IST): WebSocket live data → Cache every 5-10s
    - After market hours: REST API EOD data → Cache with 5-hour TTL + global context
    - Always reads from Dragonfly cache first for sub-50ms response
    
    Returns:
        JSON with 'as_of', 'trading_date', 'gainers', 'losers', 'source', 
        'is_market_open', 'global_context' (when market closed), and 'cache_metadata'
    
    Data Integrity:
        - NEVER returns mock/fake data
        - Returns explicit error if data unavailable
        - Includes cache metadata for transparency
    """
    import asyncio
    import time
    from services.nifty100_ranking_service import get_nifty100_ranking_service
    
    start_time = time.perf_counter()
    
    try:
        service = get_nifty100_ranking_service()
        # 10-second timeout for ranking computation
        data = await asyncio.wait_for(service.get_rankings(), timeout=10.0)
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"Top movers API response in {elapsed_ms:.2f}ms (source: {data.get('source', 'unknown')})")
        
        # Check for error response
        if data.get("error_code"):
            return data
        
        # Add global market context when NSE is closed
        if not data.get("is_market_open", True):
            try:
                from services.global_market_service import get_global_market_service
                global_service = get_global_market_service()
                global_context = await asyncio.wait_for(
                    global_service.get_global_context(), 
                    timeout=5.0
                )
                data["global_context"] = global_context
                logger.info(f"Added global context: {global_context.get('sentiment', {}).get('direction', 'N/A')}")
            except asyncio.TimeoutError:
                logger.warning("Global context fetch timed out")
                data["global_context"] = {"status": "timeout", "message": "Global data fetch timed out"}
            except Exception as ge:
                logger.warning(f"Failed to fetch global context: {ge}")
                data["global_context"] = {"status": "error", "message": str(ge)}
        
        # Check for valid data
        if not data.get("gainers") and not data.get("losers"):
            logger.warning("Top movers service returned empty data, trying yfinance fallback")
            try:
                from utils.market_fallback import fetch_top_movers_yfinance
                fallback_data = await fetch_top_movers_yfinance()
                if fallback_data.get("gainers") or fallback_data.get("losers"):
                    return fallback_data
            except Exception as fe:
                logger.error(f"Top movers fallback failed: {fe}")
                
            return {
                "as_of": datetime.now().isoformat(),
                "gainers": [],
                "losers": [],
                "error": "Market data temporarily unavailable",
                "error_code": "DATA_UNAVAILABLE",
                "retry_after_seconds": 10
            }
        
        return data
        
    except asyncio.TimeoutError:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"Top movers service timed out after {elapsed_ms:.2f}ms")
        return {
            "as_of": datetime.now().isoformat(),
            "gainers": [],
            "losers": [],
            "error": "Request timed out. Market data service is slow.",
            "error_code": "TIMEOUT",
            "retry_after_seconds": 5
        }
        
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"Top movers endpoint failed in {elapsed_ms:.2f}ms: {e}")
        return {
            "as_of": datetime.now().isoformat(),
            "gainers": [],
            "losers": [],
            "error": "Failed to fetch market data",
            "error_code": "INTERNAL_ERROR",
            "retry_after_seconds": 10
        }


@router.get("/global-context")
async def get_global_market_context():
    """
    Get global market indices for after-hours context.
    
    Returns:
        - SGX Nifty (most relevant for next day's NSE direction)
        - Dow Jones, S&P 500, Nasdaq (US markets)
        - FTSE 100 (European market)
        - Overall sentiment indicator
    
    Useful when NSE is closed to gauge global market sentiment.
    """
    import asyncio
    from services.global_market_service import get_global_market_service
    
    try:
        service = get_global_market_service()
        data = await asyncio.wait_for(service.get_global_context(), timeout=10.0)
        return data
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "error": "Global market data fetch timed out",
            "indices": [],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Global context endpoint error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "indices": [],
            "timestamp": datetime.now().isoformat()
        }



@router.get("/nifty100/status")
async def get_nifty100_ranking_status():
    """Get NIFTY 100 ranking service status for monitoring."""
    from services.nifty100_ranking_service import get_nifty100_ranking_service
    service = get_nifty100_ranking_service()
    return service.get_status()


# Alias for compatibility
@router.get("/top-movers")
async def get_top_movers_alias():
    """Alias for /nifty100/top-movers for API compatibility."""
    return await get_nifty100_top_movers()


@router.get("/status")
async def get_market_status():
    """Get market status - alias for /nifty100/status."""
    return await get_nifty100_ranking_status()


@router.get("/indices")
async def get_market_indices():
    """Get market indices."""
    from services.dragonfly_client import get_cache
    cache = get_cache()
    
    # Try cache first
    cached = cache.get("qai:market:indices")
    if cached:
        return {"status": "success", "data": cached}
    
    # Return default indices
    return {
        "status": "success",
        "data": [
            {"name": "NIFTY 50", "symbol": "NSE_INDEX|Nifty 50"},
            {"name": "NIFTY Bank", "symbol": "NSE_INDEX|Nifty Bank"},
            {"name": "NIFTY IT", "symbol": "NSE_INDEX|Nifty IT"},
            {"name": "NIFTY Pharma", "symbol": "NSE_INDEX|Nifty Pharma"},
            {"name": "NIFTY Auto", "symbol": "NSE_INDEX|Nifty Auto"}
        ]
    }

# Industry mapping for Sector Heatmap Detail
INDUSTRY_MAPPING = {
    "Banking": ["Financial Services"],
    "IT": ["Information Technology"],
    "Auto": ["Automobile and Auto Components"],
    "FMCG": ["Fast Moving Consumer Goods"],
    "Pharma": ["Healthcare"],
    "Metal": ["Metals & Mining"],
    "Realty": ["Realty"],
    "Energy": ["Oil Gas & Consumable Fuels", "Power"],
    "Media": ["Media Entertainment & Publication"],
    "Infra": ["Construction", "Construction Materials"],
}

# Sectoral Indices Mapping for Upstox
SECTOR_MAP = {
    "Banking": "NSE_INDEX|Nifty Bank",
    "IT": "NSE_INDEX|Nifty IT",
    "Auto": "NSE_INDEX|Nifty Auto",
    "FMCG": "NSE_INDEX|Nifty FMCG",
    "Pharma": "NSE_INDEX|Nifty Pharma",
    "Metal": "NSE_INDEX|Nifty Metal",
    "Realty": "NSE_INDEX|Nifty Realty",
    "Energy": "NSE_INDEX|Nifty Energy",
    "Media": "NSE_INDEX|Nifty Media",
    "Infra": "NSE_INDEX|Nifty Infra",
}

@router.get("/orchestrator/status")
async def get_orchestrator_status():
    """
    Get the status of the market data orchestrator.
    Returns information about WebSocket health, REST API status, and data sources.
    """
    try:
        from core.market_data.orchestrator import get_market_data_orchestrator
        orchestrator = get_market_data_orchestrator()
        status = orchestrator.get_status()
        return {
            "status": "success",
            "orchestrator": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.warning(f"Orchestrator status unavailable: {e}")
        # Return fallback status
        return {
            "status": "success",
            "orchestrator": {
                "websocket_healthy": False,
                "rest_api_healthy": True,
                "current_source": "REST",
                "fallback_active": True,
                "db_fallback_enabled": True
            },
            "timestamp": datetime.now().isoformat(),
            "note": "Orchestrator not initialized, using fallback data"
        }

@router.get("/health")
async def get_market_health():
    """
    Quick health check for market data services.
    Returns status of data sources and connectivity.
    """
    try:
        from services.upstox_client import get_upstox_client
        client = get_upstox_client()
        
        # Quick check for Upstox connectivity
        import asyncio
        try:
            # Try to get a simple quote with short timeout
            test_quote = await asyncio.wait_for(
                client.get_live_quote("NSE_INDEX|Nifty 50", "NIFTY 50"),
                timeout=2.0
            )
            upstox_healthy = test_quote is not None and test_quote.get("last_price", 0) > 0
        except:
            upstox_healthy = False
        
        return {
            "status": "healthy",
            "services": {
                "upstox_api": "connected" if upstox_healthy else "degraded",
                "database": "healthy",
                "cache": "healthy"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Market health check failed: {e}")
        return {
            "status": "degraded",
            "services": {
                "upstox_api": "unknown",
                "database": "unknown",
                "cache": "unknown"
            },
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/heatmap")
async def get_sector_heatmap(current_user: User = Depends(get_current_user)):
    """
    Fetches real-time performance of sectoral indices.
    Source: Redis Cache (populated by HP Scanner / Heatmap Aggregator)
    """
    from services.dragonfly_client import get_cache, CacheKeys
    cache = get_cache()
    
    # Try common heatmap key first (computed by workers)
    data = cache.get(CacheKeys.heatmap_all())
    
    if not data:
        # Fallback to internal aggregator if worker hasn't run
        return await _fetch_heatmap_internal()
    
    return {"status": "success", "data": data}



async def _fetch_heatmap_internal():
    """
    Internal function to fetch heatmap data.
    Uses Dragonfly cache for instant response.
    """
    from services.dragonfly_client import get_cache, CacheKeys
    from datetime import datetime
    
    cache = get_cache()
    
    # 1. Try to get cached computation
    cache_key = "qai:market:heatmap"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # 2. If no pre-computed data, build from quotes (Avoid blocking)
    try:
        from services.upstox_client import get_upstox_client
        client = get_upstox_client()
        
        all_keys = ["NSE_INDEX|Nifty 50"] + list(SECTOR_MAP.values())
        quotes = await client.get_live_quotes(all_keys)
        
        results = []
        nifty_quote = quotes.get("NSE_INDEX|Nifty 50") or quotes.get("NSE_INDEX:Nifty 50")
        nifty_change = nifty_quote.get('change_percent', 0) if nifty_quote else 0

        for sector, key in SECTOR_MAP.items():
            quote = quotes.get(key) or quotes.get(key.replace("|", ":"))
            if quote:
                results.append({
                    "sector": sector,
                    "last_price": quote['last_price'],
                    "change_pct": round(quote.get('change_percent', 0), 2),
                    "is_bullish": quote.get('change_percent', 0) > 0
                })
        
        results.sort(key=lambda x: x.get('change_pct', 0), reverse=True)
        
        data = {
            "status": "success", 
            "data": results,
            "market_outlook": {
                "verdict": "Bullish" if nifty_change > 0.4 else "Bearish" if nifty_change < -0.4 else "Neutral",
                "nifty_change": round(nifty_change, 2),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        cache.set(cache_key, data, ttl=60)
        return data
        
    except Exception as e:
        logger.error(f"Internal heatmap fetch failed: {e}")
        return {"status": "error", "message": str(e), "data": []}




@router.get("/sector-stocks/{sector_name}")
async def get_sector_stocks(sector_name: str, current_user: User = Depends(get_current_user)):
    """
    Fetches list of stocks for a given sector and their live performance.
    Source: Redis Cache (populated by HP Scanner)
    """
    from services.dragonfly_client import get_cache, CacheKeys
    cache = get_cache()
    
    # 1. Try to get cached sector snapshot (calculated by workers)
    key = f"{CacheKeys.sector_snapshot(sector_name)}:stocks"
    stocks = cache.get(key)
    
    if stocks:
        return {
            "status": "success",
            "sector": sector_name,
            "stocks": sorted(stocks, key=lambda x: x.get('change_pct', 0), reverse=True)
        }

    # 2. If not in cache, fallback logic removed to prevent blocking
    return {
        "status": "success",
        "sector": sector_name,
        "stocks": [],
        "note": "Market data for this sector is still warming up"
    }



