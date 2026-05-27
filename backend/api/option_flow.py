from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, time, timedelta
import pytz

from database import get_read_db
from models import User
from utils.auth import get_current_user
from services.cache import get_cache_manager
from data.fno_stocks import has_derivatives, is_index
from services.upstox_client import get_upstox_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Option Flow"])

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
    Get option flow and chain metrics for a symbol.
    """
    symbol = symbol.upper().strip()
    
    if not has_derivatives(symbol):
        raise HTTPException(status_code=400, detail=f"Symbol '{symbol}' is not available in the F&O segment.")
        
    if not expiry:
        try:
            if is_index(symbol):
                calculated_exp = get_upcoming_thursdays()
            else:
                calculated_exp = get_monthly_expiries()
            if calculated_exp:
                expiry = calculated_exp[0]
        except Exception as ee:
            logger.warning(f"Failed to resolve default expiry for {symbol}: {ee}")

    try:
        cache_key = f"option_flow:{symbol}:{expiry or 'nearest'}:{strike_range or 'all'}"
        cache = get_cache_manager()
        if not bypass_cache and cache.is_available():
            try:
                cached = cache.get(cache_key)
                if cached:
                    logger.info(f"Serving option flow for {symbol} from cache")
                    return {
                        "success": True,
                        "data": cached,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "source": "cache"
                    }
                # Outside market hours, if we have fallback cache, serve it immediately
                if not is_market_open():
                    fallback = cache.get(f"{cache_key}:fallback")
                    if fallback:
                        logger.info(f"Serving stale option flow for {symbol} outside market hours")
                        return {
                            "success": True,
                            "data": fallback,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "source": "stale_cache",
                            "_diagnostics": {
                                "reason": "market_closed_direct_fallback",
                                "market_open": False
                            }
                        }
            except Exception as ce:
                logger.warning(f"Cache read error in option flow: {ce}")
                
        # Get instrument_key
        symbol_query = text("""
            SELECT instrument_key, exchange
            FROM instrument_master
            WHERE symbol = :symbol AND is_active = TRUE
            LIMIT 1
        """)
        symbol_res = await db.execute(symbol_query, {"symbol": symbol})
        symbol_row = symbol_res.fetchone()
        
        if not symbol_row:
            # Fallback for indices which might not be in instrument_master
            if is_index(symbol):
                instrument_key = f"NSE_INDEX|{symbol}"
            else:
                raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found in active master.")
        else:
            instrument_key = symbol_row.instrument_key

        client = get_upstox_client()
        params = {"instrument_key": instrument_key}
        if expiry:
            params["expiry_date"] = expiry
            
        # Call Upstox option chain API
        response = await client._make_request("GET", "/option/chain", params=params)
        
        if response.get("status") != "success" or not response.get("data"):
            logger.warning(
                f"[Option Flow] Upstox API non-success for {symbol}: "
                f"status={response.get('status')}, data_present={bool(response.get('data'))}, "
                f"response_keys={list(response.keys())}"
            )
            # Attempt stale-cache fallback
            if cache.is_available():
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
                                "api_status": response.get("status"),
                                "api_message": response.get("message", ""),
                            }
                        }
                except Exception as sce:
                    logger.debug(f"[Option Flow] Stale cache read failed: {sce}")

            api_status = response.get("status", "unknown")
            api_message = response.get("message", "")
            msg = f"No option chain data available from Upstox currently for {symbol}. API status: {api_status}."
            if api_message:
                msg += f" Message: {api_message}"
            if not is_market_open():
                msg += " Note: NSE market is currently closed \u2013 data may reflect last closing session."
            return {
                "success": False,
                "data": None,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "upstox",
                "error": {
                    "code": "BROKER_UNAVAILABLE",
                    "message": msg
                },
                "_diagnostics": {
                    "market_open": is_market_open(),
                    "api_status": api_status,
                    "api_message": api_message,
                    "token_present": bool(client.access_token),
                    "instrument_key": instrument_key,
                }
            }
            
        raw_strikes = response["data"]
        
        # Parse strikes
        strikes_list = []
        total_call_oi = 0
        total_put_oi = 0
        total_call_vol = 0
        total_put_vol = 0
        total_call_premium = 0.0
        total_put_premium = 0.0
        
        active_expiry = expiry
        
        for item in raw_strikes:
            if not item:
                continue
            strike_price = float(item.get("strike_price", 0) or 0)
            if strike_price <= 0:
                continue
            
            call = item.get("call_options") or {}
            put = item.get("put_options") or {}
            
            # Log missing CE/PE options separately
            if not item.get("call_options"):
                logger.warning(f"[Option Flow] Symbol {symbol}: Strike {strike_price} is missing Call (CE) options")
            if not item.get("put_options"):
                logger.warning(f"[Option Flow] Symbol {symbol}: Strike {strike_price} is missing Put (PE) options")
            
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
            
            # Premium turnover = Volume * LTP
            c_premium = c_vol * c_ltp
            p_premium = p_vol * p_ltp
            
            total_call_oi += c_oi
            total_put_oi += p_oi
            total_call_vol += c_vol
            total_put_vol += p_vol
            total_call_premium += c_premium
            total_put_premium += p_premium
            
            # Call details
            call_data = {
                "oi": c_oi,
                "oi_change": int(call_market.get("oi_change", 0) or 0),
                "volume": c_vol,
                "ltp": c_ltp,
                "bid": float(call_market.get("bid_price", 0) or 0),
                "ask": float(call_market.get("ask_price", 0) or 0),
                "premium": round(c_premium, 2),
                "iv": round(float(call_market.get("iv", 0) or 0) * 100, 2)
            }
            
            # Put details
            put_data = {
                "oi": p_oi,
                "oi_change": int(put_market.get("oi_change", 0) or 0),
                "volume": p_vol,
                "ltp": p_ltp,
                "bid": float(put_market.get("bid_price", 0) or 0),
                "ask": float(put_market.get("ask_price", 0) or 0),
                "premium": round(p_premium, 2),
                "iv": round(float(put_market.get("iv", 0) or 0) * 100, 2)
            }
            
            strikes_list.append({
                "strike_price": strike_price,
                "call": call_data,
                "put": put_data
            })
            
        # Sort strikes
        strikes_list = sorted(strikes_list, key=lambda x: x["strike_price"])
        
        # Calculate PCR (Put-Call Ratio)
        pcr_oi = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0
        pcr_vol = round(total_put_vol / total_call_vol, 2) if total_call_vol > 0 else 0.0
        
        net_flow = total_call_premium - total_put_premium
        buy_sell_ratio = round(total_call_premium / total_put_premium, 2) if total_put_premium > 0 else 1.0
        
        # Sentiment
        if pcr_oi > 1.2:
            sentiment = "Bullish"
        elif pcr_oi < 0.7:
            sentiment = "Bearish"
        else:
            sentiment = "Neutral"
            
        # Detect Institutional Block Deals (> ₹10L Premium Turnover in a single option contract)
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
                
        # Sort block deals by premium descending
        block_deals = sorted(block_deals, key=lambda x: x["premium"], reverse=True)
        
        response_data = {
            "status": "success",
            "symbol": symbol,
            "expiry": active_expiry,
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
            "strikes": strikes_list,
            "block_deals": block_deals
        }
        
        # Cache for 15s (very dynamic) and fallback cache for 7 days
        if cache.is_available():
            try:
                cache.set(cache_key, response_data, ttl=15)
                cache.set(f"{cache_key}:fallback", response_data, ttl=604800) # 7 days
            except Exception as ce:
                logger.warning(f"Cache write error in option flow: {ce}")
                
        return {
            "success": True,
            "data": response_data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "upstox"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Option Flow] Exception for {symbol}: {type(e).__name__}: {e}", exc_info=True)
        # Attempt stale-cache fallback
        try:
            if cache.is_available():
                stale = cache.get(cache_key) or cache.get(f"{cache_key}:fallback")
                if stale:
                    logger.info(f"[Option Flow] Serving stale cache for {symbol} after exception")
                    return {
                        "success": True,
                        "data": stale,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "source": "stale_cache",
                        "_diagnostics": {
                            "reason": "exception_fallback",
                            "error": str(e),
                            "market_open": is_market_open(),
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
        # Check cache
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
                
        # Try fetching live option chain first to extract available expiries
        expiries = []
        try:
            symbol_query = text("""
                SELECT instrument_key
                FROM instrument_master
                WHERE symbol = :symbol AND is_active = TRUE
                LIMIT 1
            """)
            symbol_res = await db.execute(symbol_query, {"symbol": symbol})
            symbol_row = symbol_res.fetchone()
            instrument_key = symbol_row.instrument_key if symbol_row else f"NSE_INDEX|{symbol}"
            
            client = get_upstox_client()
            response = await client._make_request("GET", "/option/chain", params={"instrument_key": instrument_key})
            if response.get("status") == "success" and response.get("data"):
                strikes = response["data"]
                unique_expiries = set()
                for item in strikes:
                    if not item:
                        continue
                    c_exp = (item.get("call_options") or {}).get("expiry")
                    p_exp = (item.get("put_options") or {}).get("expiry")
                    if c_exp: unique_expiries.add(c_exp)
                    if p_exp: unique_expiries.add(p_exp)
                expiries = sorted(list(unique_expiries))
                logger.info(f"[Option Expiries] Found {len(expiries)} expiry dates for {symbol} from live API")
        except Exception as e:
            logger.warning(f"[Option Expiries] Failed to fetch live expiries for {symbol}: {type(e).__name__}: {e}")
            
        # Fallback to calculated dates if live retrieval failed
        if not expiries:
            if is_index(symbol):
                expiries = get_upcoming_thursdays()
            else:
                expiries = get_monthly_expiries()
                
        response_data = {
            "status": "success",
            "symbol": symbol,
            "expiries": expiries
        }
        
        # Cache for 1 hour (expiries don't change frequently during the day)
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
