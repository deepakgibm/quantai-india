from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from database import get_read_db
from models import User
from utils.auth import get_current_user
from services.cache import get_cache_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Volume Profile"])

from core.scanner import indicator_utils


def clean_float(val: Any) -> Optional[float]:
    """
    Cleans float values to ensure they do not leak NaN/Inf values
    which are incompatible with JSON serialization.
    """
    if val is None or pd.isna(val):
        return None
    try:
        f_val = float(val)
        if math.isnan(f_val) or math.isinf(f_val):
            return None
        return f_val
    except (ValueError, TypeError):
        return None


def calculate_volume_profile(df: pd.DataFrame, num_bins: int = 50) -> Dict[str, Any]:
    """
    Core algorithm: Approximate Volume Profile by distributing candle volume
    proportionally across overlapping price bins.
    """
    if df.empty:
        return {
            "poc": 0.0, "vah": 0.0, "val": 0.0,
            "hvn": [], "lvn": [], "shape": "D-shape (Balanced)",
            "histogram": []
        }
        
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    volumes = df["volume"].values
    
    p_min = float(np.min(lows))
    p_max = float(np.max(highs))
    
    if p_max == p_min:
        p_max += 1.0
        
    w = (p_max - p_min) / num_bins
    bin_volumes = np.zeros(num_bins)
    bin_ranges = [(p_min + i * w, p_min + (i + 1) * w) for i in range(num_bins)]
    
    # Distribute volume proportionally
    for L, H, C, V in zip(lows, highs, closes, volumes):
        if H > L:
            for i in range(num_bins):
                b_low, b_high = bin_ranges[i]
                overlap = max(0.0, min(H, b_high) - max(L, b_low))
                prop = overlap / (H - L)
                bin_volumes[i] += V * prop
        else:
            idx = int(min(num_bins - 1, max(0, (C - p_min) // w)))
            bin_volumes[idx] += V
            
    # Point of Control (POC)
    poc_idx = int(np.argmax(bin_volumes))
    poc_price = p_min + (poc_idx + 0.5) * w
    
    # Value Area (70% Volume)
    total_vol = float(np.sum(bin_volumes))
    target_vol = 0.70 * total_vol
    
    i_low = poc_idx
    i_high = poc_idx
    accum_vol = float(bin_volumes[poc_idx])
    
    while accum_vol < target_vol:
        if i_low > 0 and i_high < num_bins - 1:
            vol_above = float(bin_volumes[i_high + 1])
            vol_below = float(bin_volumes[i_low - 1])
            if vol_above >= vol_below:
                i_high += 1
                accum_vol += vol_above
            else:
                i_low -= 1
                accum_vol += vol_below
        elif i_low > 0:
            i_low -= 1
            accum_vol += float(bin_volumes[i_low])
        elif i_high < num_bins - 1:
            i_high += 1
            accum_vol += float(bin_volumes[i_high])
        else:
            break
            
    vah_price = p_min + (i_high + 1) * w
    val_price = p_min + i_low * w
    
    # Peak & Valley detection (HVNs and LVNs)
    peaks = []
    troughs = []
    for i in range(1, num_bins - 1):
        if bin_volumes[i] > bin_volumes[i-1] and bin_volumes[i] > bin_volumes[i+1]:
            peaks.append((i, bin_volumes[i]))
        elif bin_volumes[i] < bin_volumes[i-1] and bin_volumes[i] < bin_volumes[i+1]:
            troughs.append((i, bin_volumes[i]))
            
    peaks = sorted(peaks, key=lambda x: x[1], reverse=True)[:3]
    troughs = sorted(troughs, key=lambda x: x[1])[:3]
    
    hvn_prices = [round(p_min + (p[0] + 0.5) * w, 2) for p in peaks]
    lvn_prices = [round(p_min + (t[0] + 0.5) * w, 2) for t in troughs]
    
    # Profile Shape Detection (Auction Market Theory)
    avg_vol = total_vol / num_bins if num_bins > 0 else 1.0
    max_vol = bin_volumes[poc_idx]
    
    shape = "D-shape (Balanced)"
    if max_vol < 2.0 * avg_vol:
        shape = "Trend Day"
    elif len(peaks) >= 2:
        p_indices = [p[0] for p in peaks[:2]]
        dist = abs(p_indices[0] - p_indices[1])
        if dist >= int(num_bins * 0.15):
            min_p, max_p = min(p_indices), max(p_indices)
            trough_idx = min_p + int(np.argmin(bin_volumes[min_p:max_p+1]))
            if bin_volumes[trough_idx] < 0.65 * min(bin_volumes[p_indices[0]], bin_volumes[p_indices[1]]):
                shape = "B-shape (Double Distribution)"
                
    if shape not in ["Trend Day", "B-shape (Double Distribution)"]:
        poc_pct = poc_idx / num_bins
        if poc_pct > 0.65:
            shape = "P-shape (Short Covering)"
        elif poc_pct < 0.35:
            shape = "b-shape (Long Liquidation)"
            
    # Format histogram
    histogram = []
    for i, vol in enumerate(bin_volumes):
        histogram.append({
            "price_min": round(bin_ranges[i][0], 2),
            "price_max": round(bin_ranges[i][1], 2),
            "volume": float(vol)
        })
        
    return {
        "poc": round(poc_price, 2),
        "vah": round(vah_price, 2),
        "val": round(val_price, 2),
        "hvn": hvn_prices,
        "lvn": lvn_prices,
        "shape": shape,
        "histogram": histogram
    }


async def fetch_stock_data_and_calculate(symbol: str, lookback: int, db: AsyncSession) -> Dict[str, Any]:
    from services.instrument_resolver import resolve_instrument_info
    info = resolve_instrument_info(symbol.upper().strip())
    if not info or not info.is_active:
        raise HTTPException(status_code=404, detail=f"Stock symbol '{symbol}' not found or inactive.")
        
    instrument_id = info.instrument_id
    company_name = info.company_name
    sector = info.sector
    
    # 2. Fetch daily candles dynamically based on requested lookback + indicators buffer
    limit = max(lookback + 250, 360)
    
    candles_query = text(f"""
        SELECT candle_ts::date as date, open, high, low, close, volume
        FROM stock_candle
        WHERE instrument_id = :instrument_id AND timeframe = 1440
        ORDER BY candle_ts DESC
        LIMIT {limit}
    """)
    candles_res = await db.execute(candles_query, {"instrument_id": instrument_id})
    candles_rows = candles_res.fetchall()
    
    if len(candles_rows) < 10:
        raise HTTPException(status_code=404, detail=f"Insufficient candle data found for {symbol}.")
        
    # Standard DataFrame (chronological)
    df = pd.DataFrame([{
        "date": r.date,
        "open": float(r.open),
        "high": float(r.high),
        "low": float(r.low),
        "close": float(r.close),
        "volume": float(r.volume)
    } for r in reversed(candles_rows)])
    
    # 2.5 Apply corporate action adjustments
    from services.corporate_action_service import get_corporate_actions, adjust_candles
    corporate_actions = await get_corporate_actions(symbol, db)
    df = adjust_candles(df, corporate_actions)
    
    # 3. Technical indicators calculation
    df["ema20"] = indicator_utils.ema(df["close"], 20)
    df["ema50"] = indicator_utils.ema(df["close"], 50)
    df["ema200"] = indicator_utils.ema(df["close"], 200)
    df["volume_ma"] = df["volume"].rolling(window=20).mean()
    
    # ATR calculation
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()
    
    # Cumulative VWAP
    df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
    
    # 4. Market Structure Detection
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    
    swing_highs = [None] * len(df)
    swing_lows = [None] * len(df)
    bos_markers = [False] * len(df)
    choch_markers = [False] * len(df)
    sweeps = [False] * len(df)
    
    # Detect Swings (strength=3)
    for i in range(3, len(df) - 3):
        if highs[i] == max(highs[i-3:i+4]):
            swing_highs[i] = float(highs[i])
        if lows[i] == min(lows[i-3:i+4]):
            swing_lows[i] = float(lows[i])
            
    # BOS / CHoCH structure tracking
    last_sh = None
    last_sl = None
    trend = 0
    
    for i in range(len(df)):
        if swing_highs[i] is not None:
            last_sh = swing_highs[i]
        if swing_lows[i] is not None:
            last_sl = swing_lows[i]
            
        if i > 0:
            if last_sh is not None and closes[i] > last_sh and closes[i-1] <= last_sh:
                if trend == -1:
                    choch_markers[i] = True
                    trend = 1
                else:
                    bos_markers[i] = True
                    trend = 1
                last_sh = None
            elif last_sl is not None and closes[i] < last_sl and closes[i-1] >= last_sl:
                if trend == 1:
                    choch_markers[i] = True
                    trend = -1
                else:
                    bos_markers[i] = True
                    trend = -1
                last_sl = None
                
            # Liquidity sweeps
            if last_sh is not None and highs[i] > last_sh and closes[i] <= last_sh:
                sweeps[i] = True
            elif last_sl is not None and lows[i] < last_sl and closes[i] >= last_sl:
                sweeps[i] = True
                
    df["swing_high"] = swing_highs
    df["swing_low"] = swing_lows
    df["bos"] = bos_markers
    df["choch"] = choch_markers
    df["sweep"] = sweeps
    
    latest_close = df["close"].iloc[-1]
    latest_volume = df["volume"].iloc[-1]
    
    # Adaptive bins calculation
    atr_val = float(df["atr"].iloc[-1]) if not pd.isna(df["atr"].iloc[-1]) else 0.0
    p_min, p_max = float(df["low"].min()), float(df["high"].max())
    if atr_val > 0:
        num_bins = int(min(120, max(30, (p_max - p_min) / (atr_val / 4.0))))
    else:
        num_bins = 50
        
    df_daily = df.tail(lookback)
    daily_profile = calculate_volume_profile(df_daily, num_bins=num_bins)
    
    # Weekly & Monthly Profile Aggregations
    df_weekly = df.copy()
    df_weekly["week_group"] = pd.to_datetime(df_weekly["date"]).dt.to_period("W")
    weekly_candles = df_weekly.groupby("week_group").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "date": "first"
    }).reset_index()
    weekly_profile = calculate_volume_profile(weekly_candles.tail(26), num_bins=40)
    
    df_monthly = df.copy()
    df_monthly["month_group"] = pd.to_datetime(df_monthly["date"]).dt.to_period("M")
    monthly_candles = df_monthly.groupby("month_group").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "date": "first"
    }).reset_index()
    monthly_profile = calculate_volume_profile(monthly_candles.tail(12), num_bins=40)
    
    # Technical Indicators
    rsi_series = indicator_utils.rsi(df["close"])
    rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]) else 50.0
    
    adx_series, _, _ = indicator_utils.adx(df["high"], df["low"], df["close"])
    adx = float(adx_series.iloc[-1]) if not adx_series.empty and not pd.isna(adx_series.iloc[-1]) else 20.0
    
    ema20 = float(df["ema20"].iloc[-1]) if not pd.isna(df["ema20"].iloc[-1]) else latest_close
    ema50 = float(df["ema50"].iloc[-1]) if not pd.isna(df["ema50"].iloc[-1]) else latest_close
    ema200 = float(df["ema200"].iloc[-1]) if not pd.isna(df["ema200"].iloc[-1]) else latest_close
    vwap = float(df["vwap"].iloc[-1]) if not pd.isna(df["vwap"].iloc[-1]) else latest_close
    
    avg_vol_20 = float(df["volume"].tail(20).mean())
    vol_expansion = latest_volume / max(1.0, avg_vol_20)
    
    # Relative Strength compared to universe performance average
    ref_res = await db.execute(text("SELECT MAX(candle_ts) FROM stock_candle"))
    max_ts = ref_res.scalar() or datetime.now()
    cutoff_dt = (max_ts - timedelta(days=45)).date()
    
    perf_query = text("""
        SELECT AVG((close - prev_close)/prev_close) * 100 as avg_pct
        FROM (
            SELECT instrument_id, close, 
                   LAG(close, 21) OVER (PARTITION BY instrument_id ORDER BY candle_ts ASC) as prev_close
            FROM stock_candle
            WHERE timeframe = 1440 AND candle_ts::date >= :cutoff
        ) sub
        WHERE prev_close IS NOT NULL AND prev_close > 0
    """)
    perf_res = await db.execute(perf_query, {"cutoff": cutoff_dt})
    univ_avg_ret = float(perf_res.scalar() or 2.0)
    
    closes_list = df["close"].tolist()
    stock_ret_1m = ((latest_close - closes_list[-21]) / closes_list[-21] * 100) if len(closes_list) >= 21 else 0.0
    relative_strength_rank = round(stock_ret_1m - univ_avg_ret, 2)
    
    # Sector integration
    latest_date_res = await db.execute(text("SELECT MAX(candle_ts::date) FROM stock_candle"))
    latest_date = latest_date_res.scalar() or datetime.now().date()
    
    sec_query = text("""
        SELECT AVG(change_pct) as sec_avg_ret
        FROM (
            SELECT im.sector, (sc.close - prev.close)/prev.close * 100 as change_pct
            FROM instrument_master im
            JOIN stock_candle sc ON im.instrument_id = sc.instrument_id
            JOIN (
                SELECT DISTINCT ON (instrument_id) instrument_id, close
                FROM stock_candle
                WHERE timeframe = 1440 AND candle_ts::date >= :cutoff
                ORDER BY instrument_id, candle_ts ASC
            ) prev ON im.instrument_id = prev.instrument_id
            WHERE im.is_active = TRUE AND sc.timeframe = 1440 AND sc.candle_ts::date >= :latest_date
        ) sub
        WHERE sector = :sector
    """)
    sec_res = await db.execute(sec_query, {"cutoff": cutoff_dt, "sector": sector, "latest_date": latest_date})
    sec_avg_ret = float(sec_res.scalar() or 0.0)
    sector_score = min(100.0, max(0.0, 50.0 + sec_avg_ret * 5))
    
    # BUY / SELL / HOLD Scoring Engine
    score = 50.0
    factors = []
    
    shape = daily_profile["shape"]
    if "P-shape" in shape:
        score += 15
        factors.append("Bullish P-shape Profile (Short Covering)")
    elif "b-shape" in shape:
        score -= 15
        factors.append("Bearish b-shape Profile (Long Liquidation)")
    elif "Trend Day" in shape:
        if latest_close > closes_list[-5]:
            score += 12
            factors.append("Bullish Trend Day structure")
        else:
            score -= 12
            factors.append("Bearish Trend Day structure")
            
    poc = daily_profile["poc"]
    vah = daily_profile["vah"]
    val = daily_profile["val"]
    
    if latest_close > vah:
        score += 15
        factors.append("Price accepted above Value Area High (VAH)")
    elif latest_close < val:
        score -= 15
        factors.append("Price rejected below Value Area Low (VAL)")
    else:
        factors.append("Price trading inside Value Area boundary")
        
    if latest_close > vwap:
        score += 10
        factors.append("Price accepted above VWAP support")
    else:
        score -= 10
        factors.append("Price trading below VWAP resistance")
        
    if latest_close > ema20 > ema50 > ema200:
        score += 15
        factors.append("Strong Bullish EMA Alignment (EMA 20 > 50 > 200)")
    elif latest_close < ema20 < ema50 < ema200:
        score -= 15
        factors.append("Strong Bearish EMA Alignment (EMA 20 < 50 < 200)")
        
    if 50 <= rsi <= 68:
        score += 10
        factors.append(f"RSI in Bullish momentum zone ({rsi:.1f})")
    elif rsi < 32:
        score += 5
        factors.append(f"RSI oversold buy zone ({rsi:.1f})")
        
    if adx > 25:
        if latest_close > ema50:
            score += 10
            factors.append("Strong bullish trend strength (ADX confirmed)")
        else:
            score -= 10
            factors.append("Strong bearish trend strength (ADX confirmed)")
            
    score = min(100.0, max(0.0, score))
    
    if score >= 68:
        action = "BUY"
        verdict = "Strong Buy" if score >= 80 else "Buy"
    elif score <= 35:
        action = "SELL"
        verdict = "Strong Sell" if score <= 20 else "Sell"
    else:
        action = "HOLD"
        verdict = "Hold"
        
    confidence = int(abs(score - 50.0) * 2.0)
    factors = list(dict.fromkeys(factors))[:5]
    
    # Precise Risk Management Entry/Stop/Targets
    stop_loss = round(val * 0.985, 2) if action == "BUY" else round(vah * 1.015, 2)
    entry_zone = f"{round(val, 2)} - {round(latest_close, 2)}" if action == "BUY" else f"{round(latest_close, 2)} - {round(vah, 2)}"
    
    if action == "BUY":
        target_1 = round(latest_close + 1.5 * (latest_close - stop_loss), 2)
        target_2 = round(latest_close + 2.5 * (latest_close - stop_loss), 2)
        target_3 = round(latest_close + 4.0 * (latest_close - stop_loss), 2)
    else:
        target_1 = round(latest_close - 1.5 * (stop_loss - latest_close), 2)
        target_2 = round(latest_close - 2.5 * (stop_loss - latest_close), 2)
        target_3 = round(latest_close - 4.0 * (stop_loss - latest_close), 2)
        
    risk_reward = round((target_1 - latest_close) / max(0.1, latest_close - stop_loss), 2) if action == "BUY" else 1.5
    
    summary = f"Volume profile shows a {shape} structure. "
    if latest_close > vah:
        summary += "Buyers are in control. Price accepted above value area. "
    elif latest_close < val:
        summary += "Sellers are in control. Price rejected below value area. "
    else:
        summary += "Price consolidating inside value area. "
    summary += f"Expect active support/resistance near POC ₹{poc}."
    
    institutional_bias = "Bullish Acceptance" if latest_close > vah else "Bearish Rejection" if latest_close < val else "Rotational Equilibrium"
    
    def get_timeframe_verdict(tf_shape, tf_poc):
        if "P-shape" in tf_shape or latest_close > tf_poc:
            return "Buy"
        elif "b-shape" in tf_shape or latest_close < tf_poc:
            return "Sell"
        return "Hold"
        
    # Format detailed price history with indicators
    price_history = []
    for _, r in df_daily.iterrows():
        price_history.append({
            "date": str(r["date"]),
            "open": clean_float(r["open"]),
            "high": clean_float(r["high"]),
            "low": clean_float(r["low"]),
            "close": clean_float(r["close"]),
            "volume": clean_float(r["volume"]),
            "ema20": clean_float(r["ema20"]),
            "ema50": clean_float(r["ema50"]),
            "ema200": clean_float(r["ema200"]),
            "vwap": clean_float(r["vwap"]),
            "volume_ma": clean_float(r["volume_ma"]),
            "atr": clean_float(r["atr"]),
            "swing_high": clean_float(r["swing_high"]),
            "swing_low": clean_float(r["swing_low"]),
            "bos": bool(r["bos"]),
            "choch": bool(r["choch"]),
            "sweep": bool(r["sweep"])
        })
        
    return {
        "status": "success",
        "symbol": symbol.upper(),
        "company_name": company_name,
        "sector": sector,
        "price": clean_float(latest_close),
        "poc": clean_float(daily_profile["poc"]),
        "vah": clean_float(daily_profile["vah"]),
        "val": clean_float(daily_profile["val"]),
        "hvn": [clean_float(x) for x in daily_profile["hvn"] if clean_float(x) is not None],
        "lvn": [clean_float(x) for x in daily_profile["lvn"] if clean_float(x) is not None],
        "shape": shape,
        "action": action,
        "verdict": verdict,
        "confidence": confidence,
        "risk_score": int(100 - score) if action == "BUY" else int(score),
        "institutional_bias": institutional_bias,
        "summary": summary,
        "factors": factors,
        "histogram": [
            {
                "price_min": clean_float(bin["price_min"]),
                "price_max": clean_float(bin["price_max"]),
                "volume": clean_float(bin["volume"])
            }
            for bin in daily_profile["histogram"]
        ],
        "price_history": price_history,
        "timeframes": {
            "daily": {"shape": shape, "verdict": get_timeframe_verdict(shape, daily_profile["poc"])},
            "weekly": {"shape": weekly_profile["shape"], "verdict": get_timeframe_verdict(weekly_profile["shape"], weekly_profile["poc"])},
            "monthly": {"shape": monthly_profile["shape"], "verdict": get_timeframe_verdict(monthly_profile["shape"], monthly_profile["poc"])}
        },
        "risk_management": {
            "entry_zone": entry_zone,
            "stop_loss": clean_float(stop_loss),
            "target_1": clean_float(target_1),
            "target_2": clean_float(target_2),
            "target_3": clean_float(target_3),
            "risk_reward_ratio": clean_float(risk_reward)
        },
        "sector_integration": {
            "sector_name": sector,
            "sector_score": clean_float(sector_score),
            "sector_rank": 3,
            "relative_strength_rank": clean_float(relative_strength_rank)
        }
    }


@router.get("")
async def get_volume_profile(
    symbol: str,
    lookback: int = 90,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    try:
        cache_key = f"volume_profile:{symbol}:{lookback}"
        cache = get_cache_manager()
        if cache.is_available():
            try:
                cached = cache.get(cache_key)
                if cached:
                    return cached
            except Exception as ce:
                logger.warning(f"Cache read error: {ce}")
                
        res = await fetch_stock_data_and_calculate(symbol, lookback, db)
        
        if cache.is_available():
            try:
                cache.set(cache_key, res, ttl=60)
            except Exception as ce:
                logger.warning(f"Cache write error: {ce}")
                
        return res
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in Volume Profile API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_volume_profile_summary(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    try:
        res = await fetch_stock_data_and_calculate(symbol, 90, db)
        return {
            "status": "success",
            "symbol": res["symbol"],
            "summary": res["summary"],
            "institutional_bias": res["institutional_bias"]
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in Volume Profile Summary API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-verdict")
async def get_volume_profile_verdict(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    try:
        res = await fetch_stock_data_and_calculate(symbol, 90, db)
        return {
            "status": "success",
            "symbol": res["symbol"],
            "verdict": res["verdict"],
            "confidence": res["confidence"],
            "factors": res["factors"],
            "risk_management": res["risk_management"]
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in Volume Profile Verdict API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
