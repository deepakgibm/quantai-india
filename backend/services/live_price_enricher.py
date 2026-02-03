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

from utils.trade_logic import (
    calculate_atr_levels
)

# Use the comprehensive mapping (300+ Nifty 500 stocks)
INSTRUMENT_MAPPING = NIFTY_500_MAPPING

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
    return INSTRUMENT_MAPPING.get(symbol.upper())

async def fetch_live_ltp(symbols: List[str], access_token: str = None) -> Dict[str, float]:
    if not symbols: return {}
    if not access_token: access_token = settings.UPSTOX_ACCESS_TOKEN
    if not access_token: return {}
    prices = {}
    batch_size = 50
    tasks = []
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        tasks.append(_fetch_batch_ltp(batch, access_token))
    batch_results = await asyncio.gather(*tasks)
    for res in batch_results:
        prices.update(res)
    return prices

async def fetch_live_full_quotes(symbols: List[str], access_token: str = None) -> Dict[str, Dict[str, Any]]:
    if not symbols: return {}
    if not access_token: access_token = settings.UPSTOX_ACCESS_TOKEN
    if not access_token: return {}
    results = {}
    batch_size = 50
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        try:
            instrument_keys = []
            key_to_symbol = {}
            for s in batch:
                ik = get_instrument_key(s)
                if ik:
                    instrument_keys.append(ik)
                    key_to_symbol[ik] = s
                    key_to_symbol[ik.replace('|', ':')] = s
            if not instrument_keys: continue
            keys_param = ",".join(instrument_keys)
            encoded_keys = quote(keys_param, safe=',')
            url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={encoded_keys}"
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success" and data.get("data"):
                        for key, q in data["data"].items():
                            symbol = key_to_symbol.get(key)
                            if not symbol and ":" in key:
                                symbol = key_to_symbol.get(key.split(':')[-1])
                            if symbol:
                                results[symbol] = {
                                    "ltp": q.get("last_price"),
                                    "prev_close": q.get("ohlc", {}).get("close"),
                                    "volume": q.get("volume"),
                                    "timestamp": q.get("timestamp")
                                }
        except Exception as e:
            logger.error(f"Upstox full quote batch failed: {e}")
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
