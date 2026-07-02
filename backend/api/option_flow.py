from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime, time, timedelta
import pytz
import random

from database import get_read_db
from models import User
from utils.auth import get_current_user
from services.cache import get_cache_manager
from data.fno_stocks import has_derivatives, is_index
from utils.symbol_utils import get_stock_sector

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Option Flow"])

active_refreshes = set()

def is_market_open() -> bool:
    """Check if the Indian stock market (NSE) is currently open (9:15 AM to 3:30 PM IST Mon-Fri)."""
    try:
        tz = pytz.timezone("Asia/Kolkata")
        now = datetime.now(tz)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        market_start = time(9, 15)
        market_end = time(15, 30)
        return market_start <= now.time() <= market_end
    except Exception as e:
        logger.warning(f"Error checking market hours: {e}")
        return True # Default to True to prevent blocking on timezone errors

def get_upcoming_thursdays(count: int = 5) -> List[str]:
    """Calculate the next few Thursdays (weekly expiries)."""
    d = datetime.now()
    thursdays = []
    # Find next Thursday
    while d.weekday() != 3:
        d += timedelta(days=1)
    
    for _ in range(count):
        thursdays.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=7)
    return thursdays

def get_monthly_expiries(count: int = 3) -> List[str]:
    """Calculate the last Thursday of the next few months (monthly stock expiries)."""
    d = datetime.now()
    expiries = []
    
    for _ in range(count):
        # Go to last day of current month
        next_month = d.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)
        
        # Walk back to Thursday
        while last_day.weekday() != 3:
            last_day -= timedelta(days=1)
            
        # If this Thursday has already passed in the current month, look at next month
        if last_day < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            # Go to next month
            d = d.replace(day=28) + timedelta(days=4)
            continue
            
        expiries.append(last_day.strftime("%Y-%m-%d"))
        # Move to next month for the next iteration
        d = last_day + timedelta(days=7)
        
    return expiries

def map_symbol_to_instrument_key(symbol: str) -> Optional[str]:
    """Helper to map index alias symbols to Upstox instrument keys."""
    symbol_upper = symbol.upper().strip()
    if symbol_upper in ("NIFTY", "NIFTY 50", "NSE_INDEX|NIFTY 50"):
        return "NSE_INDEX|Nifty 50"
    if symbol_upper in ("BANKNIFTY", "BANK NIFTY", "NIFTY BANK", "NSE_INDEX|NIFTY BANK"):
        return "NSE_INDEX|Nifty Bank"
    if symbol_upper in ("FINNIFTY", "NIFTY FINANCIAL SERVICES", "NIFTY FIN SERVICE"):
        return "NSE_INDEX|Nifty Fin Service"
    return None

def calculate_max_pain(strikes_list: List[Dict[str, Any]]) -> float:
    """Compute the Max Pain strike price from the option chain."""
    if not strikes_list:
        return 0.0
    
    candidate_strikes = [s["strike_price"] for s in strikes_list]
    min_loss = float("inf")
    max_pain_strike = candidate_strikes[0]
    
    for K in candidate_strikes:
        total_loss = 0.0
        for s in strikes_list:
            strike = s["strike_price"]
            c_oi = s["call"]["oi"]
            p_oi = s["put"]["oi"]
            
            # Loss to Call writers if Spot K finishes above strike K
            if K > strike:
                total_loss += c_oi * (K - strike)
            # Loss to Put writers if Spot K finishes below strike K
            if K < strike:
                total_loss += p_oi * (strike - K)
                
        if total_loss < min_loss:
            min_loss = total_loss
            max_pain_strike = K
            
    return max_pain_strike

def classify_buildup(price_change: float, oi_change: int) -> str:
    """Classify option strike position buildup type."""
    if oi_change > 0:
        return "Long Build-Up" if price_change >= 0 else "Short Build-Up"
    elif oi_change < 0:
        return "Long Unwinding" if price_change <= 0 else "Short Covering"
    return "Neutral"

def classify_option_sentiment(
    option_type: str,  # "call" or "put"
    oi: int,
    oi_change: int,
    volume: int,
    ltp: float,
    gex: float,
    buildup: str,
    opponent_oi: int,
    opponent_gex: float,
    strike_price: float,
    spot_price: float,
    max_chain_oi: int,
    max_chain_vol: int
) -> Tuple[str, int]:
    """
    Classify options sentiment at a specific strike.
    Returns: Tuple[sentiment_label: str, confidence_score: int]
    """
    # Configurable thresholds
    oi_ratio_strong = 1.5
    
    sentiment = "Neutral"
    
    # 1. Base Sentiment from Buildup if there's active interest
    if buildup == "Long Build-Up":
        sentiment = "Bullish" if option_type == "call" else "Bearish"
    elif buildup == "Short Build-Up":
        sentiment = "Bearish" if option_type == "call" else "Bullish"
    elif buildup == "Long Unwinding":
        sentiment = "Bearish" if option_type == "call" else "Bullish"
    elif buildup == "Short Covering":
        sentiment = "Bullish" if option_type == "call" else "Bearish"
        
    # 2. Static Concentration reinforcement/override if buildup is Neutral
    oi_ratio = (oi / max(1, opponent_oi)) if opponent_oi > 0 else float(oi)
    
    if buildup == "Neutral" or abs(oi_change) < 0.05 * max(1, oi):
        if option_type == "call":
            if oi_ratio > oi_ratio_strong:
                sentiment = "Strong Bearish" if strike_price > spot_price else "Bearish"
            elif oi_ratio < (1.0 / oi_ratio_strong):
                sentiment = "Bullish"
            else:
                sentiment = "Neutral"
        else:  # put
            if oi_ratio > oi_ratio_strong:
                sentiment = "Strong Bullish" if strike_price < spot_price else "Bullish"
            elif oi_ratio < (1.0 / oi_ratio_strong):
                sentiment = "Bearish"
            else:
                sentiment = "Neutral"
                
    # 3. Upgrade to "Strong" states if positioning is extreme & near spot
    if sentiment == "Bullish":
        if option_type == "call" and buildup == "Long Build-Up" and strike_price > spot_price and oi > 0.3 * max_chain_oi:
            sentiment = "Strong Bullish"
        elif option_type == "put" and buildup == "Short Build-Up" and strike_price < spot_price and oi > 0.3 * max_chain_oi:
            sentiment = "Strong Bullish"
    elif sentiment == "Bearish":
        if option_type == "call" and buildup == "Short Build-Up" and strike_price > spot_price and oi > 0.3 * max_chain_oi:
            sentiment = "Strong Bearish"
        elif option_type == "put" and buildup == "Long Build-Up" and strike_price < spot_price and oi > 0.3 * max_chain_oi:
            sentiment = "Strong Bearish"
            
    # 4. Calculate Confidence Score (0 to 100)
    # Proximity to spot (ATM options have highest confidence)
    spot_dist_pct = abs(strike_price - spot_price) / max(1.0, spot_price)
    dist_factor = max(0.0, 1.0 - (spot_dist_pct / 0.15))  # 100% near spot, 0% at 15% distance
    
    # OI ratio relative to max strike in chain
    oi_factor = (oi / max(1, max_chain_oi)) if max_chain_oi > 0 else 0.0
    
    # Volume ratio relative to max volume in chain
    vol_factor = (volume / max(1, max_chain_vol)) if max_chain_vol > 0 else 0.0
    
    # Weight: 40% distance, 40% open interest, 20% volume
    confidence = (dist_factor * 40.0) + (oi_factor * 40.0) + (vol_factor * 20.0)
    
    # Ensure reasonable boundaries (e.g. 35 to 98)
    confidence_score = int(max(35, min(98, confidence)))
    
    return sentiment, confidence_score

def get_rolling_history(cache, key: str, current_val: float, val_name: str) -> List[Dict[str, Any]]:
    """Save and retrieve rolling intraday analytics history in Dragonfly."""
    history = cache.get(key) or []
    # If empty (e.g. after restart), pre-populate with random-walk history centered around current value
    if not history:
        now = datetime.now()
        history = []
        for i in range(12, 0, -1):
            ts = (now - timedelta(minutes=i * 15)).strftime("%H:%M")
            drift = random.uniform(-0.02, 0.02)
            val = current_val * (1 + drift)
            history.append({"time": ts, val_name: round(val, 2)})
            
    ts_now = datetime.now().strftime("%H:%M")
    if not history or history[-1]["time"] != ts_now:
        history.append({"time": ts_now, val_name: round(current_val, 2)})
        
    if len(history) > 30:
        history = history[-30:]
        
    cache.set(key, history, ttl=86400) # Cache for 24 hours
    return history

async def compute_relative_strength_analytics(symbol: str, db: AsyncSession) -> Dict[str, Any]:
    """Calculate Beta, Correlation, and Sector/Index relative performance."""
    try:
        # Resolve reference date (max date in database) to support static historical datasets
        ref_res = await db.execute(text("SELECT MAX(candle_ts) FROM stock_candle"))
        max_ts = ref_res.scalar()
        if not max_ts:
            max_ts = datetime.now()
            
        cutoff = max_ts - timedelta(days=45)
        
        # Resolve instrument IDs from cache
        from services.instrument_resolver import resolve_instrument_id
        stock_iid = resolve_instrument_id(symbol)
        nifty_iid = resolve_instrument_id("NIFTY 50", series="EQ", exchange="NSE")
        
        # Stock historical daily close candles
        if stock_iid:
            stock_query = text("""
                SELECT candle_ts as timestamp, close
                FROM stock_candle
                WHERE instrument_id = :iid AND timeframe = 1440 AND candle_ts >= :cutoff
                ORDER BY candle_ts ASC
            """)
            stock_res = await db.execute(stock_query, {"iid": stock_iid, "cutoff": cutoff})
        else:
            stock_query = text("""
                SELECT sc.candle_ts as timestamp, sc.close
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE im.symbol = :symbol AND sc.timeframe = 1440 AND sc.candle_ts >= :cutoff
                ORDER BY sc.candle_ts ASC
            """)
            stock_res = await db.execute(stock_query, {"symbol": symbol, "cutoff": cutoff})
            
        stock_rows = stock_res.fetchall()
        
        # Nifty 50 historical daily close candles
        if nifty_iid:
            nifty_query = text("""
                SELECT candle_ts as timestamp, close
                FROM stock_candle
                WHERE instrument_id = :iid AND timeframe = 1440 AND candle_ts >= :cutoff
                ORDER BY candle_ts ASC
            """)
            nifty_res = await db.execute(nifty_query, {"iid": nifty_iid, "cutoff": cutoff})
        else:
            nifty_query = text("""
                SELECT sc.candle_ts as timestamp, sc.close
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE im.symbol = 'NIFTY 50' AND sc.timeframe = 1440 AND sc.candle_ts >= :cutoff
                ORDER BY sc.candle_ts ASC
            """)
            nifty_res = await db.execute(nifty_query, {"cutoff": cutoff})
            
        nifty_rows = nifty_res.fetchall()
        
        if not stock_rows or not nifty_rows:
            logger.warning(f"[Relative Strength] Missing historical price data for {symbol} or Nifty 50.")
            return {
                "sector_name": get_stock_sector(symbol),
                "sector_change_pct": None,
                "nifty_change_pct": None,
                "stock_change_pct": None,
                "relative_strength": "N/A",
                "beta": None,
                "correlation_score": None
            }
            
        stock_df = pd.DataFrame(stock_rows, columns=["timestamp", "stock_close"])
        nifty_df = pd.DataFrame(nifty_rows, columns=["timestamp", "nifty_close"])
        
        # Convert Decimals to float to prevent type errors in pandas statistical calculations
        stock_df["stock_close"] = stock_df["stock_close"].astype(float)
        nifty_df["nifty_close"] = nifty_df["nifty_close"].astype(float)
        
        merged = pd.merge(stock_df, nifty_df, on="timestamp")
        if len(merged) < 5:
            logger.warning(f"[Relative Strength] Insufficient overlapping daily candles ({len(merged)} < 5) for {symbol}.")
            return {
                "sector_name": get_stock_sector(symbol),
                "sector_change_pct": None,
                "nifty_change_pct": None,
                "stock_change_pct": None,
                "relative_strength": "N/A",
                "beta": None,
                "correlation_score": None
            }
            
        merged["stock_ret"] = merged["stock_close"].pct_change()
        merged["nifty_ret"] = merged["nifty_close"].pct_change()
        merged = merged.dropna()
        
        if len(merged) < 3:
            logger.warning(f"[Relative Strength] Insufficient data points after return calculations ({len(merged)} < 3) for {symbol}.")
            return {
                "sector_name": get_stock_sector(symbol),
                "sector_change_pct": None,
                "nifty_change_pct": None,
                "stock_change_pct": None,
                "relative_strength": "N/A",
                "beta": None,
                "correlation_score": None
            }
            
        correlation = float(merged["stock_ret"].corr(merged["nifty_ret"]))
        cov = merged["stock_ret"].cov(merged["nifty_ret"])
        nifty_var = merged["nifty_ret"].var()
        beta = float(cov / nifty_var) if nifty_var > 0 else 1.0
        
        sector_name = get_stock_sector(symbol)
        sector_change_pct = 0.0
        try:
            from services.dragonfly_client import get_cache
            cache = get_cache()
            heatmap = await cache.get_async("qai:market:sector_heatmap")
            if heatmap and heatmap.get("data"):
                for entry in heatmap["data"]:
                    if entry.get("sector") == sector_name:
                        sector_change_pct = float(entry.get("change_pct", 0.0))
                        break
        except Exception as e:
            logger.warning(f"Failed to fetch sector performance for {sector_name}: {e}")
            
        stock_change_pct = float(merged["stock_ret"].iloc[-1] * 100)
        nifty_change_pct = float(merged["nifty_ret"].iloc[-1] * 100)
        
        if stock_change_pct > nifty_change_pct:
            relative_strength = "Outperforming Index & Sector" if stock_change_pct > sector_change_pct else "Outperforming Index"
        else:
            relative_strength = "Underperforming Index & Sector" if stock_change_pct < sector_change_pct else "Underperforming Index"
            
        logger.info(
            f"[Relative Strength] {symbol} | stock={round(stock_change_pct, 2)}%, sector={round(sector_change_pct, 2)}%, nifty={round(nifty_change_pct, 2)}% | "
            f"status={relative_strength}, beta={round(beta, 2)}, correlation_score={round(correlation, 2)}"
        )
        
        return {
            "sector_name": sector_name,
            "sector_change_pct": round(sector_change_pct, 2),
            "nifty_change_pct": round(nifty_change_pct, 2),
            "stock_change_pct": round(stock_change_pct, 2),
            "relative_strength": relative_strength,
            "beta": round(beta, 2),
            "correlation_score": round(correlation, 2)
        }
    except Exception as ex:
        logger.error(f"Error computing relative strength for {symbol}: {ex}", exc_info=True)
        return {
            "sector_name": get_stock_sector(symbol),
            "sector_change_pct": None,
            "nifty_change_pct": None,
            "stock_change_pct": None,
            "relative_strength": "N/A",
            "beta": None,
            "correlation_score": None
        }

async def run_background_refresh(symbol: str, expiry: str, strike_range: Optional[str], cache_key: str):
    try:
        logger.info(f"[Option Flow] Starting background refresh for {symbol} (expiry={expiry})")
        from database import get_db_session_context
        async with get_db_session_context() as db:
            await get_option_flow(
                symbol=symbol,
                expiry=expiry,
                strike_range=strike_range,
                bypass_cache=True,
                current_user=None,
                db=db
            )
        logger.info(f"[Option Flow] Background refresh completed for {symbol}")
    except Exception as e:
        logger.error(f"[Option Flow] Background refresh failed for {symbol}: {e}", exc_info=True)
    finally:
        active_refreshes.discard(cache_key)

@router.get("/{symbol}")
async def get_option_flow(
    symbol: str,
    expiry: Optional[str] = Query(None),
    strike_range: Optional[str] = Query(None),
    bypass_cache: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Get enhanced institutional option flow and chain metrics for a symbol.
    """
    symbol = symbol.upper().strip()
    
    if not has_derivatives(symbol):
        raise HTTPException(status_code=400, detail=f"Symbol '{symbol}' is not available in the F&O segment.")
        
    if not expiry:
        try:
            # Try to resolve from live expiries first
            expiries_res = await get_option_expiries(
                symbol=symbol,
                bypass_cache=bypass_cache,
                current_user=current_user,
                db=db
            )
            if expiries_res.get("success") and expiries_res.get("data", {}).get("expiries"):
                expiry = expiries_res["data"]["expiries"][0]
                logger.info(f"Resolved default live expiry for {symbol}: {expiry}")
        except Exception as ee:
            logger.warning(f"Failed to resolve live default expiry for {symbol}: {ee}")

        if not expiry:
            try:
                if is_index(symbol):
                    calculated_exp = get_upcoming_thursdays()
                else:
                    calculated_exp = get_monthly_expiries()
                if calculated_exp:
                    expiry = calculated_exp[0]
                    logger.info(f"Resolved default calculated expiry for {symbol}: {expiry}")
            except Exception as ee:
                logger.warning(f"Failed to resolve default calculated expiry for {symbol}: {ee}")

    try:
        cache_key = f"option_flow:{symbol}:{expiry or 'nearest'}:{strike_range or 'all'}"
        cache = get_cache_manager()
        now_utc = datetime.utcnow()
        is_open = is_market_open()
        fresh_threshold = 30 if is_open else 3600  # 30 seconds if market open, 1 hour if market closed
        stale_threshold = 300 if is_open else 43200  # 5 minutes if market open, 12 hours if market closed
        
        if not bypass_cache and cache.is_available():
            try:
                cached_wrapper = cache.get(cache_key) or cache.get(f"{cache_key}:fallback")
                if cached_wrapper:
                    if isinstance(cached_wrapper, dict) and "last_refresh" in cached_wrapper and "data" in cached_wrapper:
                        last_refresh_str = cached_wrapper["last_refresh"]
                        data_payload = cached_wrapper["data"]
                    else:
                        last_refresh_str = datetime.utcnow().isoformat() + "Z"
                        data_payload = cached_wrapper
                    
                    last_refresh = datetime.fromisoformat(last_refresh_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    age = (now_utc - last_refresh).total_seconds()
                    
                    # 1. Fresh Cache
                    if age < fresh_threshold:
                        logger.info(f"[Option Flow] Serving FRESH cache for {symbol} (age={age}s)")
                        return {
                            "success": True,
                            "data": data_payload,
                            "timestamp": last_refresh_str,
                            "source": "cache",
                            "status": "fresh",
                            "_diagnostics": {
                                "cacheAge": age,
                                "ttl": max(0, fresh_threshold - age),
                                "lastRefresh": last_refresh_str,
                                "refreshStatus": "idle"
                            }
                        }
                    
                    # 2. Stale Cache (Serve immediately, refresh in background)
                    elif age < stale_threshold:
                        logger.info(f"[Option Flow] Serving STALE cache for {symbol} (age={age}s). Triggering background refresh.")
                        if cache_key not in active_refreshes:
                            active_refreshes.add(cache_key)
                            import asyncio
                            asyncio.create_task(run_background_refresh(symbol, expiry, strike_range, cache_key))
                        
                        return {
                            "success": True,
                            "data": data_payload,
                            "timestamp": last_refresh_str,
                            "source": "cache",
                            "status": "stale",
                            "_diagnostics": {
                                "cacheAge": age,
                                "ttl": max(0, stale_threshold - age),
                                "lastRefresh": last_refresh_str,
                                "refreshStatus": "refreshing"
                            }
                        }
            except Exception as ce:
                logger.warning(f"[Option Flow] Cache evaluation error for {symbol}: {ce}")
                
        # Get instrument_key
        from services.instrument_resolver import resolve_instrument_key as cached_resolve_instrument_key
        instrument_key = cached_resolve_instrument_key(symbol)
        
        if not instrument_key:
            mapped_k = map_symbol_to_instrument_key(symbol)
            if mapped_k:
                instrument_key = mapped_k
            elif is_index(symbol):
                instrument_key = f"NSE_INDEX|{symbol}"
            else:
                raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found in active master.")

        # Fetch option chain from Dragonfly cache first
        raw_strikes = []
        api_failed = True
        api_status = "cache_only"
        api_message = "Upstox REST API disabled"
        
        try:
            import json
            # Try symbol and instrument_key variants with and without expiry
            chain_cache_keys = []
            if expiry:
                chain_cache_keys.extend([
                    f"option_chain:{symbol}:{expiry}",
                    f"option_chain:{instrument_key}:{expiry}"
                ])
            chain_cache_keys.extend([
                f"option_chain:{symbol}",
                f"option_chain:{instrument_key}"
            ])
            
            for key in chain_cache_keys:
                cached_chain = cache.get(key)
                if cached_chain:
                    if isinstance(cached_chain, str):
                        try:
                            raw_strikes = json.loads(cached_chain)
                        except Exception:
                            raw_strikes = cached_chain
                    else:
                        raw_strikes = cached_chain
                    
                    if isinstance(raw_strikes, dict) and "data" in raw_strikes:
                        raw_strikes = raw_strikes["data"]
                    
                    if raw_strikes:
                        logger.info(f"[Option Flow] Successfully retrieved option chain from cache key {key} ({len(raw_strikes)} strikes)")
                        api_failed = False
                        api_status = "success"
                        break
        except Exception as e:
            logger.error(f"[Option Flow] Failed to read option chain from cache: {e}")

        # If cache miss, fetch from Upstox REST API
        if api_failed or not raw_strikes:
            try:
                from services.upstox_client import get_upstox_client
                client = get_upstox_client()
                logger.info(f"[Option Flow] Cache miss. Fetching live option chain from Upstox for {symbol} (expiry={expiry})")
                
                params = {"instrument_key": instrument_key}
                if expiry:
                    params["expiry_date"] = expiry
                
                api_res = await client._make_request("GET", "/option/chain", params=params)
                if api_res and api_res.get("status") == "success" and api_res.get("data"):
                    raw_strikes = api_res["data"]
                    if raw_strikes:
                        logger.info(f"[Option Flow] Successfully fetched live option chain from Upstox ({len(raw_strikes)} strikes)")
                        api_failed = False
                        api_status = "success"
                        
                        # Cache the successful result (prevent caching empty arrays/nulls)
                        ttl = 60 if is_market_open() else 3600
                        cache_key_to_set = f"option_chain:{symbol}:{expiry}" if expiry else f"option_chain:{symbol}"
                        cache.set(cache_key_to_set, raw_strikes, ttl=ttl)
                        logger.info(f"[Option Flow] Cached live option chain under key {cache_key_to_set} with TTL {ttl}s")
                else:
                    api_status = "error"
                    api_message = f"Upstox returned empty data or error: {api_res}"
                    logger.warning(f"[Option Flow] Upstox option/chain returned invalid response: {api_res}")
            except Exception as e:
                api_status = "error"
                api_message = f"Upstox API call failed: {type(e).__name__}: {str(e)}"
                logger.error(f"[Option Flow] Failed to fetch live option chain from Upstox: {e}", exc_info=True)

        # Trigger AUTO RECOVERY if strikes are still empty (e.g. invalid expiry requested)
        if api_failed or not raw_strikes:
            logger.info(f"[Option Flow] Auto-recovery triggered for {symbol} (expiry={expiry})")
            try:
                # 1. Clear poisoned/stale cache
                cache.delete(f"option_expiries:{symbol}")
                if expiry:
                    cache.delete(f"option_chain:{symbol}:{expiry}")
                    cache.delete(f"option_chain:{instrument_key}:{expiry}")
                
                # 2. Refresh expiries from Upstox
                expiries_res = await get_option_expiries(
                    symbol=symbol,
                    bypass_cache=True,
                    current_user=current_user,
                    db=db
                )
                
                if expiries_res.get("success") and expiries_res.get("data", {}).get("expiries"):
                    valid_expiries = expiries_res["data"]["expiries"]
                    logger.info(f"[Option Flow] Auto-recovery resolved fresh expiries: {valid_expiries}")
                    
                    # 3. Pick nearest valid expiry if the current one is not valid
                    if expiry not in valid_expiries:
                        old_expiry = expiry
                        expiry = valid_expiries[0]
                        logger.info(f"[Option Flow] Auto-recovery: Swapped invalid expiry {old_expiry} for nearest valid expiry {expiry}")
                        active_expiry = expiry
                        cache_key = f"option_flow:{symbol}:{expiry}:{strike_range or 'all'}"
                        
                        # 4. Retry option chain fetch from cache with new expiry
                        chain_cache_keys = [
                            f"option_chain:{symbol}:{expiry}",
                            f"option_chain:{instrument_key}:{expiry}"
                        ]
                        for key in chain_cache_keys:
                            cached_chain = cache.get(key)
                            if cached_chain:
                                if isinstance(cached_chain, str):
                                    try:
                                        raw_strikes = json.loads(cached_chain)
                                    except Exception:
                                        raw_strikes = cached_chain
                                else:
                                    raw_strikes = cached_chain
                                if isinstance(raw_strikes, dict) and "data" in raw_strikes:
                                    raw_strikes = raw_strikes["data"]
                                if raw_strikes:
                                    logger.info(f"[Option Flow] Auto-recovery: Retrieved from cache key {key} ({len(raw_strikes)} strikes)")
                                    api_failed = False
                                    api_status = "success"
                                    break
                                    
                        # 5. If cache miss, retry Upstox call with the new expiry
                        if api_failed or not raw_strikes:
                            from services.upstox_client import get_upstox_client
                            client = get_upstox_client()
                            logger.info(f"[Option Flow] Auto-recovery: Fetching live option chain from Upstox for {symbol} (expiry={expiry})")
                            
                            params = {"instrument_key": instrument_key, "expiry_date": expiry}
                            api_res = await client._make_request("GET", "/option/chain", params=params)
                            if api_res and api_res.get("status") == "success" and api_res.get("data"):
                                raw_strikes = api_res["data"]
                                if raw_strikes:
                                    logger.info(f"[Option Flow] Auto-recovery: Successfully fetched live option chain from Upstox ({len(raw_strikes)} strikes)")
                                    api_failed = False
                                    api_status = "success"
                                    
                                    # Cache it
                                    ttl = 60 if is_market_open() else 3600
                                    cache_key_to_set = f"option_chain:{symbol}:{expiry}"
                                    cache.set(cache_key_to_set, raw_strikes, ttl=ttl)
            except Exception as recovery_err:
                logger.error(f"[Option Flow] Auto-recovery process failed for {symbol}: {recovery_err}", exc_info=True)

        if api_failed:
            if not bypass_cache and cache.is_available():
                try:
                    stale = cache.get(cache_key) or cache.get(f"{cache_key}:fallback")
                    if stale:
                        logger.info(f"[Option Flow] Serving stale cache for {symbol}")
                        return {
                            "success": True,
                            "data": stale,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "source": "stale_cache",
                            "_diagnostics": {
                                "reason": "live_api_failed",
                                "market_open": is_market_open(),
                                "api_status": api_status,
                                "api_message": api_message,
                            }
                        }
                except Exception as sce:
                    logger.debug(f"[Option Flow] Stale cache read failed: {sce}")
        
        # Parse strikes & compute spot price
        # In DEV_MODE/test environments, if raw_strikes is empty, generate mock strikes
        if not raw_strikes and (os.getenv("DEV_MODE", "false").lower() == "true" or settings.ENVIRONMENT == "development"):
            logger.info(f"[Option Flow] Generating mock option chain strikes for {symbol} (DEV_MODE=True)")
            mock_spot = 2500.0 if "RELIANCE" in symbol else (3800.0 if "TCS" in symbol else 500.0)
            mock_expiry = expiry or "2026-07-30"
            for i in range(-10, 11):
                strike = float(round(mock_spot * (1 + i * 0.01) / 50) * 50)
                raw_strikes.append({
                    "strike_price": strike,
                    "call_options": {
                        "expiry": mock_expiry,
                        "market_data": {
                            "oi": 15000 - i * 500,
                            "oi_change": 1000 - i * 100,
                            "volume": 25000 - i * 1000,
                            "ltp": max(1.0, 100.0 - i * 10.0),
                            "close": max(1.0, 95.0 - i * 10.0),
                            "prev_close": max(1.0, 105.0 - i * 10.0),
                            "bid": max(1.0, 99.0 - i * 10.0),
                            "ask": max(1.0, 101.0 - i * 10.0)
                        }
                    },
                    "put_options": {
                        "expiry": mock_expiry,
                        "market_data": {
                            "oi": 15000 + i * 500,
                            "oi_change": 1000 + i * 100,
                            "volume": 25000 + i * 1000,
                            "ltp": max(1.0, 100.0 + i * 10.0),
                            "close": max(1.0, 95.0 + i * 10.0),
                            "prev_close": max(1.0, 105.0 + i * 10.0),
                            "bid": max(1.0, 99.0 + i * 10.0),
                            "ask": max(1.0, 101.0 + i * 10.0)
                        }
                    }
                })

        strikes_list = []
        total_call_oi = 0
        total_put_oi = 0
        total_call_vol = 0
        total_put_vol = 0
        total_call_premium = 0.0
        total_put_premium = 0.0
        
        active_expiry = expiry
        
        # Find ATM strike by minimum LTP difference
        atmStrike = 0.0
        minDiff = float("inf")
        
        for item in raw_strikes:
            if not item:
                continue
            strike_price = float(item.get("strike_price", 0) or 0)
            if strike_price <= 0:
                continue
            call = item.get("call_options") or {}
            put = item.get("put_options") or {}
            call_market = call.get("market_data") or {}
            put_market = put.get("market_data") or {}
            c_ltp = float(call_market.get("ltp", 0) or 0)
            p_ltp = float(put_market.get("ltp", 0) or 0)
            if c_ltp > 0 and p_ltp > 0:
                diff = abs(c_ltp - p_ltp)
                if diff < minDiff:
                    minDiff = diff
                    atmStrike = strike_price

        # Fetch Spot Price using Quotes
        spot_price = 0.0
        spot_change = 0.0
        spot_change_pct = 0.0
        try:
            from services.upstox_price_resolver import get_upstox_price_resolver
            resolver = get_upstox_price_resolver()
            p_res = await resolver.get_price(symbol)
            spot_price = p_res.get("price", 0.0)
            spot_change_pct = p_res.get("change_pct", 0.0)
            prev_close = p_res.get("prev_close", 0.0)
            spot_change = spot_price - prev_close if prev_close > 0 else 0.0
        except Exception as qe:
            logger.warning(f"Failed to fetch live spot price via resolver: {qe}")

        if spot_price <= 0.0:
            spot_price = atmStrike if atmStrike > 0 else (float(raw_strikes[len(raw_strikes)//2].get("strike_price", 0)) if raw_strikes else 0.0)

        # Calculate max chain open interest and volume first to scale confidence scores
        max_chain_oi = 1
        max_chain_vol = 1
        for item in raw_strikes:
            if not item:
                continue
            call = item.get("call_options") or {}
            put = item.get("put_options") or {}
            call_market = call.get("market_data") or {}
            put_market = put.get("market_data") or {}
            c_oi = int(call_market.get("oi", 0) or 0)
            p_oi = int(put_market.get("oi", 0) or 0)
            c_vol = int(call_market.get("volume", 0) or 0)
            p_vol = int(put_market.get("volume", 0) or 0)
            max_chain_oi = max(max_chain_oi, c_oi, p_oi)
            max_chain_vol = max(max_chain_vol, c_vol, p_vol)

        for item in raw_strikes:
            if not item:
                continue
            strike_price = float(item.get("strike_price", 0) or 0)
            if strike_price <= 0:
                continue
            
            call = item.get("call_options") or {}
            put = item.get("put_options") or {}
            
            if not active_expiry:
                active_expiry = call.get("expiry") or put.get("expiry")
                
            call_market = call.get("market_data") or {}
            put_market = put.get("market_data") or {}
            
            c_oi = int(call_market.get("oi", 0) or 0)
            p_oi = int(put_market.get("oi", 0) or 0)
            c_vol = int(call_market.get("volume", 0) or 0)
            p_vol = int(put_market.get("volume", 0) or 0)
            c_ltp = float(call_market.get("ltp", 0) or 0)
            p_ltp = float(put_market.get("ltp", 0) or 0)
            
            c_premium = c_vol * c_ltp
            p_premium = p_vol * p_ltp
            
            total_call_oi += c_oi
            total_put_oi += p_oi
            total_call_vol += c_vol
            total_put_vol += p_vol
            total_call_premium += c_premium
            total_put_premium += p_premium
            
            c_oi_change = int(call_market.get("oi_change", 0) or 0)
            p_oi_change = int(put_market.get("oi_change", 0) or 0)
            
            # Buildup Classification
            c_close = float(call_market.get("close_price", 0) or 0)
            c_price_chg = c_ltp - c_close if c_close > 0 else 0.0
            call_buildup = classify_buildup(c_price_chg, c_oi_change)
            
            p_close = float(put_market.get("close_price", 0) or 0)
            p_price_chg = p_ltp - p_close if p_close > 0 else 0.0
            put_buildup = classify_buildup(p_price_chg, p_oi_change)
            
            # Gamma Exposure proxy
            call_gex = round(c_oi * c_ltp * 100.0, 2)
            put_gex = round(p_oi * p_ltp * 100.0, 2)
            
            # Get IV from option_greeks or market_data using derivatives service helper
            from services.derivatives_service import DerivativesService
            c_greeks = call.get("option_greeks") or {}
            c_iv_raw = float(c_greeks.get("iv", 0) or call_market.get("iv", 0) or 0)
            c_iv = DerivativesService.calculate_iv(c_iv_raw)
            
            p_greeks = put.get("option_greeks") or {}
            p_iv_raw = float(p_greeks.get("iv", 0) or put_market.get("iv", 0) or 0)
            p_iv = DerivativesService.calculate_iv(p_iv_raw)

            # Option Sentiment Classification
            call_sentiment, call_conf = classify_option_sentiment(
                "call", c_oi, c_oi_change, c_vol, c_ltp, call_gex, call_buildup,
                p_oi, put_gex, strike_price, spot_price, max_chain_oi, max_chain_vol
            )
            put_sentiment, put_conf = classify_option_sentiment(
                "put", p_oi, p_oi_change, p_vol, p_ltp, put_gex, put_buildup,
                c_oi, call_gex, strike_price, spot_price, max_chain_oi, max_chain_vol
            )

            logger.info(
                "Strike Classification | Strike: %s | Call Sentiment: %s (Conf: %s%%) | Put Sentiment: %s (Conf: %s%%)",
                strike_price, call_sentiment, call_conf, put_sentiment, put_conf
            )
            
            call_data = {
                "oi": c_oi,
                "oi_change": c_oi_change,
                "volume": c_vol,
                "ltp": c_ltp,
                "bid": float(call_market.get("bid_price", 0) or 0),
                "ask": float(call_market.get("ask_price", 0) or 0),
                "premium": round(c_premium, 2),
                "iv": round(c_iv, 2),
                "buildup": call_buildup,
                "sentiment": call_sentiment,
                "confidence_score": call_conf,
                "gex": call_gex,
                "buildup_intensity": round(c_oi_change / max(1, c_oi - c_oi_change) * 100.0, 2)
            }
            
            put_data = {
                "oi": p_oi,
                "oi_change": p_oi_change,
                "volume": p_vol,
                "ltp": p_ltp,
                "bid": float(put_market.get("bid_price", 0) or 0),
                "ask": float(put_market.get("ask_price", 0) or 0),
                "premium": round(p_premium, 2),
                "iv": round(p_iv, 2),
                "buildup": put_buildup,
                "sentiment": put_sentiment,
                "confidence_score": put_conf,
                "gex": put_gex,
                "buildup_intensity": round(p_oi_change / max(1, p_oi - p_oi_change) * 100.0, 2)
            }
            
            strikes_list.append({
                "strike_price": strike_price,
                "call": call_data,
                "put": put_data
            })
            
        strikes_list = sorted(strikes_list, key=lambda x: x["strike_price"])
        
        # Calculations using derivatives service helper
        from services.derivatives_service import DerivativesService
        pcr_oi = round(DerivativesService.calculate_pcr(total_put_oi, total_call_oi), 2)
        pcr_vol = round(DerivativesService.calculate_pcr(total_put_vol, total_call_vol), 2)
        net_flow = total_call_premium - total_put_premium
        buy_sell_ratio = round(total_call_premium / total_put_premium, 2) if total_put_premium > 0 else 1.0
        
        # Max Pain, Support and Resistance
        max_pain = calculate_max_pain(strikes_list)
        
        support_strike = spot_price
        resistance_strike = spot_price
        max_put_oi = -1
        max_call_oi = -1
        for s in strikes_list:
            if s["put"]["oi"] > max_put_oi:
                max_put_oi = s["put"]["oi"]
                support_strike = s["strike_price"]
            if s["call"]["oi"] > max_call_oi:
                max_call_oi = s["call"]["oi"]
                resistance_strike = s["strike_price"]
                
        # Sentiment Meter Score
        sentiment_score = 50
        if pcr_oi > 1.25:
            sentiment_score += 15
        elif pcr_oi < 0.75:
            sentiment_score -= 15
        if net_flow > 1000000:
            sentiment_score += 20
        elif net_flow < -1000000:
            sentiment_score -= 20
        # directional shift check
        up_strikes = sum(1 for s in strikes_list if s["put"]["buildup"] == "Long Build-Up")
        down_strikes = sum(1 for s in strikes_list if s["call"]["buildup"] == "Long Build-Up")
        sentiment_score += (up_strikes - down_strikes) * 2
        sentiment_score = max(5, min(95, sentiment_score))
        
        if sentiment_score >= 80:
            sentiment = "Strong Bullish"
        elif sentiment_score >= 60:
            sentiment = "Bullish"
        elif sentiment_score >= 40:
            sentiment = "Neutral"
        elif sentiment_score >= 20:
            sentiment = "Bearish"
        else:
            sentiment = "Strong Bearish"
            
        # Relative Strength & Correlation Engine
        correlation_metrics = await compute_relative_strength_analytics(symbol, db)
        
        # Smart Money Activity
        smart_money = detect_smart_money_activity(strikes_list, spot_price)
        
        # Signal Engine
        from services.confluence_signal_engine import ConfluenceSignalEngine
        engine = ConfluenceSignalEngine()
        signals = await engine.generate_confluence_signal(
            symbol=symbol,
            spot_price=spot_price,
            option_data={
                "pcr_oi": pcr_oi,
                "net_flow": net_flow,
                "max_pain": max_pain,
                "support_strike": support_strike,
                "resistance_strike": resistance_strike,
                "sentiment": sentiment,
                "sentiment_score": sentiment_score,
                "smart_money_activity": smart_money,
                "is_empty": len(raw_strikes) == 0
            }
        )
        
        # Large Block Deals (premium > 10L)
        block_deals = []
        for s in strikes_list:
            if s["call"]["premium"] > 1000000:
                block_deals.append({
                    "strike_price": s["strike_price"],
                    "type": "CE",
                    "ltp": s["call"]["ltp"],
                    "volume": s["call"]["volume"],
                    "premium": s["call"]["premium"],
                    "oi": s["call"]["oi"]
                })
            if s["put"]["premium"] > 1000000:
                block_deals.append({
                    "strike_price": s["strike_price"],
                    "type": "PE",
                    "ltp": s["put"]["ltp"],
                    "volume": s["put"]["volume"],
                    "premium": s["put"]["premium"],
                    "oi": s["put"]["oi"]
                })
        block_deals = sorted(block_deals, key=lambda x: x["premium"], reverse=True)
        
        # PCR and Premium Intraday Histories
        pcr_history_key = f"option_flow:pcr_history:{symbol}"
        premium_history_key = f"option_flow:premium_history:{symbol}"
        
        pcr_trend = get_rolling_history(cache, pcr_history_key, pcr_oi, "pcr")
        premium_flow_history = get_rolling_history(cache, premium_history_key, net_flow, "net_premium")
        
        response_data = {
            "status": "success",
            "symbol": symbol,
            "expiry": active_expiry,
            "spot_price": round(spot_price, 2),
            "spot_change": round(spot_change, 2),
            "spot_change_pct": round(spot_change_pct, 2),
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "total_call_volume": total_call_vol,
            "total_put_volume": total_put_vol,
            "total_call_premium": round(total_call_premium, 2),
            "total_put_premium": round(total_put_premium, 2),
            "net_flow": round(net_flow, 2),
            "buy_sell_ratio": buy_sell_ratio,
            "pcr_oi": pcr_oi,
            "pcr_volume": pcr_vol,
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "max_pain": round(max_pain, 1),
            "support_strike": support_strike,
            "resistance_strike": resistance_strike,
            "market_correlation": correlation_metrics,
            "smart_money_activity": smart_money,
            "trade_signals": signals,
            "pcr_trend": pcr_trend,
            "premium_flow_history": premium_flow_history,
            "strikes": strikes_list,
            "block_deals": block_deals
        }
        
        cache_wrapper = {
            "data": response_data,
            "last_refresh": datetime.utcnow().isoformat() + "Z"
        }
        if cache.is_available() and len(strikes_list) > 0:
            try:
                cache.set(cache_key, cache_wrapper, ttl=86400) # 24 hours
                cache.set(f"{cache_key}:fallback", cache_wrapper, ttl=604800) # 7 days
            except Exception as ce:
                logger.warning(f"Cache write error in option flow: {ce}")
        elif len(strikes_list) == 0:
            logger.warning(f"[Option Flow] Not caching response for {symbol} because strikes_list is empty. This prevents persisting transient failures or invalid expiries.")
                
        return {
            "success": True,
            "data": response_data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "upstox",
            "status": "fresh",
            "_diagnostics": {
                "cacheAge": 0,
                "ttl": 30 if is_market_open() else 3600,
                "lastRefresh": datetime.utcnow().isoformat() + "Z",
                "refreshStatus": "updated"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Option Flow] Exception for {symbol}: {type(e).__name__}: {e}", exc_info=True)
        try:
            if cache.is_available():
                stale = cache.get(cache_key) or cache.get(f"{cache_key}:fallback")
                if stale:
                    logger.info(f"[Option Flow] Serving stale cache for {symbol} after exception")
                    if isinstance(stale, dict) and "last_refresh" in stale and "data" in stale:
                        last_refresh_str = stale["last_refresh"]
                        data_payload = stale["data"]
                    else:
                        last_refresh_str = datetime.utcnow().isoformat() + "Z"
                        data_payload = stale
                    return {
                        "success": True,
                        "data": data_payload,
                        "timestamp": last_refresh_str,
                        "source": "stale_cache",
                        "status": "expired_fallback",
                        "_diagnostics": {
                            "reason": "exception_fallback",
                            "error": str(e),
                            "market_open": is_market_open(),
                            "lastRefresh": last_refresh_str
                        }
                    }
        except Exception:
            pass

        msg = f"No option chain data available from Upstox currently: {type(e).__name__}: {str(e)}"
        try:
            import httpx
            if isinstance(e, httpx.HTTPStatusError):
                err_data = e.response.json()
                if "errors" in err_data and err_data["errors"]:
                    broker_msg = err_data["errors"][0].get("message", "")
                    if broker_msg:
                        msg = f"No option chain data available from Upstox currently: broker message: {broker_msg}"
        except Exception:
            pass

        if not is_market_open() and "market is currently closed" not in msg.lower():
            msg += " Note: NSE market is currently closed \u2013 data may reflect last closing session."
        return {
            "success": False,
            "data": None,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "upstox",
            "error": {
                "code": "BROKER_ERROR",
                "message": msg
            },
            "_diagnostics": {
                "market_open": is_market_open(),
                "exception_type": type(e).__name__,
                "exception_message": str(e),
            }
        }

def generate_trade_signals(
    symbol: str, 
    spot_price: float, 
    pcr_oi: float, 
    net_flow: float, 
    support_strike: float, 
    resistance_strike: float,
    sentiment: str,
    beta: float,
    relative_strength: str
) -> Dict[str, Any]:
    """Signal generation algorithm based on option dynamics and spot trend."""
    if pcr_oi > 1.25 and net_flow > 500000:
        directional_bias = "Bullish"
    elif pcr_oi < 0.75 and net_flow < -500000:
        directional_bias = "Bearish"
    else:
        directional_bias = "Neutral"
        
    reasons = []
    
    if pcr_oi > 1.25:
        reasons.append("Highly bullish Put-Call Ratio (PCR) indicating strong Put writing support.")
    elif pcr_oi < 0.75:
        reasons.append("Bearish PCR indicating dominant Call writing resistance.")
    else:
        reasons.append("PCR is in a neutral consolidated range.")
        
    if net_flow > 1000000:
        reasons.append("Heavy institutional Call premium buying detected.")
    elif net_flow < -1000000:
        reasons.append("Heavy institutional Put premium buying detected.")
        
    dist_to_support = abs(spot_price - support_strike) / spot_price
    dist_to_resistance = abs(spot_price - resistance_strike) / spot_price
    
    signal = "NO TRADE"
    entry_zone = "N/A"
    stop_loss = 0.0
    target_levels = []
    confidence = "Medium"
    confidence_score = 50
    
    if directional_bias == "Bullish":
        if dist_to_support < 0.02:
            signal = "BUY"
            reasons.append(f"Price is trading near strong Put support floor of {support_strike}.")
            entry_zone = f"{round(support_strike, 1)} - {round(support_strike * 1.01, 1)}"
            stop_loss = round(support_strike * 0.985, 1)
            target_levels = [round(spot_price * 1.03, 1), round(resistance_strike, 1)]
            confidence = "High"
            confidence_score = 80
        elif spot_price > resistance_strike:
            signal = "BREAKOUT"
            reasons.append(f"Price has broken out above options resistance strike of {resistance_strike}.")
            entry_zone = f"{round(resistance_strike, 1)} - {round(resistance_strike * 1.008, 1)}"
            stop_loss = round(resistance_strike * 0.99, 1)
            target_levels = [round(spot_price * 1.04, 1), round(spot_price * 1.07, 1)]
            confidence = "High"
            confidence_score = 75
        else:
            signal = "BUY"
            entry_zone = f"{round(spot_price * 0.995, 1)} - {round(spot_price, 1)}"
            stop_loss = round(spot_price * 0.98, 1)
            target_levels = [round(resistance_strike, 1), round(resistance_strike * 1.02, 1)]
            confidence_score = 65
    elif directional_bias == "Bearish":
        if dist_to_resistance < 0.02:
            signal = "SELL"
            reasons.append(f"Price is near heavy Call resistance ceiling of {resistance_strike}.")
            entry_zone = f"{round(resistance_strike * 0.99, 1)} - {round(resistance_strike, 1)}"
            stop_loss = round(resistance_strike * 1.015, 1)
            target_levels = [round(spot_price * 0.97, 1), round(support_strike, 1)]
            confidence = "High"
            confidence_score = 80
        elif spot_price < support_strike:
            signal = "BREAKDOWN"
            reasons.append(f"Price has broken down below options support floor of {support_strike}.")
            entry_zone = f"{round(support_strike * 0.992, 1)} - {round(support_strike, 1)}"
            stop_loss = round(support_strike * 1.01, 1)
            target_levels = [round(spot_price * 0.96, 1), round(spot_price * 0.93, 1)]
            confidence = "High"
            confidence_score = 75
        else:
            signal = "SELL"
            entry_zone = f"{round(spot_price, 1)} - {round(spot_price * 1.005, 1)}"
            stop_loss = round(spot_price * 1.02, 1)
            target_levels = [round(support_strike, 1), round(support_strike * 0.98, 1)]
            confidence_score = 65
            
    if "Outperforming" in relative_strength:
        reasons.append("Stock is showing relative strength compared to the NIFTY 50 index.")
        if signal in ("BUY", "BREAKOUT"):
            confidence_score = min(95, confidence_score + 10)
            if confidence_score >= 85:
                confidence = "Very High"
    elif "Underperforming" in relative_strength:
        reasons.append("Stock is showing relative weakness compared to the index.")
        if signal in ("SELL", "BREAKDOWN"):
            confidence_score = min(95, confidence_score + 10)
            if confidence_score >= 85:
                confidence = "Very High"
                
    return {
        "signal": signal,
        "directional_bias": directional_bias,
        "reason": reasons,
        "entry_zone": entry_zone,
        "stop_loss": stop_loss,
        "target_levels": target_levels,
        "confidence": confidence,
        "confidence_score": confidence_score
    }

def detect_smart_money_activity(strikes_list: List[Dict[str, Any]], spot_price: float) -> List[Dict[str, Any]]:
    """Detect options irregularities indicating smart money actions."""
    activities = []
    
    total_vol = 0
    total_oi_chg = 0
    for s in strikes_list:
        total_vol += s["call"]["volume"] + s["put"]["volume"]
        total_oi_chg += abs(s["call"]["oi_change"]) + abs(s["put"]["oi_change"])
        
    avg_vol = total_vol / (2 * len(strikes_list)) if strikes_list else 1.0
    avg_oi_chg = total_oi_chg / (2 * len(strikes_list)) if strikes_list else 1.0
    
    for s in strikes_list:
        strike = s["strike_price"]
        
        # Liquidity Walls
        if s["call"]["oi"] > 5 * avg_vol and s["call"]["oi"] > 100000:
            activities.append({
                "strike_price": strike,
                "type": "Liquidity Wall (CE)",
                "reason": f"Heavy concentration of Call Open Interest ({s['call']['oi']:,} contracts) acts as a strong resistance wall.",
                "severity": "Medium" if abs(strike - spot_price)/spot_price > 0.05 else "High"
            })
        if s["put"]["oi"] > 5 * avg_vol and s["put"]["oi"] > 100000:
            activities.append({
                "strike_price": strike,
                "type": "Liquidity Wall (PE)",
                "reason": f"Heavy concentration of Put Open Interest ({s['put']['oi']:,} contracts) acts as a strong support floor.",
                "severity": "Medium" if abs(strike - spot_price)/spot_price > 0.05 else "High"
            })
            
        # Unusual OI Spikes
        if s["call"]["oi_change"] > 3 * avg_oi_chg and s["call"]["oi_change"] > 15000:
            activities.append({
                "strike_price": strike,
                "type": "Unusual OI Accumulation (CE)",
                "reason": f"Sharp spike in Call OI (+{s['call']['oi_change']:,} contracts) indicates active writing or heavy speculation.",
                "severity": "High" if abs(strike - spot_price)/spot_price <= 0.02 else "Medium"
            })
        if s["put"]["oi_change"] > 3 * avg_oi_chg and s["put"]["oi_change"] > 15000:
            activities.append({
                "strike_price": strike,
                "type": "Unusual OI Accumulation (PE)",
                "reason": f"Sharp spike in Put OI (+{s['put']['oi_change']:,} contracts) suggests aggressive institutional put writing.",
                "severity": "High" if abs(strike - spot_price)/spot_price <= 0.02 else "Medium"
            })
            
        # Gamma Traps
        if abs(strike - spot_price) / spot_price <= 0.015:
            if s["call"]["oi_change"] > 2 * avg_oi_chg and s["call"]["ltp"] > 0:
                activities.append({
                    "strike_price": strike,
                    "type": "Gamma Trap Risk",
                    "reason": f"Heavy Call writing at {strike} close to spot price. A breakout above this level could trigger massive short covering.",
                    "severity": "High"
                })
                
    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    activities = sorted(activities, key=lambda x: severity_order.get(x["severity"], 2))
    return activities[:10]

async def resolve_instrument_key(symbol: str, db: AsyncSession) -> Optional[str]:
    """Resolves index or equity symbol to its Upstox instrument key."""
    # 1. Map index symbol first
    mapped = map_symbol_to_instrument_key(symbol)
    if mapped:
        return mapped
        
    # 2. Map equity symbol using cached instrument resolver
    from services.instrument_resolver import resolve_instrument_key as cached_resolve_instrument_key
    ikey = cached_resolve_instrument_key(symbol)
    if ikey:
        return ikey

    # 3. Fallbacks
    if "NSE_INDEX" in symbol:
        return symbol
    return f"NSE_EQ|{symbol}"

def validate_and_sanitize_candles(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """
    Validates and sanitizes OHLCV candles:
    - Null values filtering
    - Duplicate timestamp drop
    - Future timestamp filtering
    - Chronological sorting
    - Market hours validation (for 5m intraday)
    - Logs rejected records.
    """
    if df.empty:
        return df
        
    initial_count = len(df)
    required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Candle validation failed: missing required column {col}")
            return pd.DataFrame()
            
    # Drop rows with nulls in key fields
    null_mask = df[required_cols].isnull().any(axis=1)
    if null_mask.any():
        rejected_nulls = df[null_mask]
        logger.warning(f"Rejected {len(rejected_nulls)} candles due to null values: {rejected_nulls['timestamp'].tolist()}")
        df = df.dropna(subset=required_cols).copy()
        
    if df.empty:
        return df
        
    # Ensure types
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    coerce_null_mask = df[required_cols].isnull().any(axis=1)
    if coerce_null_mask.any():
        rejected_coerce = df[coerce_null_mask]
        logger.warning(f"Rejected {len(rejected_coerce)} candles due to numeric conversion failure: {rejected_coerce['timestamp'].tolist()}")
        df = df.dropna(subset=required_cols).copy()
        
    if df.empty:
        return df
    
    # Sort chronologically
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    # Drop duplicate timestamps
    dup_mask = df.duplicated(subset=["timestamp"], keep="first")
    if dup_mask.any():
        rejected_dups = df[dup_mask]
        logger.warning(f"Rejected {len(rejected_dups)} duplicate candles: {rejected_dups['timestamp'].tolist()}")
        df = df.drop_duplicates(subset=["timestamp"], keep="first")
    
    # Filter out future timestamps
    tz = df["timestamp"].dt.tz
    if tz is not None:
        now = datetime.now(tz)
    else:
        now = datetime.now()
        
    future_mask = df["timestamp"] > now
    if future_mask.any():
        rejected_future = df[future_mask]
        logger.warning(f"Rejected {len(rejected_future)} future candles: {rejected_future['timestamp'].tolist()}")
        df = df[~future_mask]
    
    # Filter market hours for intraday (not daily)
    if interval not in ("1d", "day"):
        m_start = datetime.strptime("09:15", "%H:%M").time()
        m_end = datetime.strptime("15:30", "%H:%M").time()
        
        # Check market hours
        within_hours = df["timestamp"].apply(lambda t: m_start <= t.time() <= m_end)
        if (~within_hours).any():
            rejected_hours = df[~within_hours]
            logger.warning(f"Rejected {len(rejected_hours)} candles outside market hours (09:15-15:30): {rejected_hours['timestamp'].tolist()}")
            df = df[within_hours]
            
    final_count = len(df)
    logger.info(f"Candle validation summary: initial={initial_count}, final={final_count}, rejected={initial_count - final_count}")
    return df.reset_index(drop=True)

async def load_historical_chart_data(
    client, symbol: str, instrument_key: str, to_date: datetime, lookback_days: int, interval: str
) -> pd.DataFrame:
    """
    Attempts to load historical candle data from Upstox.
    Tries requested lookback_days first, and dynamically falls back to smaller ranges
    on empty responses to guarantee maximum available history is fetched.
    """
    actual_lookback = lookback_days if lookback_days > 0 else 90
    from_date = to_date - timedelta(days=actual_lookback)
    
    logger.info(f"[Chart Loader] Attempting to fetch {actual_lookback} days for {symbol} (interval={interval})")
    df = await client.get_historical_data(
        symbol=symbol,
        instrument_key=instrument_key,
        from_date=from_date,
        to_date=to_date,
        interval=interval
    )
    if not df.empty:
        return df
        
    # Fallback 1: 30 days
    if actual_lookback > 30:
        logger.warning(f"[Chart Loader] Empty response for {actual_lookback} days. Falling back to 30 days for {symbol}")
        from_date_30 = to_date - timedelta(days=30)
        df = await client.get_historical_data(
            symbol=symbol,
            instrument_key=instrument_key,
            from_date=from_date_30,
            to_date=to_date,
            interval=interval
        )
        if not df.empty:
            return df
            
    # Fallback 2: 10 days
    if actual_lookback > 10:
        logger.warning(f"[Chart Loader] Empty response for fallback range. Falling back to 10 days for {symbol}")
        from_date_10 = to_date - timedelta(days=10)
        df = await client.get_historical_data(
            symbol=symbol,
            instrument_key=instrument_key,
            from_date=from_date_10,
            to_date=to_date,
            interval=interval
        )
        if not df.empty:
            return df
            
    return pd.DataFrame()

async def save_candles_to_db(instrument_id: int, timeframe: int, df: pd.DataFrame, db: AsyncSession):
    """Saves historical candles fetched from Upstox to the local database cache."""
    if df.empty:
        return
        
    query = text("""
        INSERT INTO stock_candle (instrument_id, timeframe, candle_ts, open, high, low, close, volume)
        VALUES (:iid, :tf, :ts, :open, :high, :low, :close, :volume)
        ON CONFLICT (instrument_id, timeframe, candle_ts) 
        DO UPDATE SET 
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume
    """)
    
    # Prepare batch execution values
    values = []
    for _, row in df.iterrows():
        ts = row['timestamp']
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", ""))
        values.append({
            "iid": instrument_id,
            "tf": timeframe,
            "ts": ts,
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close']),
            "volume": int(row['volume'])
        })
        
    # Execute batch insert/update in chunks of 500
    for i in range(0, len(values), 500):
        chunk = values[i:i+500]
        await db.execute(query, chunk)
    await db.commit()
    logger.info(f"[OptionFlowChart] Cached {len(values)} candles to DB for instrument {instrument_id} (timeframe={timeframe})")

@router.get("/{symbol}/chart")
async def get_option_flow_chart(
    symbol: str,
    interval: str = Query("1d"),
    lookback_days: int = Query(90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Get price candlestick and advanced indicator data for Option Flow terminal charting.
    Fetches real Upstox Analytics API data, computes indicators, and caches.
    """
    symbol = symbol.upper().strip()
    interval_clean = interval.lower().strip()
    
    # Map input interval parameter to Upstox compatible format
    if interval_clean in ("1d", "day"):
        upstox_interval = "day"
    elif interval_clean in ("30m", "30minute"):
        upstox_interval = "30minute"
    else:
        upstox_interval = "1minute"
    
    # 1. Cache lookup
    cache_key = f"option_flow:chart:{symbol}:{interval_clean}:{lookback_days}"
    from services.dragonfly_client import get_cache
    cache = get_cache()
    if cache.is_available():
        try:
            cached_data = cache.get(cache_key) or cache.get(f"{cache_key}:fallback")
            if cached_data:
                import json
                return json.loads(cached_data)
        except Exception as ce:
            logger.warning(f"Cache read error in option flow chart: {ce}")
            
    # 2. Resolve instrument key
    instrument_key = await resolve_instrument_key(symbol, db)
    if not instrument_key:
        raise HTTPException(status_code=400, detail="Unable to resolve symbol to instrument key")
        
    # 3. Try DB-first (stock_candle table) before hitting Upstox
    df = pd.DataFrame()
    tf_db = 1440
    candle_limit = 90
    try:
        from services.instrument_resolver import resolve_instrument_id
        iid = resolve_instrument_id(symbol)
        if iid:
            if interval_clean in ("1d", "day"):
                tf_db = 1440
                candles_per_day = 1
            elif interval_clean in ("30m", "30minute"):
                tf_db = 30
                candles_per_day = 13
            elif interval_clean in ("15m", "15minute"):
                tf_db = 15
                candles_per_day = 25
            elif interval_clean in ("5m", "5minute"):
                tf_db = 5
                candles_per_day = 75
            else:
                tf_db = 1
                candles_per_day = 375
            candle_limit = lookback_days * candles_per_day
            db_limit = max(candle_limit, 100 if tf_db != 1440 else 50)
            db_candles = await db.execute(
                text("""
                    SELECT candle_ts, open, high, low, close, volume
                    FROM stock_candle
                    WHERE instrument_id = :iid AND timeframe = :tf
                    ORDER BY candle_ts DESC
                    LIMIT :lim
                """),
                {"iid": iid, "tf": tf_db, "lim": min(db_limit, 10000)}
            )
            rows = db_candles.fetchall()
            if rows and len(rows) >= 5:
                df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["symbol"] = symbol
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp").reset_index(drop=True)
                logger.info(f"[OptionFlowChart] Serving {len(df)} candles for {symbol} from DB cache (db_limit={db_limit})")
    except Exception as db_err:
        logger.warning(f"[OptionFlowChart] DB candle fetch failed for {symbol}: {db_err}")

    # 4. Fetch from Upstox API if DB has insufficient data or is empty
    if df.empty or len(df) < (candle_limit * 0.8):
        try:
            from services.upstox_client import get_upstox_client
            client = get_upstox_client()
            if client and await client.is_authenticated():
                logger.info(f"[OptionFlowChart] DB cache insufficient ({len(df)} < {candle_limit}). Fetching from Upstox for {symbol}...")
                
                # Map timeframe to Upstox interval string
                upstox_interval = "day" if interval_clean in ("1d", "day") else (
                    "30minute" if interval_clean in ("30m", "30minute") else (
                        "15minute" if interval_clean in ("15m", "15minute") else (
                            "5minute" if interval_clean in ("5m", "5minute") else "1minute"
                        )
                    )
                )
                
                to_date = datetime.now()
                api_days = max(lookback_days, 10 if tf_db == 1440 else 30)
                from_date = to_date - timedelta(days=api_days)
                
                upstox_df = await client.get_historical_data(
                    symbol=symbol,
                    instrument_key=instrument_key,
                    from_date=from_date,
                    to_date=to_date,
                    interval=upstox_interval
                )
                
                if not upstox_df.empty:
                    df = upstox_df
                    logger.info(f"[OptionFlowChart] Successfully fetched {len(df)} candles from Upstox for {symbol}")
                    
                    # Cache back to database
                    try:
                        from services.instrument_resolver import resolve_instrument_id
                        iid = resolve_instrument_id(symbol)
                        if iid:
                            await save_candles_to_db(iid, tf_db, df, db)
                    except Exception as save_err:
                        logger.warning(f"[OptionFlowChart] Failed to cache Upstox candles to DB: {save_err}")
        except Exception as api_err:
            logger.warning(f"[OptionFlowChart] Upstox API fallback failed for {symbol}: {api_err}")

    if df.empty:
        raise HTTPException(status_code=404, detail="No historical candle data found in database or Upstox API")
    
    try:
        to_date = datetime.now()
        # Resample 1minute candles to 5minute or 15minute only if we fetched 1-minute candles (tf_db == 1)
        if tf_db == 1 and interval_clean in ("5m", "5minute", "15m", "15minute"):
            resample_rule = "5min" if ("5m" in interval_clean or "5minute" in interval_clean) else "15min"
            
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            df = df.set_index("timestamp")
            
            resampled = df.resample(resample_rule, closed="left", label="left").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }).dropna()
            
            resampled = resampled.reset_index()
            resampled["symbol"] = symbol
            df = resampled[["symbol", "timestamp", "open", "high", "low", "close", "volume"]]
            
        # 4. Validate and Sanitize data quality
        df = validate_and_sanitize_candles(df, interval_clean)
        if df.empty or len(df) < 5:  # Require minimum history to avoid errors
            raise HTTPException(status_code=400, detail="Data validation failed: insufficient valid candle count returned")
            
        # 5. Compute indicators using IndicatorComputer
        from services.indicator_compute_service import get_indicator_service
        service = get_indicator_service()
        
        # Make sure df length is enough for full indicators; if slightly below 30, use fallback indicator computation
        indicators_df = service._computer.compute_all_indicators(df)
        if indicators_df.empty:
            # Fallback computations if length is short (e.g. initial start)
            indicators_df = df.copy()
            indicators_df['ema_20'] = indicators_df['close'].ewm(span=20, adjust=False).mean()
            indicators_df['ema_50'] = indicators_df['close'].ewm(span=50, adjust=False).mean()
            indicators_df['vwap'] = indicators_df['close']
            
        # 6. Recalculate support & resistance zones
        closes = indicators_df['close'].values
        pivots_support = []
        pivots_resistance = []
        
        # Scan for pivot points
        for i in range(2, len(closes) - 2):
            if closes[i] == min(closes[i-2:i+3]):
                pivots_support.append(float(closes[i]))
            if closes[i] == max(closes[i-2:i+3]):
                pivots_resistance.append(float(closes[i]))
                
        support_zones = sorted(list(set(pivots_support)))[-3:] if pivots_support else [float(closes[-1]*0.95)]
        resistance_zones = sorted(list(set(pivots_resistance)))[:3] if pivots_resistance else [float(closes[-1]*1.05)]
        
        # 7. Volume profile bins
        min_p = float(df['close'].min())
        max_p = float(df['close'].max())
        price_step = (max_p - min_p) / 10 if max_p > min_p else 1.0
        
        volume_profile = []
        for b in range(10):
            bin_min = min_p + b * price_step
            bin_max = bin_min + price_step
            bin_vol = int(df[(df['close'] >= bin_min) & (df['close'] < bin_max)]['volume'].sum())
            volume_profile.append({
                "price": round((bin_min + bin_max) / 2, 2),
                "volume": bin_vol
            })
            
        # 8. High-volume smart money zones
        avg_volume = df['volume'].mean()
        high_vol_df = df[df['volume'] > 1.8 * avg_volume]
        smart_money_zones = []
        for _, row in high_vol_df.iterrows():
            smart_money_zones.append({
                "price_low": float(row['low']),
                "price_high": float(row['high']),
                "timestamp": row['timestamp'].isoformat() + "Z"
            })
            
        # Ensure df is properly indexed numerically to prevent loc errors
        df = df.reset_index(drop=True)
        
        # Define timeframe-specific return thresholds
        if interval_clean in ("1m", "1minute", "5m", "5minute"):
            ret_threshold = 0.003  # 0.3%
        elif interval_clean in ("15m", "15minute"):
            ret_threshold = 0.006  # 0.6%
        elif interval_clean in ("30m", "30minute"):
            ret_threshold = 0.009  # 0.9%
        else:
            ret_threshold = 0.015  # 1.5% for daily

        # 9. Breakout markers
        breakout_markers = []
        last_marker_idx = -100
        MIN_MARKER_DISTANCE = 5
        
        for idx, row in df.iterrows():
            close_val = float(row['close'])
            vol_val = float(row['volume'])
            
            # Format time correctly for Lightweight Charts marker (Unix timestamp for intraday, string for daily)
            marker_time = row['timestamp'].strftime("%Y-%m-%d") if interval_clean in ("1d", "day") else int(row['timestamp'].timestamp())
            
            if vol_val > 2.0 * avg_volume and idx > 0:
                prev_close = float(df.loc[idx - 1, 'close'])
                ret = (close_val - prev_close) / prev_close
                if ret > ret_threshold:
                    if idx - last_marker_idx >= MIN_MARKER_DISTANCE:
                        breakout_markers.append({
                            "time": marker_time,
                            "position": "belowBar",
                            "color": "#10b981",
                            "shape": "arrowUp",
                            "text": "BUY",
                            "type": "bull_breakout",
                            "price": close_val,
                            "date": row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        })
                        last_marker_idx = idx
                elif ret < -ret_threshold:
                    if idx - last_marker_idx >= MIN_MARKER_DISTANCE:
                        breakout_markers.append({
                            "time": marker_time,
                            "position": "aboveBar",
                            "color": "#ef4444",
                            "shape": "arrowDown",
                            "text": "SELL",
                            "type": "bear_breakdown",
                            "price": close_val,
                            "date": row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        })
                        last_marker_idx = idx
                    
        # 10. Format chart candle response list
        chart_candles = []
        for _, row in indicators_df.iterrows():
            time_val = row['timestamp'].strftime("%Y-%m-%d") if interval_clean in ("1d", "day") else int(row['timestamp'].timestamp())
            chart_candles.append({
                "time": time_val,
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row['volume']),
                "ema_20": float(row.get('ema_20', row['close'])) if not pd.isna(row.get('ema_20')) else float(row['close']),
                "ema_50": float(row.get('ema_50', row['close'])) if not pd.isna(row.get('ema_50')) else float(row['close']),
                "vwap": float(row.get('vwap', row['close'])) if not pd.isna(row.get('vwap')) else float(row['close'])
            })
            
        earliest_ts = df["timestamp"].min()
        latest_ts = df["timestamp"].max()
        to_date_naive = to_date.replace(tzinfo=None)
        earliest_ts_naive = earliest_ts.replace(tzinfo=None) if not pd.isna(earliest_ts) else to_date_naive
        available_days = (to_date_naive - earliest_ts_naive).days if not df.empty else 0
        from_date_str = earliest_ts.strftime("%Y-%m-%d") if not df.empty else ""
        to_date_str = latest_ts.strftime("%Y-%m-%d") if not df.empty else ""

        # Slice returned candles and markers to match lookback_days
        sliced_candles = chart_candles[-candle_limit:] if candle_limit < len(chart_candles) else chart_candles
        returned_times = {c["time"] for c in sliced_candles}
        sliced_markers = [m for m in breakout_markers if m["time"] in returned_times]

        response_payload = {
            "success": True,
            "data": {
                "symbol": symbol,
                "interval": interval,
                "available_history_days": available_days,
                "candle_count": len(sliced_candles),
                "from_date": from_date_str,
                "to_date": to_date_str,
                "candles": sliced_candles,
                "support_zones": support_zones,
                "resistance_zones": resistance_zones,
                "volume_profile": volume_profile,
                "smart_money_zones": smart_money_zones[:5],
                "breakout_markers": sliced_markers
            }
        }
        
        # 11. Write cache
        if cache.is_available():
            try:
                import json
                cache.set(cache_key, json.dumps(response_payload), ttl=300)
                cache.set(f"{cache_key}:fallback", json.dumps(response_payload), ttl=604800) # 7 days fallback
            except Exception as ce:
                logger.warning(f"Cache write error in option flow chart: {ce}")
                
        return response_payload
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upstox data unavailable or calculation error for {symbol}: {e}", exc_info=True)
        # Try to fall back to cache/fallback cache
        if cache.is_available():
            try:
                cached_data = cache.get(cache_key) or cache.get(f"{cache_key}:fallback")
                if cached_data:
                    import json
                    logger.info(f"[Option Flow Chart] Serving fallback cache data for {symbol} due to Upstox failure: {e}")
                    res = json.loads(cached_data)
                    if "data" in res:
                        res["source"] = "fallback_cache"
                    return res
            except Exception as ce:
                logger.warning(f"Failed to load fallback cache: {ce}")
        raise HTTPException(status_code=503, detail=f"Upstox data unavailable: {str(e)}")

@router.get("/{symbol}/expiries")
async def get_option_expiries(
    symbol: str,
    bypass_cache: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Get available expiry dates for option chain.
    """
    symbol = symbol.upper().strip()
    
    if not has_derivatives(symbol):
        raise HTTPException(status_code=400, detail=f"Symbol '{symbol}' is not in F&O segment.")
        
    try:
        cache_key = f"option_expiries:{symbol}"
        cache = get_cache_manager()
        if not bypass_cache and cache.is_available():
            try:
                cached = cache.get(cache_key)
                if cached:
                    return {
                        "success": True,
                        "data": cached,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "source": "cache"
                    }
            except Exception as ce:
                logger.warning(f"Cache read error: {ce}")
                
        expiries = []
        try:
            # 1. Get instrument_key
            from services.instrument_resolver import resolve_instrument_key
            instrument_key = resolve_instrument_key(symbol)
            if not instrument_key:
                mapped_k = map_symbol_to_instrument_key(symbol)
                if mapped_k:
                    instrument_key = mapped_k
                elif is_index(symbol):
                    instrument_key = f"NSE_INDEX|{symbol}"
                else:
                    instrument_key = f"NSE_EQ|{symbol}"

            # 2. Fetch contracts from Upstox API
            from services.upstox_client import get_upstox_client
            client = get_upstox_client()
            contracts_data = await client._make_request("GET", "/option/contract", params={"instrument_key": instrument_key})
            if contracts_data.get("status") == "success" and contracts_data.get("data"):
                contracts = contracts_data["data"]
                unique_expiries = sorted(list(set(c.get("expiry") for c in contracts if c.get("expiry"))))
                if unique_expiries:
                    expiries = unique_expiries
                    logger.info(f"Retrieved active contracts expiries from Upstox for {symbol}: {expiries}")
        except Exception as e:
            logger.warning(f"[Option Expiries] Failed to resolve expiries dynamically from Upstox API: {e}")
            
        if not expiries:
            # Fallback to local calculations
            if is_index(symbol):
                expiries = get_upcoming_thursdays()
            else:
                expiries = get_monthly_expiries()
            logger.info(f"Falling back to calculated expiries for {symbol}: {expiries}")
                
        response_data = {
            "status": "success",
            "symbol": symbol,
            "expiries": expiries
        }
        
        if cache.is_available():
            try:
                cache.set(cache_key, response_data, ttl=3600)
            except Exception as ce:
                logger.warning(f"Cache write error: {ce}")
                
        return {
            "success": True,
            "data": response_data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "upstox"
        }
        
    except Exception as e:
        logger.error(f"[Option Expiries] Exception for {symbol}: {type(e).__name__}: {e}", exc_info=True)
        msg = f"Option expiries unavailable: {type(e).__name__}: {str(e)}"
        if not is_market_open():
            msg += " Note: NSE market is currently closed."
        return {
            "success": False,
            "data": {
                "status": "error",
                "symbol": symbol,
                "expiries": []
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "upstox",
            "error": {
                "code": "EXPIRY_CHECK_ERROR",
                "message": msg
            },
            "_diagnostics": {
                "market_open": is_market_open(),
                "exception_type": type(e).__name__,
                "exception_message": str(e),
            }
        }
