from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import numpy as np
import pandas as pd
from typing import Dict, Any
import logging
from datetime import datetime, date

from database import get_read_db
from models import User
from utils.auth import get_current_user
from services.cache import get_cache_manager
from data.fno_stocks import has_derivatives

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Volatility"])

def generate_investor_summary(
    iv: float,
    hv: float,
    iv_rank: float,
    iv_percentile: float,
    volatility_regime: str,
    mean_reversion_score: float,
    price_change_pct: float = 0.0,
    symbol: str = "Stock"
) -> Dict[str, Any]:
    """
    Translates complex volatility technical indicators into simple plain-English actions for retail investors.
    """
    reasons = []
    
    # 1. Translate IV / HV Relationship
    if iv < hv:
        reasons.append("The options market expects lower future volatility than recent history.")
    else:
        reasons.append("The options market expects larger price swings ahead.")
        
    # 2. Translate IV Rank
    if iv_rank > 70:
        reasons.append("Options are relatively expensive compared to the past year.")
    elif iv_rank < 30:
        reasons.append("Options are relatively cheap compared to the past year.")
    else:
        reasons.append("Options are priced fairly compared to the past year.")
        
    # 3. Translate Mean Reversion
    if mean_reversion_score >= 60:
        reasons.append("Volatility may move back toward its long-term average.")
    elif mean_reversion_score <= 40:
        reasons.append("Volatility is low and could expand in the near future.")
        
    # 4. Volatility Regime status
    reasons.append(f"Volatility regime is {volatility_regime}.")
    
    # Determine Action, Risk Level, Summary
    # STRONG BUY
    if "low" in volatility_regime.lower() and iv_rank < 30 and price_change_pct >= 0:
        action = "STRONG BUY"
        risk_level = "Low"
        summary = f"{symbol} appears attractively priced from a volatility perspective. Low volatility and low option pricing suggest an excellent entry point with low risk."
    # WAIT FOR BETTER ENTRY / AVOID
    elif iv_rank > 85 or ("high" in volatility_regime.lower() and iv_rank > 80):
        action = "WAIT FOR BETTER ENTRY"
        risk_level = "High"
        summary = f"Current conditions suggest waiting for volatility to cool down. {symbol} is experiencing high volatility and option pricing, indicating elevated speculation."
    # SELL
    elif "high" in volatility_regime.lower() and price_change_pct < 0:
        action = "SELL"
        risk_level = "High"
        summary = f"Risk has increased and downside pressure is building for {symbol}. Elevated volatility coupled with negative price momentum suggests caution."
    # BUY
    elif "normal" in volatility_regime.lower() and price_change_pct >= 0 and iv_rank <= 65:
        action = "BUY"
        risk_level = "Moderate"
        summary = f"Conditions remain favorable for gradual accumulation of {symbol}. Volatility is stable and trading within historical norms."
    # HOLD (Fallback / Mixed)
    else:
        action = "HOLD"
        risk_level = "Moderate"
        summary = f"There is no strong buy or sell signal currently for {symbol}. Volatility metrics are in a neutral consolidated range."
        
    # Calculate Confidence Score (0-100%)
    base_conf = 60
    if "low" in volatility_regime.lower() or "high" in volatility_regime.lower():
        base_conf += 10
    if iv_rank < 30 or iv_rank > 80:
        base_conf += 10
    if iv_percentile < 25 or iv_percentile > 75:
        base_conf += 5
    if mean_reversion_score > 65 or mean_reversion_score < 35:
        base_conf += 5
    if abs(iv - hv) / max(1.0, hv) > 0.15:
        base_conf += 5
        
    confidence = min(95, max(45, base_conf))
    
    return {
        "action": action,
        "confidence": confidence,
        "risk_level": risk_level,
        "summary": summary,
        "reasons": reasons
    }

@router.get("/{symbol}")
async def get_volatility_data(
    symbol: str,
    lookback_days: int = Query(30, ge=5, le=60),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Get comprehensive volatility analysis for a stock.
    Returns: India VIX, Historical Volatility, IV/HV Rank, IV/HV Percentile, ATR, 
             Regime signals, and historical time series for charting.
    """
    symbol = symbol.upper().strip()
    
    try:
        # Check cache first
        cache_key = f"volatility:{symbol}:{lookback_days}"
        cache = get_cache_manager()
        if cache.is_available():
            try:
                cached = cache.get(cache_key)
                if cached:
                    return cached
            except Exception as ce:
                logger.warning(f"Cache read error in volatility: {ce}")
        
        # 1. Verify symbol exists in instrument_master
        from services.instrument_resolver import resolve_instrument_info
        info = resolve_instrument_info(symbol)
        
        if not info or not info.is_active:
            raise HTTPException(status_code=404, detail=f"Active stock symbol '{symbol}' not found.")
        
        instrument_id = info.instrument_id
        instrument_key = info.instrument_key
        company_name = info.company_name
        sector = info.sector
        exchange = info.exchange
        
        # 2. Fetch last 280 daily candles from DB for calculations (needs 252 for 1 year + margin)
        candles_query = text("""
            SELECT candle_ts::date as date, open, high, low, close, volume
            FROM stock_candle
            WHERE instrument_id = :instrument_id AND timeframe = 1440
            ORDER BY candle_ts DESC
            LIMIT 280
        """)
        candles_res = await db.execute(candles_query, {"instrument_id": instrument_id})
        candles_rows = candles_res.fetchall()
        
        # Reverse to chronological order for calculations
        candles_rows = list(reversed(candles_rows))
        
        # Fallback: if no DB candles, do NOT fetch from Upstox API (disabled)
        if len(candles_rows) < 10:
            logger.warning(f"Insufficient DB candles for {symbol} (count={len(candles_rows)}), Upstox REST API fallback disabled")
                
        if len(candles_rows) < 5:
            # We don't have enough data
            return {
                "status": "error",
                "symbol": symbol,
                "message": "Data unavailable. Insufficient historical price data to compute volatility.",
                "data": None
            }

        df = pd.DataFrame([{
            'date': r.date,
            'open': float(r.open) if r.open is not None else 0.0,
            'high': float(r.high) if r.high is not None else 0.0,
            'low': float(r.low) if r.low is not None else 0.0,
            'close': float(r.close) if r.close is not None else 0.0,
            'volume': int(r.volume) if r.volume is not None else 0
        } for r in candles_rows])
        
        # Inject live/EOD price from PriceService to construct today's session candle
        try:
            from services.price_manager import get_price_service
            from services.market_hours_service import get_market_hours_service
            
            price_svc = get_price_service()
            price_res = await price_svc.get_price(symbol)
            
            if price_res and price_res.get("ltp") and price_res.get("ltp") > 0:
                ltp = float(price_res["ltp"])
                prev_close = float(price_res.get("previous_close") or df['close'].iloc[-1])
                
                market_hours = get_market_hours_service()
                today_date_str = market_hours.get_trading_date()
                today_date = date.fromisoformat(today_date_str)
                
                last_date = df['date'].iloc[-1]
                
                if last_date < today_date:
                    # Construct a new daily candle for today's session
                    open_p = prev_close
                    high_p = max(prev_close, ltp)
                    low_p = min(prev_close, ltp)
                    close_p = ltp
                    
                    new_row = pd.DataFrame([{
                        'date': today_date,
                        'open': open_p,
                        'high': high_p,
                        'low': low_p,
                        'close': close_p,
                        'volume': 0
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                else:
                    # Today's candle is already in the database, update its close with the live LTP
                    df.loc[df.index[-1], 'close'] = ltp
                    df.loc[df.index[-1], 'high'] = max(df.loc[df.index[-1], 'high'], ltp)
                    df.loc[df.index[-1], 'low'] = min(df.loc[df.index[-1], 'low'], ltp)
        except Exception as e:
            logger.warning(f"Failed to enrich volatility calculations with live price: {e}")
        
        # 3. Compute log returns & historical volatility
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # Compute rolling annualized volatility (252 trading days in a year)
        # 30-day HV is standard, but we use lookback_days
        df['hv'] = df['log_return'].rolling(window=lookback_days).std() * np.sqrt(252) * 100
        
        # ATR (Average True Range) - 14 period
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = (df['high'] - df['close'].shift(1)).abs()
        df['tr3'] = (df['low'] - df['close'].shift(1)).abs()
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # Latest calculated values
        latest_price = float(df['close'].iloc[-1])
        latest_change_pct = float(((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100) if len(df) > 1 else 0.0
        latest_hv = float(df['hv'].iloc[-1]) if not pd.isna(df['hv'].iloc[-1]) else 0.0
        latest_atr = float(df['atr'].iloc[-1]) if not pd.isna(df['atr'].iloc[-1]) else 0.0
        
        # If HV calculation is NaN, fallback to standard deviation of whatever we have
        if latest_hv == 0.0 and len(df) > 1:
            valid_returns = df['log_return'].dropna()
            if len(valid_returns) > 1:
                latest_hv = float(valid_returns.std() * np.sqrt(252) * 100)
        
        # 4. Fetch Option Chain / IV from Dragonfly Cache if F&O stock
        current_iv = 0.0
        is_fno = has_derivatives(symbol)
        
        if is_fno:
            try:
                # Retrieve from cache instead of Upstox API
                import json
                cache_keys = [
                    f"option_chain:{symbol}",
                    f"option_chain:{instrument_key}"
                ]
                strikes = []
                cache = get_cache_manager()
                for key in cache_keys:
                    cached_val = cache.get(key)
                    if cached_val:
                        if isinstance(cached_val, str):
                            try:
                                strikes = json.loads(cached_val)
                            except Exception:
                                strikes = cached_val
                        else:
                            strikes = cached_val
                        if isinstance(strikes, dict) and "data" in strikes:
                            strikes = strikes["data"]
                        if strikes:
                            break
                
                if strikes:
                    # Find closest strike to latest price (ATM)
                    closest_strike = min(strikes, key=lambda s: abs(float(s.get("strike_price", 0)) - latest_price))
                    call_opt = closest_strike.get("call_options") or {}
                    put_opt = closest_strike.get("put_options") or {}
                    call_market = call_opt.get("market_data") or {}
                    put_market = put_opt.get("market_data") or {}
                    call_greeks = call_opt.get("option_greeks") or {}
                    put_greeks = put_opt.get("option_greeks") or {}
                    
                    call_iv = call_greeks.get("iv", 0) or call_market.get("iv", 0) or 0
                    put_iv = put_greeks.get("iv", 0) or put_market.get("iv", 0) or 0
                    iv_list = [v for v in [call_iv, put_iv] if v and v > 0]
                    if iv_list:
                        mean_iv = float(np.mean(iv_list))
                        current_iv = mean_iv * 100.0 if 0.0 < mean_iv < 1.0 else mean_iv
            except Exception as e:
                logger.debug(f"Could not retrieve IV from cached option chain for {symbol}: {e}")
        
        # If we couldn't get live IV, or it is non-F&O, we use Historical Volatility as the volatility metric
        if current_iv == 0.0:
            current_iv = latest_hv
            
        # 5. Compute 52-Week Volatility Rank and Percentile (IV/HV Rank and Percentile)
        # We use the rolling HV series over the last 252 days as the reference
        hv_series = df['hv'].dropna().tolist()
        if not hv_series:
            # Fallback series based on rolling returns
            hv_series = [latest_hv]
            
        min_hv = min(hv_series)
        max_hv = max(hv_series)
        
        if max_hv > min_hv:
            iv_rank = ((current_iv - min_hv) / (max_hv - min_hv)) * 100
        else:
            iv_rank = 50.0 # Neutral fallback
            
        # Percentile: % of days where volatility was less than current volatility
        less_than_count = sum(1 for v in hv_series if v < current_iv)
        iv_percentile = (less_than_count / len(hv_series)) * 100 if hv_series else 50.0
        
        # 6. Volatility Regime Signal & Mean Reversion Probability
        # Compare current HV to historical mean and stddev
        hv_mean = np.mean(hv_series)
        hv_std = np.std(hv_series) if len(hv_series) > 1 else 1.0
        if hv_std == 0:
            hv_std = 1.0
            
        z_score = (current_iv - hv_mean) / hv_std
        
        if z_score > 1.0:
            regime_signal = "High Volatility"
            # High volatility indicates high probability of reversion to mean (crushing)
            mean_reversion_prob = min(95.0, 50.0 + abs(z_score) * 15.0)
        elif z_score < -1.0:
            regime_signal = "Low Volatility"
            # Low volatility implies consolidation, likely to expand (low reversion probability, high expansion probability)
            mean_reversion_prob = max(10.0, 50.0 - abs(z_score) * 15.0)
        else:
            regime_signal = "Normal Volatility"
            mean_reversion_prob = 50.0
            
        # 7. Fetch India VIX (from index_master or live Upstox NIFTY VIX)
        india_vix = 15.0 # standard fallback
        try:
            # Check database for VIX candle using cached instrument_id
            from services.instrument_resolver import resolve_instrument_id
            vix_iid = resolve_instrument_id("INDIA VIX", series="EQ", exchange="NSE")
            if vix_iid:
                vix_query = text("""
                    SELECT close
                    FROM stock_candle
                    WHERE instrument_id = :iid AND timeframe = 1440
                    ORDER BY candle_ts DESC
                    LIMIT 1
                """)
                vix_res = await db.execute(vix_query, {"iid": vix_iid})
            else:
                vix_query = text("""
                    SELECT close
                    FROM stock_candle sc
                    JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                    WHERE im.symbol = 'INDIA VIX' AND sc.timeframe = 1440
                    ORDER BY sc.candle_ts DESC
                    LIMIT 1
                """)
                vix_res = await db.execute(vix_query)
            vix_row = vix_res.fetchone()
            if vix_row:
                india_vix = float(vix_row.close)
            else:
                # Try fetching resolved price for India VIX index via centralized PriceService
                from services.price_manager import get_price_service
                price_svc = get_price_service()
                p_res = await price_svc.get_price("INDIA VIX")
                if p_res and p_res.get("ltp"):
                    india_vix = float(p_res["ltp"])
        except Exception as vix_err:
            logger.debug(f"Failed to fetch India VIX: {vix_err}")
            
        # 8. Build historical time series for the chart (last lookback_days)
        chart_data = []
        chart_slice = df.tail(lookback_days)
        for _, row in chart_slice.iterrows():
            if not pd.isna(row['hv']):
                chart_data.append({
                    "date": row['date'].strftime("%Y-%m-%d") if isinstance(row['date'], (datetime, date)) else str(row['date']),
                    "price": round(float(row['close']), 2),
                    "volatility": round(float(row['hv']), 2),
                    "atr": round(float(row['atr']), 2) if not pd.isna(row['atr']) else 0.0
                })
        
        # Generate simple retail investor summary
        investor_summary = generate_investor_summary(
            iv=current_iv,
            hv=latest_hv,
            iv_rank=iv_rank,
            iv_percentile=iv_percentile,
            volatility_regime=regime_signal,
            mean_reversion_score=mean_reversion_prob,
            price_change_pct=latest_change_pct,
            symbol=symbol
        )
        
        response_data = {
            "status": "success",
            "symbol": symbol,
            "company_name": company_name,
            "sector": sector,
            "exchange": exchange,
            "is_fno": is_fno,
            "latest_price": round(latest_price, 2),
            "price_change_pct": round(latest_change_pct, 2),
            "india_vix": round(india_vix, 2),
            "historical_volatility": round(latest_hv, 2),
            "implied_volatility": round(current_iv, 2),
            "iv_rank": round(iv_rank, 2),
            "iv_percentile": round(iv_percentile, 2),
            "atr": round(latest_atr, 2),
            "regime": regime_signal,
            "mean_reversion_probability": round(mean_reversion_prob, 2),
            "time_series": chart_data,
            "investor_summary": investor_summary
        }
        
        # Set cache (30s TTL for real-time feel)
        if cache.is_available():
            try:
                cache.set(cache_key, response_data, ttl=30)
            except Exception as ce:
                logger.warning(f"Cache write error in volatility: {ce}")
                
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Volatility API: {e}", exc_info=True)
        return {
            "status": "error",
            "symbol": symbol,
            "message": f"Volatility analytics temporarily unavailable: {str(e)}",
            "data": None
        }
