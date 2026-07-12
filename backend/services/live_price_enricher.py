import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

from services.price_manager import get_price_service, get_market_status_service
from utils.trade_logic import calculate_atr_levels

logger = logging.getLogger(__name__)

async def get_database_prices(symbols: List[str]) -> Dict[str, float]:
    """Fallback to database for prices. Delegated to PriceService."""
    if not symbols:
        return {}
    service = get_price_service()
    prices_data = await service.get_prices_bulk(symbols)
    return {s: data.get("ltp", 0.0) for s, data in prices_data.items() if data}

async def get_database_movers_data(symbols: List[str]) -> Dict[str, Dict[str, float]]:
    """Used for calculating change percentage. Delegated to PriceService."""
    if not symbols:
        return {}
    service = get_price_service()
    prices_data = await service.get_prices_bulk(symbols)
    movers_data = {}
    for s, data in prices_data.items():
        if data:
            movers_data[s] = {
                "ltp": data.get("ltp", 0.0),
                "prev_close": data.get("previous_close", 0.0)
            }
    return movers_data

async def get_yfinance_price(symbol: str) -> Optional[float]:
    """Yahoo Finance lookup. Delegated to PriceService."""
    service = get_price_service()
    price_data = await service.get_price(symbol)
    return price_data.get("ltp") if price_data.get("ltp") > 0 else None

def get_instrument_key(symbol: str) -> Optional[str]:
    """Get the Upstox instrument key for a symbol via PriceService metadata."""
    # We resolve it dynamically using PriceService's build_dto resolver
    from services.instrument_resolver import resolve_instrument_info
    info = resolve_instrument_info(symbol)
    return info.instrument_key if info else None

async def fetch_live_ltp(symbols: List[str], access_token: str = None) -> Dict[str, float]:
    """Fetch live LTP. Delegated to PriceService."""
    if not symbols:
        return {}
    service = get_price_service()
    prices_data = await service.get_prices_bulk(symbols)
    return {s: data.get("ltp", 0.0) for s, data in prices_data.items() if data}

async def fetch_live_full_quotes(symbols: List[str], access_token: str = None) -> Dict[str, Dict[str, Any]]:
    """Fetch live full quotes. Delegated to PriceService."""
    if not symbols:
        return {}
    service = get_price_service()
    prices_data = await service.get_prices_bulk(symbols)
    results = {}
    for s, data in prices_data.items():
        if data:
            results[s] = {
                "ltp": data.get("ltp", 0.0),
                "prev_close": data.get("previous_close", 0.0),
                "volume": data.get("volume", 0),
                "timestamp": data.get("timestamp")
            }
    return results

async def enrich_scanner_results(results: List[Dict], access_token: str = None) -> List[Dict]:
    """Enriches scanner results with standard price data from PriceService."""
    if not results:
        return results
    symbols = [r.get("symbol") for r in results if r.get("symbol")]
    service = get_price_service()
    bulk_prices = await service.get_prices_bulk(symbols)
    
    enriched = []
    for result in results:
        symbol = result.get("symbol", "").upper()
        p_data = bulk_prices.get(symbol, {})
        ltp = p_data.get("ltp")
        source = p_data.get("source", "NONE")
        res = result.copy()
        
        if ltp and ltp > 0:
            res["current_price"] = ltp
            res["price_source"] = source
        elif result.get("ltp"):
            res["current_price"] = round(float(result["ltp"]), 2)
            res["price_source"] = "CACHED"
        else:
            res["current_price"] = None
            res["price_source"] = "NONE"
            enriched.append(res)
            continue
            
        res["ltp"] = res["current_price"]
        trend = res.get("trend") or res.get("signal") or "BULLISH"
        is_bull = "BEARISH" not in str(trend).upper() and "SELL" not in str(trend).upper()
        atr = res.get("atr")
        
        if atr and atr > 0:
            levels = calculate_atr_levels(is_bull, res["current_price"], atr)
            res.update(levels)
        else:
            res["entry_price"] = res["current_price"]
            res["target_price"] = round(res["current_price"] * (1.05 if is_bull else 0.95), 2)
            res["stop_loss"] = round(res["current_price"] * (0.97 if is_bull else 1.03), 2)
            
        res["signal_active"] = True
        enriched.append(res)
    return enriched

async def get_single_live_price(symbol: str, access_token: str = None) -> Optional[float]:
    """Get single live price. Delegated to PriceService."""
    service = get_price_service()
    data = await service.get_price(symbol)
    return data.get("ltp") if data.get("ltp") > 0 else None

async def get_live_ltp(symbol: str, access_token: str = None) -> Dict:
    """Get live LTP. Delegated to PriceService."""
    service = get_price_service()
    data = await service.get_price(symbol)
    source_map = {"UPSTOX_WS": "WS", "UPSTOX_REST": "REST", "DB_EOD": "DB"}
    return {
        "symbol": data["symbol"],
        "ltp": data["ltp"],
        "source": source_map.get(data["source"], "NONE"),
        "timestamp": data["timestamp"],
        "stale": data.get("market_status") != "OPEN" or data.get("source") == "DB_EOD",
        "price_source": data["source"]
    }

async def get_ltp_bulk(symbols: List[str], access_token: str = None) -> Dict[str, Dict]:
    """Get live LTP bulk. Delegated to PriceService."""
    service = get_price_service()
    prices = await service.get_prices_bulk(symbols)
    source_map = {"UPSTOX_WS": "WS", "UPSTOX_REST": "REST", "DB_EOD": "DB"}
    results = {}
    for sym, d in prices.items():
        if d:
            results[sym] = {
                "ltp": d["ltp"],
                "source": source_map.get(d["source"], "NONE"),
                "timestamp": d["timestamp"],
                "stale": d.get("market_status") != "OPEN" or d.get("source") == "DB_EOD",
                "price_source": d["source"]
            }
    return results

def get_price_source_status() -> Dict:
    """Get status of price manager and market."""
    status_service = get_market_status_service()
    from config import settings
    return {
        "timestamp": datetime.now().isoformat(),
        "market_status": status_service.get_status().value,
        "upstox_token_configured": bool(settings.UPSTOX_ACCESS_TOKEN)
    }
