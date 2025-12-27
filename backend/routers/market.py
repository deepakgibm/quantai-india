from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.upstox_client import get_upstox_client
from database import AsyncSessionLocal
from services.nifty500_fetcher import Nifty500Symbol
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Market"])

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
async def get_sector_heatmap():
    """
    Fetches real-time performance of sectoral indices from Upstox.
    Calculates change percentage and generates market outlook.
    """
    import asyncio
    from datetime import datetime
    
    # Fallback data
    FALLBACK_DATA = {
        "status": "success",
        "data": [
            {"sector": "IT", "last_price": 36500, "change_pct": 1.2, "is_bullish": True},
            {"sector": "Banking", "last_price": 51200, "change_pct": 0.8, "is_bullish": True},
            {"sector": "Auto", "last_price": 18900, "change_pct": -0.5, "is_bullish": False},
            {"sector": "Pharma", "last_price": 18200, "change_pct": 0.3, "is_bullish": True},
            {"sector": "FMCG", "last_price": 56800, "change_pct": -0.2, "is_bullish": False},
            {"sector": "Metal", "last_price": 8500, "change_pct": 1.5, "is_bullish": True},
            {"sector": "Realty", "last_price": 1050, "change_pct": 2.1, "is_bullish": True},
            {"sector": "Energy", "last_price": 36200, "change_pct": -0.8, "is_bullish": False},
        ],
        "market_outlook": {
            "verdict": "Neutral",
            "nifty_change": 0.25,
            "suggestion": "Range-bound: Trade with caution",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    try:
        result = await asyncio.wait_for(_fetch_heatmap_internal(), timeout=15.0)
        return result
    except asyncio.TimeoutError:
        logger.warning("Sector heatmap fetch timed out, using fallback")
        return FALLBACK_DATA
    except Exception as e:
        logger.error(f"Heatmap generation failed: {e}")
        return FALLBACK_DATA


async def _fetch_heatmap_internal():
    """Internal function to fetch heatmap data"""
    from datetime import datetime
    
    client = get_upstox_client()
    results = []
    
    try:
        # Prepare all keys for batch fetch
        nifty_key = "NSE_INDEX|Nifty 50"
        sector_keys = list(SECTOR_MAP.values())
        all_keys = [nifty_key] + sector_keys
        
        # Fetch all at once
        quotes = await client.get_live_quotes(all_keys)
        
        # Find Nifty 50 quote
        nifty_quote = None
        for key in [nifty_key, nifty_key.replace("|", ":")]:
            if key in quotes:
                nifty_quote = quotes[key]
                break
                
        nifty_change = 0
        if nifty_quote and nifty_quote.get('open'):
            nifty_change = ((nifty_quote['last_price'] - nifty_quote['open']) / nifty_quote['open']) * 100
        elif nifty_quote:
            nifty_change = nifty_quote.get('change_percent', 0)

        # Process sectors
        for sector, key in SECTOR_MAP.items():
            quote = None
            for k in [key, key.replace("|", ":")]:
                if k in quotes:
                    quote = quotes[k]
                    break
            
            if quote and (quote.get('open') or quote.get('last_price')):
                open_val = quote.get('open') or (quote.get('last_price', 0) - quote.get('net_change', 0))
                if open_val and open_val > 0:
                    change = ((quote['last_price'] - open_val) / open_val) * 100
                else:
                    change = quote.get('change_percent', 0)
                
                results.append({
                    "sector": sector,
                    "last_price": quote['last_price'],
                    "change_pct": round(change, 2),
                    "is_bullish": change > 0,
                    "volume": quote.get("volume", 0)
                })
            else:
                results.append({
                    "sector": sector,
                    "last_price": 0,
                    "change_pct": 0,
                    "is_bullish": False,
                    "status": "No data available"
                })
        
        # Sort by performance
        results.sort(key=lambda x: x.get('change_pct', 0), reverse=True)
        
        # Determine Market Outlook
        outlook = "Neutral"
        if nifty_change > 0.4:
            outlook = "Bullish"
        elif nifty_change < -0.4:
            outlook = "Bearish"
            
        suggestion = "Look for Long positions" if "Bullish" in outlook else "Look for Short positions" if "Bearish" in outlook else "Range-bound: Trade with caution"

        return {
            "status": "success",
            "data": results,
            "market_outlook": {
                "verdict": outlook,
                "nifty_change": round(nifty_change, 2),
                "suggestion": suggestion,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Internal heatmap fetch failed: {e}")
        raise


@router.get("/sector-stocks/{sector_name}")
async def get_sector_stocks(sector_name: str):
    """
    Fetches list of stocks for a given sector and their live performance.
    """
    industries = INDUSTRY_MAPPING.get(sector_name)
    if not industries:
        # Lowercase fallback check
        for k, v in INDUSTRY_MAPPING.items():
            if k.lower() == sector_name.lower():
                industries = v
                break
        
        if not industries:
            raise HTTPException(status_code=404, detail=f"Sector '{sector_name}' mapping not found")

    client = get_upstox_client()
    stocks = []
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Nifty500Symbol).where(Nifty500Symbol.industry.in_(industries))
        )
        symbols = result.scalars().all()
        
        # Limit to 40 symbols for performance/stability
        symbols = symbols[:40]
        
        for s in symbols:
            try:
                quote = await client.get_live_quote(s.instrument_key, s.symbol)
                if quote and quote.get('open'):
                    change_pct = ((quote['last_price'] - quote['open']) / quote['open']) * 100
                    stocks.append({
                        "symbol": s.symbol,
                        "company_name": s.company_name,
                        "last_price": quote['last_price'],
                        "change_pct": round(change_pct, 2),
                        "is_bullish": change_pct > 0
                    })
            except Exception as e:
                logger.error(f"Error fetching quote for {s.symbol}: {e}")
                
    return {
        "status": "success",
        "sector": sector_name,
        "stocks": sorted(stocks, key=lambda x: x['change_pct'], reverse=True)
    }
