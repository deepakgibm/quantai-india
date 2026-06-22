import httpx
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from urllib.parse import quote
from config import settings
from database import AsyncSessionLocal
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

# Import comprehensive Nifty 500 mapping
try:
    from data.nifty500_instruments import NIFTY_500_MAPPING
except ImportError:
    NIFTY_500_MAPPING = {}

from services.upstox_price_resolver import get_upstox_price_resolver
from utils.trade_logic import calculate_atr_levels

# Global cache for instrument mappings
INSTRUMENT_MAPPING = NIFTY_500_MAPPING.copy()
_mapping_loaded = False

def _hydrate_mapping_sync():
    """Hydrate mapping from DB synchronously (for module-level init)"""
    global _mapping_loaded
    if _mapping_loaded: return
    
    from sqlalchemy import create_engine, text
    from config import settings
    try:
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT symbol, instrument_key FROM instrument_master WHERE is_active = TRUE"))
            db_mapping = {row.symbol: row.instrument_key for row in result}
            INSTRUMENT_MAPPING.update(db_mapping)
            logger.info(f"Hydrated INSTRUMENT_MAPPING with {len(db_mapping)} keys from DB")
    except Exception as e:
        logger.error(f"Failed to hydrate INSTRUMENT_MAPPING from DB: {e}")
    finally:
        _mapping_loaded = True

# Trigger hydration
_hydrate_mapping_sync()

async def get_database_prices(symbols: List[str]) -> Dict[str, float]:
    """Fallback to database for prices when live APIs fail."""
    if not symbols:
        return {}
    prices = {}
    try:
        async with AsyncSessionLocal() as session:
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
    except Exception as e:
        logger.error(f"Database fallback error: {e}")
    return prices

async def get_database_movers_data(symbols: List[str]) -> Dict[str, Dict[str, float]]:
    """Used for calculating change percentage when live feeds are down."""
    if not symbols:
        return {}
    movers_data = {}
    try:
        async with AsyncSessionLocal() as session:
            query = text("""
                WITH ranked_candles AS (
                    SELECT im.symbol, sc.close, sc.candle_ts,
                           ROW_NUMBER() OVER (PARTITION BY im.symbol ORDER BY sc.candle_ts DESC) as rn
                    FROM stock_candle sc
                    JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                    WHERE sc.timeframe = 1440
                    AND sc.close > 0
                    AND im.symbol = ANY(:symbols)
                )
                SELECT symbol, close, rn
                FROM ranked_candles
                WHERE rn <= 2
            """)
            result = await session.execute(query, {"symbols": symbols})
            rows = result.fetchall()
            temp_data = {}
            for symbol, close, rn in rows:
                if symbol not in temp_data:
                    temp_data[symbol] = {}
                if rn == 1:
                    temp_data[symbol]["ltp"] = float(close)
                elif rn == 2:
                    temp_data[symbol]["prev_close"] = float(close)
            for symbol, data in temp_data.items():
                if "ltp" in data and "prev_close" in data:
                    movers_data[symbol] = data
                elif "ltp" in data:
                    movers_data[symbol] = {"ltp": data["ltp"], "prev_close": 0.0}
    except Exception as e:
        logger.error(f"Database movers fetch error: {e}")
    return movers_data

async def get_yfinance_price(symbol: str) -> Optional[float]:
    """Fallback to Yahoo Finance."""
    try:
        import yfinance as yf
        def _fetch():
            ticker = yf.Ticker(f"{symbol}.NS")
            info = ticker.info
            return info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        price = await asyncio.to_thread(_fetch)
        if price and price > 0:
            return float(price)
    except Exception as e:
        logger.error(f"yFinance fallback failed for {symbol}: {e}")
    return None

def get_instrument_key(symbol: str) -> Optional[str]:
    """
    Get the Upstox instrument key for a symbol.
    Supports prefixes like NSE_INDEX|NIFTY 50 or raw symbols.
    """
    if "|" in symbol:
        return symbol
        
    symbol_upper = symbol.upper()
    
    # 1. Check direct mapping first (most common)
    if symbol_upper in INSTRUMENT_MAPPING:
        return INSTRUMENT_MAPPING[symbol_upper]
        
    # 2. Heuristic for indices (e.g., "NIFTY 50", "NIFTY BANK")
    index_map = {
        "NIFTY 50": "NSE_INDEX|Nifty 50",
        "NIFTY BANK": "NSE_INDEX|Nifty Bank",
        "BANKNIFTY": "NSE_INDEX|Nifty Bank", # Added for common alias
        "INDIA VIX": "NSE_INDEX|India VIX",
        "FINNIFTY": "NSE_INDEX|Nifty Fin Service",
        "MIDCPNIFTY": "NSE_INDEX|NIFTY MID SELECT", # Added for common alias
        "NIFTY NEXT 50": "NSE_INDEX|Nifty Next 50",
        "NIFTY 100": "NSE_INDEX|Nifty 100"
    }
    
    if symbol_upper in index_map:
        return index_map[symbol_upper]
        
    return None

async def fetch_live_ltp(symbols: List[str], access_token: str = None) -> Dict[str, float]:
    if not symbols: return {}
    
    from services.upstox_client import get_upstox_client
    client = get_upstox_client(access_token)
    
    prices = {}
    batch_size = 50
    
    # Map symbols to keys
    mapped_keys = []
    key_to_symbol = {}
    for s in symbols:
        key = get_instrument_key(s)
        if key:
            mapped_keys.append(key)
            key_to_symbol[key] = s
        else:
            logger.warning(f"No instrument key mapping found for symbol: {s}")
            
    if not mapped_keys:
        return {}

    tasks = []
    for i in range(0, len(mapped_keys), batch_size):
        batch = mapped_keys[i:i + batch_size]
        tasks.append(client.get_live_quotes(batch))
        
    batch_results = await asyncio.gather(*tasks)
    for res in batch_results:
        for key, quote in res.items():
            symbol = key_to_symbol.get(key)
            if symbol:
                prices[symbol] = quote.get("last_price") or quote.get("close")
            
    return prices

async def fetch_live_full_quotes(symbols: List[str], access_token: str = None) -> Dict[str, Dict[str, Any]]:
    if not symbols: return {}
    
    from services.upstox_client import get_upstox_client
    client = get_upstox_client(access_token)
    
    results = {}
    batch_size = 50
    
    # Map symbols to keys
    mapped_keys = []
    key_to_symbol = {}
    for s in symbols:
        key = get_instrument_key(s)
        if key:
            mapped_keys.append(key)
            key_to_symbol[key] = s
            # Support EXCHANGE:SYMBOL format
            if "|" in key:
                exch = key.split("|")[0]
                key_to_symbol[f"{exch}:{s}"] = s
            key_to_symbol[f"NSE_EQ:{s}"] = s
            key_to_symbol[f"BSE_EQ:{s}"] = s
        else:
            logger.warning(f"No instrument key mapping found for symbol: {s}")

    if not mapped_keys:
        logger.warning(f"No valid instrument keys found for symbols: {symbols[:10]}")
        return {}

    logger.info(f"Enricher: Batching {len(mapped_keys)} keys for Upstox API in parallel")
    tasks = []
    batches = []
    for i in range(0, len(mapped_keys), batch_size):
        batch = mapped_keys[i:i + batch_size]
        batches.append(batch)
        tasks.append(client.get_live_quotes(batch))
        
    try:
        # Fetch all batches in parallel with a timeout of 3.5 seconds
        batch_results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=3.5)
        for idx, res in enumerate(batch_results):
            if isinstance(res, Exception):
                logger.error(f"Upstox full quote batch index {idx} failed (size={len(batches[idx])}): {res}")
                continue
            logger.info(f"Enricher: Received {len(res)} quotes from batch index {idx}")
            for key, q in res.items():
                symbol = key_to_symbol.get(key)
                if symbol:
                    results[symbol] = {
                        "ltp": q.get("last_price"),
                        "prev_close": q.get("previous_close"),
                        "volume": q.get("volume"),
                        "timestamp": q.get("timestamp")
                    }
    except asyncio.TimeoutError:
        logger.warning(f"Upstox batch fetch timed out after 3.5s for {len(mapped_keys)} keys")
        
    return results

async def _fetch_batch_ltp(symbols: List[str], access_token: str) -> Dict[str, float]:
    prices = {}
    key_to_symbol = {}
    instrument_keys = []
    for symbol in symbols:
        inst_key = get_instrument_key(symbol)
        if inst_key:
            instrument_keys.append(inst_key)
            key_to_symbol[inst_key] = symbol
            key_to_symbol[f"NSE_EQ:{symbol}"] = symbol
            key_to_symbol[f"BSE_EQ:{symbol}"] = symbol
            symbol_part = inst_key.split('|')[-1]
            key_to_symbol[f"NSE_EQ:{symbol_part}"] = symbol
            key_to_symbol[symbol_part] = symbol
    if instrument_keys:
        try:
            keys_param = ",".join(instrument_keys)
            url = f"https://api.upstox.com/v2/market-quote/ltp?instrument_key={quote(keys_param, safe=',')}"
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success" and data.get("data"):
                        for key, q_data in data["data"].items():
                            ltp = q_data.get("last_price")
                            if ltp:
                                symbol = key_to_symbol.get(key)
                                if not symbol and ":" in key:
                                    symbol = key_to_symbol.get(key.split(':')[-1])
                                if symbol:
                                    prices[symbol] = ltp
        except Exception as e:
            logger.error(f"Upstox batch LTP failed: {e}")
    return prices

async def enrich_scanner_results(results: List[Dict], access_token: str = None) -> List[Dict]:
    if not results: return results
    symbols = [r.get("symbol") for r in results if r.get("symbol")]
    resolver = get_upstox_price_resolver()
    bulk_prices = await resolver.get_prices_bulk(symbols)
    enriched = []
    for result in results:
        symbol = result.get("symbol", "").upper()
        p_data = bulk_prices.get(symbol, {})
        ltp = p_data.get("price")
        source = p_data.get("price_source", "NONE")
        res = result.copy()
        if ltp and ltp > 0:
            res["current_price"] = round(float(ltp), 2)
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
    resolver = get_upstox_price_resolver()
    data = await resolver.get_price(symbol)
    return data.get("price")

async def get_live_ltp(symbol: str, access_token: str = None) -> Dict:
    resolver = get_upstox_price_resolver()
    data = await resolver.get_price(symbol)
    source_map = {"UPSTOX_WS": "WS", "UPSTOX_REST": "REST", "DB_EOD": "DB"}
    return {
        "symbol": data["symbol"],
        "ltp": data["price"],
        "source": source_map.get(data["price_source"], "NONE"),
        "timestamp": data["timestamp"],
        "stale": not data["is_live"],
        "price_source": data["price_source"]
    }

async def get_ltp_bulk(symbols: List[str], access_token: str = None) -> Dict[str, Dict]:
    resolver = get_upstox_price_resolver()
    prices = await resolver.get_prices_bulk(symbols)
    source_map = {"UPSTOX_WS": "WS", "UPSTOX_REST": "REST", "DB_EOD": "DB"}
    results = {}
    for sym, d in prices.items():
        results[sym] = {
            "ltp": d["price"],
            "source": source_map.get(d["price_source"], "NONE"),
            "timestamp": d["timestamp"],
            "stale": not d["is_live"],
            "price_source": d["price_source"]
        }
    return results

def get_price_source_status() -> Dict:
    from services.market_hours_service import get_market_hours_service
    market_service = get_market_hours_service()
    return {
        "timestamp": datetime.now().isoformat(),
        "market_status": market_service.get_market_status(),
        "upstox_token_configured": bool(settings.UPSTOX_ACCESS_TOKEN)
    }
