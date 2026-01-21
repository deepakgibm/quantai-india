import httpx
import asyncio
from typing import List, Dict, Optional
from urllib.parse import quote
from config import settings
from database import AsyncSessionLocal
from sqlalchemy import text

# Import comprehensive Nifty 500 mapping
try:
    from data.nifty500_instruments import NIFTY_500_MAPPING
except ImportError:
    NIFTY_500_MAPPING = {}

# Use the comprehensive mapping (300+ Nifty 500 stocks)
INSTRUMENT_MAPPING = NIFTY_500_MAPPING


async def get_database_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Fallback to database for prices when live APIs fail.
    Fetches the most recent close prices from stock_candle table.
    """
    if not symbols:
        return {}
        
    prices = {}
    try:
        async with AsyncSessionLocal() as session:
            # Get the latest close price for each symbol using new schema
            query = text("""
                SELECT im.symbol, sc.close
                FROM (
                    SELECT instrument_id, close, 
                           ROW_NUMBER() OVER (PARTITION BY instrument_id ORDER BY candle_ts DESC) as rn
                    FROM stock_candle
                    WHERE timeframe = 1440
                    AND close > 0
                ) sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE sc.rn = 1
                AND im.symbol = ANY(:symbols)
            """)
            
            result = await session.execute(query, {"symbols": symbols})
            rows = result.fetchall()
            
            for symbol, close in rows:
                prices[symbol] = float(close)
        
        if prices:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"📊 Got {len(prices)} prices from database fallback")
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"⚠️ Database fallback error: {e}")
    
    return prices


async def get_yfinance_price(symbol: str) -> Optional[float]:
    """Fallback to Yahoo Finance for symbols not in Upstox mapping."""
    try:
        import yfinance as yf
        # yfinance is blocking, run in thread
        def _fetch():
            ticker = yf.Ticker(f"{symbol}.NS")
            info = ticker.info
            return info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            
        price = await asyncio.to_thread(_fetch)
        if price and price > 0:
            return float(price)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"⚠️ yFinance fallback failed for {symbol}: {e}")
    return None


def get_instrument_key(symbol: str) -> Optional[str]:
    """Get Upstox instrument key for a symbol, returns None if not found."""
    return INSTRUMENT_MAPPING.get(symbol.upper())


async def fetch_live_ltp(symbols: List[str], access_token: str = None) -> Dict[str, float]:
    """
    Fetch live LTP for multiple symbols from Upstox using BATCH requests.
    """
    if not symbols:
        return {}
        
    if not access_token:
        access_token = settings.UPSTOX_ACCESS_TOKEN
    
    if not access_token:
        return {}
    
    prices = {}
    
    # Batch size for Upstox (limit is 50 instruments per request)
    tasks = []
    batch_size = 50
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        tasks.append(_fetch_batch_ltp(batch, access_token))
    
    batch_results = await asyncio.gather(*tasks)
    for res in batch_results:
        prices.update(res)
    
    return prices


async def _fetch_batch_ltp(symbols: List[str], access_token: str) -> Dict[str, float]:
    """Fetch LTP for a batch of symbols in a SINGLE async request."""
    prices = {}
    
    # 1. Map symbols to instrument keys
    key_to_symbol = {}
    instrument_keys = []
    
    for symbol in symbols:
        inst_key = get_instrument_key(symbol)
        if inst_key:
            instrument_keys.append(inst_key)
            # Map all possible key formats that Upstox might return
            key_to_symbol[inst_key] = symbol
            # Standard Upstox V2 response format: NSE_EQ:SYMBOL
            key_to_symbol[f"NSE_EQ:{symbol}"] = symbol
            key_to_symbol[f"BSE_EQ:{symbol}"] = symbol
            
            symbol_part = inst_key.split('|')[-1]
            key_to_symbol[f"NSE_EQ:{symbol_part}"] = symbol
            key_to_symbol[symbol_part] = symbol
            
    # 2. Call Upstox Batch LTP API
    if instrument_keys:
        try:
            keys_param = ",".join(instrument_keys)
            encoded_keys = quote(keys_param, safe=',')
            url = f"https://api.upstox.com/v2/market-quote/ltp?instrument_key={encoded_keys}"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success" and data.get("data"):
                        for key, quote_data in data["data"].items():
                            ltp = quote_data.get("last_price")
                            if ltp and ltp > 0:
                                # Try full key, then split parts
                                symbol = key_to_symbol.get(key)
                                if not symbol:
                                    # Try extracting symbol from NSE_EQ:SYMBOL
                                    if ":" in key:
                                        parts = key.split(':')
                                        symbol = key_to_symbol.get(parts[-1])
                                        
                                if symbol:
                                    prices[symbol] = ltp
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"⚠️ Upstox batch LTP failed: {e}")

    # 3. yFinance Fallback for missing symbols
    missing_symbols = [s for s in symbols if s not in prices]
    if missing_symbols:
        try:
            import yfinance as yf
            
            def _fetch_yf_batch():
                # Use period="2d" to ensure we get data even if market hasn't opened today
                # interval="1m" is fine if we check multiple rows
                tickers = " ".join([f"{s}.NS" for s in missing_symbols])
                return yf.download(tickers, period="2d", interval="1m", progress=False, group_by='ticker')
            
            data = await asyncio.to_thread(_fetch_yf_batch)
            
            for s in missing_symbols:
                ticker = f"{s}.NS"
                try:
                    if len(missing_symbols) == 1:
                        # For single symbol, yf returns simple columns
                        if not data.empty:
                            price = data['Close'].iloc[-1]
                        else:
                            # Fallback to Ticker info for very fresh price
                            tick = yf.Ticker(ticker)
                            price = tick.info.get('currentPrice') or tick.info.get('regularMarketPrice')
                    else:
                        # For multiple symbols, yf returns MultiIndex
                        symbol_data = data[ticker]
                        if not symbol_data.empty:
                            price = symbol_data['Close'].dropna().iloc[-1]
                        else:
                            # Try info fallback
                            tick = yf.Ticker(ticker)
                            price = tick.info.get('currentPrice') or tick.info.get('regularMarketPrice')
                            
                    if price and price > 0:
                        prices[s] = float(price)
                except:
                    pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"⚠️ yFinance batch fallback failed: {e}")
            
    return prices


async def enrich_scanner_results(results: List[Dict], access_token: str = None) -> List[Dict]:
    """
    Enrich scanner results with live prices and source metadata.
    
    Uses centralized get_ltp_bulk() which implements:
    1. WebSocket cache (during market hours)
    2. Upstox REST API
    3. Database fallback
    
    CRITICAL: This function ensures:
    - entry_price, target_price, stop_loss are NEVER undefined/None
    - current_price is always populated with source badge
    - All numeric values are properly rounded
    """
    if not results:
        return results
    
    symbols = [r.get("symbol") for r in results if r.get("symbol")]
    if not symbols:
        return results
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Use centralized bulk LTP fetcher with source metadata
    bulk_prices = await get_ltp_bulk(symbols, access_token)
    
    enriched = []
    for result in results:
        symbol = result.get("symbol", "").upper()
        price_data = bulk_prices.get(symbol, {})
        live_price = price_data.get("ltp")
        price_source = price_data.get("source", "NONE")
        
        enriched_result = result.copy()
        
        # Determine base price (live or from result)
        if live_price and live_price > 0:
            rounded_price = round(float(live_price), 2)
        elif result.get("ltp") and result.get("ltp") > 0:
            rounded_price = round(float(result.get("ltp")), 2)
            price_source = "CACHED"
        elif result.get("close") and result.get("close") > 0:
            rounded_price = round(float(result.get("close")), 2)
            price_source = "CACHED"
        elif result.get("current_price") and result.get("current_price") > 0:
            rounded_price = round(float(result.get("current_price")), 2)
            price_source = "CACHED"
        else:
            # Cannot enrich without a valid price - sanitize and skip
            enriched_result = _sanitize_trade_levels(enriched_result, None)
            enriched_result["price_source"] = "NONE"
            enriched_result["entry_reason"] = "LTP_UNAVAILABLE"
            enriched.append(enriched_result)
            continue
        
        # Update all common price fields for consistency
        enriched_result["current_price"] = rounded_price
        enriched_result["ltp"] = rounded_price
        enriched_result["price_source"] = price_source  # WS, REST, DB, or NONE
        if "price" in enriched_result or result.get("price"):
            enriched_result["price"] = rounded_price
        
        # Determine trend/action for trade level calculation
        trend = enriched_result.get("trend") or enriched_result.get("signal_type", "BULLISH")
        action = enriched_result.get("action") or enriched_result.get("signal", "BUY")
        is_bullish = trend == "BULLISH" or action == "BUY" or "BUY" in str(action).upper()
        
        # ALWAYS calculate trade levels (overwrite any invalid values)
        entry = enriched_result.get("entry_price")
        target = enriched_result.get("target_price") or enriched_result.get("target_1")
        stoploss = enriched_result.get("stop_loss")
        
        # Fix entry if missing, None, 0, or undefined
        if not entry or entry <= 0 or str(entry).lower() == 'undefined':
            enriched_result["entry_price"] = round(rounded_price * (0.995 if is_bullish else 1.005), 2)
            enriched_result["entry_reason"] = "AUTO_CALCULATED"
        else:
            enriched_result["entry_price"] = round(float(entry), 2)
            
        # Fix target if missing, None, 0, or undefined
        if not target or target <= 0 or str(target).lower() == 'undefined':
            enriched_result["target_price"] = round(rounded_price * (1.05 if is_bullish else 0.95), 2)
        else:
            enriched_result["target_price"] = round(float(target), 2)
            
        # Fix stoploss if missing, None, 0, or undefined
        if not stoploss or stoploss <= 0 or str(stoploss).lower() == 'undefined':
            enriched_result["stop_loss"] = round(rounded_price * (0.97 if is_bullish else 1.03), 2)
        else:
            enriched_result["stop_loss"] = round(float(stoploss), 2)
        
        # Ensure target_1 is also set for frontends that expect it
        enriched_result["target_1"] = enriched_result["target_price"]
        
        enriched.append(enriched_result)
    
    return enriched


def _sanitize_trade_levels(result: Dict, price: Optional[float]) -> Dict:
    """
    Sanitize trade levels to never return undefined/None.
    If price is available, calculate reasonable defaults.
    If no price, set to None (frontend should display '--')
    """
    if price and price > 0:
        result["current_price"] = round(price, 2)
        result["entry_price"] = round(price * 0.995, 2)
        result["target_price"] = round(price * 1.05, 2)
        result["stop_loss"] = round(price * 0.97, 2)
    else:
        # Set to None explicitly (not undefined)
        result["current_price"] = None
        result["entry_price"] = None
        result["target_price"] = None
        result["stop_loss"] = None
    
    return result


async def get_single_live_price(symbol: str, access_token: str = None) -> Optional[float]:
    """Get live price for a single symbol."""
    prices = await fetch_live_ltp([symbol], access_token)
    return prices.get(symbol)


async def get_live_ltp(symbol: str, access_token: str = None) -> Dict:
    """
    AUTHORITATIVE live LTP function - use this for all price lookups.
    
    Priority (during market hours):
    1. WebSocket cache (MarketDataOrchestrator)
    2. Upstox REST API
    3. Database fallback
    
    Priority (after market hours):
    1. Upstox REST API (skip WS)
    2. Database fallback
    
    Returns:
        {
            "symbol": "RELIANCE",
            "ltp": 2850.50,
            "source": "WS" | "REST" | "DB",
            "timestamp": "2026-01-21T12:15:01+05:30",
            "stale": false
        }
    """
    from datetime import datetime
    import logging
    logger = logging.getLogger(__name__)
    
    from services.market_hours_service import get_market_hours_service
    from services.market_data_orchestrator import get_market_data_orchestrator
    
    if not access_token:
        access_token = settings.UPSTOX_ACCESS_TOKEN
    
    market_service = get_market_hours_service()
    is_market_open = market_service.is_market_open()
    
    result = {
        "symbol": symbol.upper(),
        "ltp": None,
        "source": "NONE",
        "timestamp": datetime.now().isoformat(),
        "stale": False,
        "market_open": is_market_open
    }
    
    # 1. During market hours, try WebSocket cache first
    if is_market_open:
        try:
            orchestrator = get_market_data_orchestrator()
            tick = orchestrator._data_cache.get(symbol.upper())
            if tick and hasattr(tick, 'ltp') and tick.ltp and tick.ltp > 0:
                # Check staleness (>10 seconds old)
                if hasattr(tick, 'timestamp'):
                    tick_time = datetime.fromisoformat(tick.timestamp.replace('Z', '+00:00')) if isinstance(tick.timestamp, str) else tick.timestamp
                    age_seconds = (datetime.now() - tick_time.replace(tzinfo=None)).total_seconds()
                    if age_seconds <= 10:
                        result["ltp"] = round(tick.ltp, 2)
                        result["source"] = "WS"
                        logger.debug(f"🔴 {symbol}: ₹{result['ltp']} from WS cache (fresh)")
                        return result
                    else:
                        logger.debug(f"⚠️ {symbol}: WS tick is {age_seconds:.1f}s old, trying REST")
                else:
                    # No timestamp, use it anyway
                    result["ltp"] = round(tick.ltp, 2)
                    result["source"] = "WS"
                    return result
        except Exception as e:
            logger.debug(f"WS cache miss for {symbol}: {e}")
    
    # 2. Try Upstox REST API
    try:
        prices = await fetch_live_ltp([symbol], access_token)
        if prices.get(symbol) and prices[symbol] > 0:
            result["ltp"] = round(prices[symbol], 2)
            result["source"] = "REST"
            logger.debug(f"🟡 {symbol}: ₹{result['ltp']} from REST API")
            return result
    except Exception as e:
        logger.warning(f"REST API failed for {symbol}: {e}")
    
    # 3. Final fallback to Database
    try:
        db_prices = await get_database_prices([symbol])
        if db_prices.get(symbol) and db_prices[symbol] > 0:
            result["ltp"] = round(db_prices[symbol], 2)
            result["source"] = "DB"
            result["stale"] = True  # DB price is always potentially stale
            logger.debug(f"🟢 {symbol}: ₹{result['ltp']} from DB (EOD)")
            return result
    except Exception as e:
        logger.error(f"DB fallback failed for {symbol}: {e}")
    
    logger.error(f"❌ {symbol}: LTP_UNAVAILABLE from all sources")
    result["source"] = "NONE"
    return result


async def get_ltp_bulk(symbols: List[str], access_token: str = None) -> Dict[str, Dict]:
    """
    Bulk LTP fetch with source metadata for each symbol.
    Optimized for batch operations.
    
    Returns:
        {
            "RELIANCE": {"ltp": 2850.50, "source": "WS", "timestamp": "...", "stale": false},
            "TCS": {"ltp": 4200.00, "source": "REST", "timestamp": "...", "stale": false},
            ...
        }
    """
    from datetime import datetime
    import logging
    logger = logging.getLogger(__name__)
    
    from services.market_hours_service import get_market_hours_service
    from services.market_data_orchestrator import get_market_data_orchestrator
    
    if not access_token:
        access_token = settings.UPSTOX_ACCESS_TOKEN
    
    market_service = get_market_hours_service()
    is_market_open = market_service.is_market_open()
    
    results = {}
    now = datetime.now()
    remaining_symbols = list(symbols)
    
    # 1. During market hours, check WS cache first
    if is_market_open:
        try:
            orchestrator = get_market_data_orchestrator()
            ws_hits = []
            for symbol in symbols:
                tick = orchestrator._data_cache.get(symbol.upper())
                if tick and hasattr(tick, 'ltp') and tick.ltp and tick.ltp > 0:
                    results[symbol.upper()] = {
                        "ltp": round(tick.ltp, 2),
                        "source": "WS",
                        "timestamp": now.isoformat(),
                        "stale": False
                    }
                    ws_hits.append(symbol)
            
            remaining_symbols = [s for s in symbols if s.upper() not in results]
            if ws_hits:
                logger.debug(f"🔴 WS cache hits: {len(ws_hits)} symbols")
        except Exception as e:
            logger.debug(f"WS cache bulk access failed: {e}")
    
    # 2. Fetch remaining from REST API
    if remaining_symbols:
        try:
            rest_prices = await fetch_live_ltp(remaining_symbols, access_token)
            for symbol, price in rest_prices.items():
                if price and price > 0:
                    results[symbol.upper()] = {
                        "ltp": round(price, 2),
                        "source": "REST",
                        "timestamp": now.isoformat(),
                        "stale": False
                    }
            remaining_symbols = [s for s in remaining_symbols if s.upper() not in results]
            if rest_prices:
                logger.debug(f"🟡 REST hits: {len(rest_prices)} symbols")
        except Exception as e:
            logger.warning(f"REST bulk fetch failed: {e}")
    
    # 3. Final fallback to DB for still-missing symbols
    if remaining_symbols:
        try:
            db_prices = await get_database_prices(remaining_symbols)
            for symbol, price in db_prices.items():
                if price and price > 0:
                    results[symbol.upper()] = {
                        "ltp": round(price, 2),
                        "source": "DB",
                        "timestamp": now.isoformat(),
                        "stale": True
                    }
            if db_prices:
                logger.debug(f"🟢 DB fallback hits: {len(db_prices)} symbols")
        except Exception as e:
            logger.error(f"DB bulk fallback failed: {e}")
    
    # Mark symbols with no data
    for symbol in symbols:
        if symbol.upper() not in results:
            results[symbol.upper()] = {
                "ltp": None,
                "source": "NONE",
                "timestamp": now.isoformat(),
                "stale": True,
                "error": "LTP_UNAVAILABLE"
            }
    
    logger.info(f"📊 Bulk LTP: {len([r for r in results.values() if r.get('ltp')])} of {len(symbols)} symbols priced")
    return results


def get_price_source_status() -> Dict:
    """
    Get current price source status for debugging.
    Returns cache state and health info.
    """
    from datetime import datetime
    import logging
    logger = logging.getLogger(__name__)
    
    from services.market_hours_service import get_market_hours_service
    
    try:
        from services.market_data_orchestrator import get_market_data_orchestrator
        orchestrator = get_market_data_orchestrator()
        orchestrator_status = orchestrator.get_status()
    except Exception as e:
        orchestrator_status = {"error": str(e)}
    
    market_service = get_market_hours_service()
    market_status = market_service.get_market_status()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "market_status": market_status,
        "orchestrator": orchestrator_status,
        "upstox_token_configured": bool(settings.UPSTOX_ACCESS_TOKEN),
        "instrument_mapping_size": len(INSTRUMENT_MAPPING)
    }


