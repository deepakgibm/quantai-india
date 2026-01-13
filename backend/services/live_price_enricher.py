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
    Fetches the most recent close prices from stock_candles table.
    """
    if not symbols:
        return {}
        
    prices = {}
    try:
        async with AsyncSessionLocal() as session:
            # Get the latest close price for each symbol
            query = text("""
                SELECT symbol, close
                FROM (
                    SELECT symbol, close, 
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY timestamp DESC) as rn
                    FROM stock_candles
                    WHERE symbol = ANY(:symbols)
                    AND timeframe = '1d'
                    AND close > 0
                ) t
                WHERE rn = 1
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
            key_to_symbol[inst_key] = symbol
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
                                symbol = key_to_symbol.get(key) or key_to_symbol.get(key.split(':')[-1])
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
                tickers = " ".join([f"{s}.NS" for s in missing_symbols])
                return yf.download(tickers, period="1d", interval="1m", progress=False, group_by='ticker')
            
            data = await asyncio.to_thread(_fetch_yf_batch)
            
            for s in missing_symbols:
                ticker = f"{s}.NS"
                try:
                    if len(missing_symbols) == 1:
                        price = data['Close'].iloc[-1]
                    else:
                        price = data[ticker]['Close'].iloc[-1]
                        
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
    Enrich scanner results with live prices from Upstox.
    """
    if not results:
        return results
    
    from utils.market_state import is_market_open
    market_open = is_market_open()
    
    if not market_open:
        # After hours: Keep prices from snapshots if they exist (already synced via ETL)
        # Only fetch for missing prices
        missing_symbols = [s for s in symbols if not any(r.get("symbol") == s and r.get("ltp") for r in results)]
        if not missing_symbols:
            return results
        live_prices = await fetch_live_ltp(missing_symbols, access_token)
    else:
        # Market open: Fetch live prices for all
        live_prices = await fetch_live_ltp(symbols, access_token)
    
    missing_symbols = [s for s in symbols if s not in live_prices]
    if missing_symbols:
        db_prices = await get_database_prices(missing_symbols)
        live_prices.update(db_prices)
    
    if not live_prices:
        return results
    
    enriched = []
    for result in results:
        symbol = result.get("symbol")
        live_price = live_prices.get(symbol)
        
        if live_price and live_price > 0:
            enriched_result = result.copy()
            enriched_result["current_price"] = round(live_price, 2)
            
            trend = enriched_result.get("trend", "BULLISH")
            action = enriched_result.get("action", "BUY")
            
            if trend == "BULLISH" or action == "BUY":
                enriched_result["entry_price"] = round(live_price * 0.995, 2)
                enriched_result["target_price"] = round(live_price * 1.05, 2)
                enriched_result["stop_loss"] = round(live_price * 0.97, 2)
            else:
                enriched_result["entry_price"] = round(live_price * 1.005, 2)
                enriched_result["target_price"] = round(live_price * 0.95, 2)
                enriched_result["stop_loss"] = round(live_price * 1.03, 2)
            
            enriched.append(enriched_result)
        else:
            enriched.append(result)
    
    return enriched


async def get_single_live_price(symbol: str, access_token: str = None) -> Optional[float]:
    """Get live price for a single symbol."""
    prices = await fetch_live_ltp([symbol], access_token)
    return prices.get(symbol)


async def get_live_ltp(symbol: str, access_token: str = None) -> Dict:
    """
    AUTHORITATIVE live LTP function - use this for all price lookups.
    Returns dict with ltp, source, and timestamp for validation.
    
    Usage:
        result = await get_live_ltp("RELIANCE")
        price = result.get("ltp")  # Live price
        source = result.get("source")  # 'upstox' or 'database'
        timestamp = result.get("timestamp")  # Price timestamp
    """
    from datetime import datetime
    import logging
    logger = logging.getLogger(__name__)
    
    if not access_token:
        access_token = settings.UPSTOX_ACCESS_TOKEN
    
    result = {
        "symbol": symbol.upper(),
        "ltp": None,
        "source": None,
        "timestamp": datetime.now().isoformat(),
        "stale": False
    }
    
    # 1. Try Upstox LIVE first
    prices = await fetch_live_ltp([symbol], access_token)
    if prices.get(symbol):
        result["ltp"] = round(prices[symbol], 2)
        result["source"] = "upstox"
        logger.info(f"💹 {symbol}: ₹{result['ltp']} from Upstox LIVE")
        return result
    
    # 2. Fallback to Database (mark as potentially stale)
    db_prices = await get_database_prices([symbol])
    if db_prices.get(symbol):
        result["ltp"] = round(db_prices[symbol], 2)
        result["source"] = "database"
        result["stale"] = True  # DB price may be stale
        logger.warning(f"⚠️ {symbol}: ₹{result['ltp']} from DATABASE (may be stale)")
        return result
    
    logger.error(f"❌ {symbol}: No price available from any source")
    return result

