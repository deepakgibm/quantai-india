from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from database import get_read_db
from models import User
from utils.auth import get_current_user
from services.cache import get_cache_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Volume Profile"])

def calculate_rsi(closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    delta = np.diff(closes)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    
    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])
    
    if avg_loss == 0:
        rs = 1e9
    else:
        rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    for i in range(period, len(delta)):
        avg_gain = (avg_gain * (period - 1) + gain[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss[i]) / period
        if avg_loss == 0:
            rs = 1e9
        else:
            rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    return float(rsi) if not np.isnan(rsi) else 50.0

def calculate_adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < 2 * period:
        return 20.0
    
    # Calculate True Range (TR)
    tr = np.zeros(len(closes) - 1)
    plus_dm = np.zeros(len(closes) - 1)
    minus_dm = np.zeros(len(closes) - 1)
    
    for i in range(1, len(closes)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i-1])
        tr3 = abs(lows[i] - closes[i-1])
        tr[i-1] = max(tr1, tr2, tr3)
        
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        
        if up_move > down_move and up_move > 0:
            plus_dm[i-1] = up_move
        else:
            plus_dm[i-1] = 0.0
            
        if down_move > up_move and down_move > 0:
            minus_dm[i-1] = down_move
        else:
            minus_dm[i-1] = 0.0
            
    # Wilder's smoothing
    smoothed_tr = np.zeros(len(tr) - period + 1)
    smoothed_plus_dm = np.zeros(len(tr) - period + 1)
    smoothed_minus_dm = np.zeros(len(tr) - period + 1)
    
    smoothed_tr[0] = np.mean(tr[:period])
    smoothed_plus_dm[0] = np.mean(plus_dm[:period])
    smoothed_minus_dm[0] = np.mean(minus_dm[:period])
    
    for i in range(1, len(smoothed_tr)):
        smoothed_tr[i] = smoothed_tr[i-1] - (smoothed_tr[i-1] / period) + tr[period - 1 + i]
        smoothed_plus_dm[i] = smoothed_plus_dm[i-1] - (smoothed_plus_dm[i-1] / period) + plus_dm[period - 1 + i]
        smoothed_minus_dm[i] = smoothed_minus_dm[i-1] - (smoothed_minus_dm[i-1] / period) + minus_dm[period - 1 + i]
        
    plus_di = 100 * (smoothed_plus_dm / np.where(smoothed_tr == 0, 1e-9, smoothed_tr))
    minus_di = 100 * (smoothed_minus_dm / np.where(smoothed_tr == 0, 1e-9, smoothed_tr))
    
    dx = 100 * (abs(plus_di - minus_di) / np.where(plus_di + minus_di == 0, 1e-9, plus_di + minus_di))
    
    # ADX smoothing
    adx = np.zeros(len(dx) - period + 1)
    adx[0] = np.mean(dx[:period])
    for i in range(1, len(adx)):
        adx[i] = (adx[i-1] * (period - 1) + dx[period - 1 + i]) / period
        
    val = adx[-1]
    return float(val) if not np.isnan(val) else 20.0

def calculate_volume_profile(df: pd.DataFrame, num_bins: int = 50) -> Dict[str, Any]:
    """
    Core algorithm: Approximate Volume Profile by distributing candle volume
    proportionally across overlapping price bins.
    """
    if df.empty:
        return {
            "poc": 0.0, "vah": 0.0, "val": 0.0,
            "hvn": [], "lvn": [], "shape": "D Shape",
            "histogram": []
        }
        
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    volumes = df["volume"].values
    
    p_min = float(np.min(lows))
    p_max = float(np.max(highs))
    
    if p_max == p_min:
        p_max += 1.0 # prevent division by zero
        
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
            # If high == low, put everything in the bin containing close
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
    
    # High Volume Nodes (HVNs) and Low Volume Nodes (LVNs) peak detection
    peaks = []
    troughs = []
    for i in range(1, num_bins - 1):
        if bin_volumes[i] > bin_volumes[i-1] and bin_volumes[i] > bin_volumes[i+1]:
            peaks.append((i, bin_volumes[i]))
        elif bin_volumes[i] < bin_volumes[i-1] and bin_volumes[i] < bin_volumes[i+1]:
            troughs.append((i, bin_volumes[i]))
            
    # Sort and pick top 3 HVNs & LVNs
    peaks = sorted(peaks, key=lambda x: x[1], reverse=True)[:3]
    troughs = sorted(troughs, key=lambda x: x[1])[:3]
    
    hvn_prices = [round(p_min + (p[0] + 0.5) * w, 2) for p in peaks]
    lvn_prices = [round(p_min + (t[0] + 0.5) * w, 2) for t in troughs]
    
    # Profile Shape Detection Heuristics
    avg_vol = total_vol / num_bins if num_bins > 0 else 1.0
    max_vol = bin_volumes[poc_idx]
    
    shape = "D Shape" # Default balanced
    if max_vol < 2.2 * avg_vol:
        shape = "Trend Day"
    elif len(peaks) >= 2:
        # Check for Double Distribution separated by low volume trough
        p_indices = [p[0] for p in peaks[:2]]
        dist = abs(p_indices[0] - p_indices[1])
        if dist >= int(num_bins * 0.18):
            min_p, max_p = min(p_indices), max(p_indices)
            trough_idx = min_p + int(np.argmin(bin_volumes[min_p:max_p+1]))
            if bin_volumes[trough_idx] < 0.6 * min(bin_volumes[p_indices[0]], bin_volumes[p_indices[1]]):
                shape = "Double Distribution"
                
    if shape not in ["Trend Day", "Double Distribution"]:
        poc_pct = poc_idx / num_bins
        if poc_pct > 0.65:
            shape = "P Shape"
        elif poc_pct < 0.35:
            shape = "B Shape"
            
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
    # 1. Lookup symbol in instrument master
    query = text("""
        SELECT instrument_id, instrument_key, company_name, sector
        FROM instrument_master
        WHERE symbol = :symbol AND is_active = TRUE
        LIMIT 1
    """)
    res = await db.execute(query, {"symbol": symbol.upper().strip()})
    row = res.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Stock symbol '{symbol}' not found or inactive.")
        
    instrument_id, instrument_key, company_name, sector = row
    
    # 2. Fetch daily candles (fetch up to 360 to cover all timeframes)
    candles_query = text("""
        SELECT candle_ts::date as date, open, high, low, close, volume
        FROM stock_candle
        WHERE instrument_id = :instrument_id AND timeframe = 1440
        ORDER BY candle_ts DESC
        LIMIT 360
    """)
    candles_res = await db.execute(candles_query, {"instrument_id": instrument_id})
    candles_rows = candles_res.fetchall()
    
    if len(candles_rows) < 10:
        raise HTTPException(status_code=404, detail=f"Insufficient candle data found for {symbol}.")
        
    # Standard DataFrame
    df = pd.DataFrame([{
        "date": r.date,
        "open": float(r.open),
        "high": float(r.high),
        "low": float(r.low),
        "close": float(r.close),
        "volume": float(r.volume)
    } for r in reversed(candles_rows)])
    
    latest_close = df["close"].iloc[-1]
    latest_volume = df["volume"].iloc[-1]
    
    # Multi-timeframe calculations
    # Daily profile (uses chosen lookback, capped at len(df))
    df_daily = df.tail(lookback)
    daily_profile = calculate_volume_profile(df_daily)
    
    # Weekly profile (group to weeks)
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
    weekly_profile = calculate_volume_profile(weekly_candles.tail(26)) # last 26 weeks
    
    # Monthly profile (group to months)
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
    monthly_profile = calculate_volume_profile(monthly_candles.tail(12)) # last 12 months
    
    # Compute technical indicators on daily tail
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    volumes = df["volume"].values
    
    rsi = calculate_rsi(closes)
    adx = calculate_adx(highs, lows, closes)
    
    # EMAs
    df_ema = df.copy()
    ema20 = float(df_ema["close"].ewm(span=20, adjust=False).mean().iloc[-1])
    ema50 = float(df_ema["close"].ewm(span=50, adjust=False).mean().iloc[-1])
    ema200 = float(df_ema["close"].ewm(span=200, adjust=False).mean().iloc[-1])
    
    # VWAP
    vwap = float((df_ema["close"] * df_ema["volume"]).sum() / df_ema["volume"].sum())
    
    # Volume Expansion
    avg_vol_20 = float(df_ema["volume"].tail(20).mean())
    vol_expansion = latest_volume / max(1.0, avg_vol_20)
    
    # Relative Strength compared to universe performance average
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
    cutoff_dt = (datetime.now() - timedelta(days=45)).date()
    perf_res = await db.execute(perf_query, {"cutoff": cutoff_dt})
    univ_avg_ret = float(perf_res.scalar() or 2.0)
    
    # Stock 1-month return
    stock_ret_1m = ((latest_close - closes[-21]) / closes[-21] * 100) if len(closes) >= 21 else 0.0
    relative_strength_rank = round(stock_ret_1m - univ_avg_ret, 2)
    
    # Sector integration (fetch from sector analysis metrics or compute sector score)
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
    latest_date_res = await db.execute(text("SELECT MAX(candle_ts::date) FROM stock_candle"))
    latest_date = latest_date_res.scalar() or datetime.now().date()
    
    sec_res = await db.execute(sec_query, {"cutoff": cutoff_dt, "sector": sector, "latest_date": latest_date})
    sec_avg_ret = float(sec_res.scalar() or 0.0)
    # Map sector return to a normalized score 0-100
    sector_score = min(100.0, max(0.0, 50.0 + sec_avg_ret * 5))
    
    # BUY / SELL / HOLD Scoring Engine
    score = 50.0 # start neutral
    factors = []
    
    # 1. Profile Shape Contribution
    shape = daily_profile["shape"]
    if shape == "P Shape":
        score += 15
        factors.append("Bullish P-Shape Profile (High Price Acceptance)")
    elif shape == "B Shape":
        score -= 15
        factors.append("Bearish B-Shape Profile (Distribution Low)")
    elif shape == "Trend Day":
        if latest_close > closes[-5]:
            score += 12
            factors.append("Bullish Trend Day structure")
        else:
            score -= 12
            factors.append("Bearish Trend Day structure")
            
    # 2. Acceptance relative to Value Area & POC
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
        
    if latest_close > poc:
        score += 8
        factors.append("Price trading above Point of Control (POC)")
    else:
        score -= 8
        factors.append("Price trading below Point of Control (POC)")
        
    # 3. EMA alignment
    if latest_close > ema20 > ema50 > ema200:
        score += 15
        factors.append("Strong Bullish EMA Alignment (EMA 20 > 50 > 200)")
    elif latest_close < ema20 < ema50 < ema200:
        score -= 15
        factors.append("Strong Bearish EMA Alignment (EMA 20 < 50 < 200)")
        
    # 4. VWAP Position
    if latest_close > vwap:
        score += 10
        factors.append("Price accepted above VWAP support")
    else:
        score -= 10
        factors.append("Price trading below VWAP resistance")
        
    # 5. RSI
    if 50 <= rsi <= 68:
        score += 10
        factors.append(f"RSI is in Bullish momentum zone ({rsi:.1f})")
    elif rsi > 72:
        score -= 5 # overbought caution
        factors.append(f"RSI indicates Overbought condition ({rsi:.1f})")
    elif rsi < 32:
        score += 5 # oversold buy caution
        factors.append(f"RSI indicates Oversold condition ({rsi:.1f})")
        
    # 6. ADX Trend Strength
    if adx > 25:
        if latest_close > ema50:
            score += 10
            factors.append(f"ADX confirms strong bullish trend strength ({adx:.1f})")
        else:
            score -= 10
            factors.append(f"ADX confirms strong bearish trend strength ({adx:.1f})")
            
    # 7. Volume Expansion
    if vol_expansion > 1.5:
        if latest_close > closes[-2]:
            score += 10
            factors.append(f"Bullish Volume Expansion (latest volume {vol_expansion:.1f}x 20d average)")
        else:
            score -= 10
            factors.append(f"Bearish Volume Expansion on pullback ({vol_expansion:.1f}x 20d average)")
            
    # 8. Sector strength
    if sector_score > 60:
        score += 10
        factors.append(f"Strong Sector Strength score ({sector_score:.1f})")
    elif sector_score < 40:
        score -= 10
        factors.append(f"Weak Sector Strength score ({sector_score:.1f})")
        
    # Cap score
    score = min(100.0, max(0.0, score))
    
    # Action and final verdict mapping
    if score >= 68:
        action = "BUY"
        if score >= 80:
            verdict = "Strong Buy"
        else:
            verdict = "Buy"
    elif score <= 35:
        action = "SELL"
        if score <= 20:
            verdict = "Sell"
        else:
            verdict = "Reduce"
    else:
        action = "HOLD"
        verdict = "Hold"
        
    confidence = int(abs(score - 50.0) * 2.0)
    
    # Sort and pick top 5 factors
    factors = list(dict.fromkeys(factors))[:5]
    
    # Risk Management Calculation
    if action == "BUY":
        stop_loss = round(val * 0.985, 2)
        target_1 = round(latest_close + 1.5 * (latest_close - stop_loss), 2)
        target_2 = round(latest_close + 2.5 * (latest_close - stop_loss), 2)
        entry_zone = f"{round(val, 2)} - {round(latest_close, 2)}"
    elif action == "SELL":
        stop_loss = round(vah * 1.015, 2)
        target_1 = round(latest_close - 1.5 * (stop_loss - latest_close), 2)
        target_2 = round(latest_close - 2.5 * (stop_loss - latest_close), 2)
        entry_zone = f"{round(latest_close, 2)} - {round(vah, 2)}"
    else:
        stop_loss = round(val * 0.97, 2)
        target_1 = round(latest_close + 1.5 * (latest_close - stop_loss), 2)
        target_2 = round(latest_close + 2.5 * (latest_close - stop_loss), 2)
        entry_zone = f"{round(val, 2)} - {round(vah, 2)}"
        
    risk_reward = round((target_1 - latest_close) / max(1.0, latest_close - stop_loss), 2) if action == "BUY" else 1.5
    
    # Flow Summary Generator
    summary = f"Volume profile shows a {shape} structure. "
    if latest_close > vah:
        summary += f"Buyers are in control. Price accepted above value area. "
    elif latest_close < val:
        summary += f"Sellers are in control. Price rejected below value area. "
    else:
        summary += f"Price consolidating inside value area. "
        
    if action == "BUY":
        summary += "Bullish continuation likely. Expect institutional support near POC."
    elif action == "SELL":
        summary += "Bearish continuation likely. Heavy overhead supply detected near VAH."
    else:
        summary += "Acceptance near POC indicates market equilibrium. Expect rotational range trading."
        
    institutional_bias = "Bullish Acceptance" if latest_close > vah else "Bearish Rejection" if latest_close < val else "Rotational Equilibrium"
    
    # Timeframe verdicts
    def get_timeframe_verdict(tf_shape, tf_poc):
        if tf_shape == "P Shape" or latest_close > tf_poc:
            return "Buy"
        elif tf_shape == "B Shape" or latest_close < tf_poc:
            return "Sell"
        return "Hold"

    return {
        "status": "success",
        "symbol": symbol.upper(),
        "company_name": company_name,
        "sector": sector,
        "price": latest_close,
        "poc": daily_profile["poc"],
        "vah": daily_profile["vah"],
        "val": daily_profile["val"],
        "hvn": daily_profile["hvn"],
        "lvn": daily_profile["lvn"],
        "shape": shape,
        "action": action,
        "verdict": verdict,
        "confidence": confidence,
        "risk_score": int(100 - score) if action == "BUY" else int(score),
        "institutional_bias": institutional_bias,
        "summary": summary,
        "factors": factors,
        "histogram": daily_profile["histogram"],
        "price_history": [
            {
                "date": str(r["date"]),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["volume"])
            }
            for _, r in df_daily.iterrows()
        ],
        "timeframes": {
            "daily": {"shape": shape, "verdict": get_timeframe_verdict(shape, daily_profile["poc"])},
            "weekly": {"shape": weekly_profile["shape"], "verdict": get_timeframe_verdict(weekly_profile["shape"], weekly_profile["poc"])},
            "monthly": {"shape": monthly_profile["shape"], "verdict": get_timeframe_verdict(monthly_profile["shape"], monthly_profile["poc"])}
        },
        "risk_management": {
            "entry_zone": entry_zone,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "risk_reward_ratio": risk_reward
        },
        "sector_integration": {
            "sector_name": sector,
            "sector_score": round(sector_score, 1),
            "sector_rank": 3,
            "relative_strength_rank": relative_strength_rank
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
    except Exception as e:
        logger.error(f"Error in Volume Profile Verdict API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
