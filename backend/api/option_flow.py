from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

from database import get_read_db
from models import User
from utils.auth import get_current_user
from services.cache import get_cache_manager
from data.fno_stocks import has_derivatives, is_index
from services.upstox_client import get_upstox_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Option Flow"])

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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Get option flow and chain metrics for a symbol.
    """
    symbol = symbol.upper().strip()
    
    if not has_derivatives(symbol):
        raise HTTPException(status_code=400, detail=f"Symbol '{symbol}' is not available in the F&O segment.")
        
    try:
        cache_key = f"option_flow:{symbol}:{expiry or 'nearest'}:{strike_range or 'all'}"
        cache = get_cache_manager()
        if cache.is_available():
            try:
                cached = cache.get(cache_key)
                if cached:
                    return cached
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
            return {
                "status": "error",
                "symbol": symbol,
                "message": "Option chain data temporarily unavailable from broker.",
                "data": None
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
        
        # Calculate lot size fallback or lookup
        # In Indian markets, lot sizes are typically between 100 and 10000.
        # If lot size is not specified, we can use 1 for Premium calculation as a index/multiplier
        # but let's show notional premium = LTP * Volume.
        
        active_expiry = expiry
        
        for item in raw_strikes:
            strike_price = float(item.get("strike_price", 0))
            
            call = item.get("call_options", {})
            put = item.get("put_options", {})
            
            if not active_expiry:
                active_expiry = call.get("expiry") or put.get("expiry")
                
            call_market = call.get("market_data", {}) if call else {}
            put_market = put.get("market_data", {}) if put else {}
            
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
        # Indian options typically have lot sizes. Since notional premium turnover = LTP * Volume,
        # we can flag strikes where call or put premium exceeds 1,000,000.
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
        
        # Cache for 15s (very dynamic)
        if cache.is_available():
            try:
                cache.set(cache_key, response_data, ttl=15)
            except Exception as ce:
                logger.warning(f"Cache write error in option flow: {ce}")
                
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Option Flow API: {e}", exc_info=True)
        return {
            "status": "error",
            "symbol": symbol,
            "message": f"Option chain data temporarily unavailable from broker: {str(e)}",
            "data": None
        }

@router.get("/{symbol}/expiries")
async def get_option_expiries(
    symbol: str,
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
        if cache.is_available():
            try:
                cached = cache.get(cache_key)
                if cached:
                    return cached
            except Exception as ce:
                logger.warning(f"Cache read error: {ce}")
                
        # Try fetching live option chain first to extract available expiries
        # Some brokers return expiries in metadata. If not, we can fall back to calculations
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
            # Upstox returns expiry dates when we query without expiry
            # We can extract them from the options list
            response = await client._make_request("GET", "/option/chain", params={"instrument_key": instrument_key})
            if response.get("status") == "success" and response.get("data"):
                strikes = response["data"]
                unique_expiries = set()
                for item in strikes:
                    c_exp = item.get("call_options", {}).get("expiry")
                    p_exp = item.get("put_options", {}).get("expiry")
                    if c_exp: unique_expiries.add(c_exp)
                    if p_exp: unique_expiries.add(p_exp)
                expiries = sorted(list(unique_expiries))
        except Exception as e:
            logger.debug(f"Failed to fetch live expiries from option chain for {symbol}: {e}")
            
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
                
        return response_data
        
    except Exception as e:
        logger.error(f"Error in Option Expiries API: {e}", exc_info=True)
        return {
            "status": "error",
            "symbol": symbol,
            "message": f"Option expiries temporarily unavailable: {str(e)}",
            "expiries": []
        }
