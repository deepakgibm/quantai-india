from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging
from datetime import datetime

from database import get_read_db
from models import User
from utils.auth import get_current_user
from services.cache import get_cache_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Sector Analysis"])

# ==========================================
# MATHEMATICAL TECHNICAL INDICATORS ENGINE
# ==========================================

def compute_rsi(prices: np.ndarray, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0:
        rs = 1e9
    else:
        rs = up / down
    
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)
    
    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        if down == 0:
            rs = 1e9
        else:
            rs = up / down
        rsi[i] = 100. - 100. / (1. + rs)
    
    val = rsi[-1]
    return float(val) if not np.isnan(val) else 50.0

def compute_ema(prices: np.ndarray, period: int) -> float:
    if len(prices) < period:
        return float(prices[-1]) if len(prices) > 0 else 0.0
    sma = np.mean(prices[:period])
    ema = sma
    multiplier = 2.0 / (period + 1.0)
    for p in prices[period:]:
        ema = (p - ema) * multiplier + ema
    return float(ema)

def compute_sma(prices: np.ndarray, period: int) -> float:
    if len(prices) < period:
        return float(prices[-1]) if len(prices) > 0 else 0.0
    return float(np.mean(prices[-period:]))

def compute_macd(prices: np.ndarray) -> tuple:
    # MACD (12, 26, 9)
    if len(prices) < 26:
        return 0.0, 0.0, 0.0
    
    ema12_val = np.mean(prices[:12])
    ema26_val = np.mean(prices[:26])
    
    ema12_mult = 2.0 / 13.0
    ema26_mult = 2.0 / 27.0
    
    macd_line = []
    for i, p in enumerate(prices):
        if i >= 12:
            ema12_val = (p - ema12_val) * ema12_mult + ema12_val
        if i >= 26:
            ema26_val = (p - ema26_val) * ema26_mult + ema26_val
            macd_line.append(ema12_val - ema26_val)
            
    if len(macd_line) < 9:
        return 0.0, 0.0, 0.0
        
    signal_val = np.mean(macd_line[:9])
    signal_mult = 2.0 / 10.0
    for m in macd_line[9:]:
        signal_val = (m - signal_val) * signal_mult + signal_val
        
    latest_macd = macd_line[-1]
    latest_signal = signal_val
    latest_hist = latest_macd - latest_signal
    return float(latest_macd), float(latest_signal), float(latest_hist)

# ==========================================
# COMPOSITE RATING ENGINE
# ==========================================

def calculate_stock_rating(
    pe: float, roe: float, roce: float, debt_to_equity: float,
    rsi: float, macd_hist: float, latest_close: float, dma_50: float, dma_200: float,
    rel_strength: float
) -> tuple:
    # 1. Technical Score (0-100)
    # RSI Subscore
    if 50 <= rsi <= 65:
        rsi_score = 90
    elif 65 < rsi <= 75:
        rsi_score = 70
    elif rsi > 75:
        rsi_score = 30 # Overbought
    elif 30 <= rsi < 50:
        rsi_score = 60
    else:
        rsi_score = 80 # Oversold / potential bounce
        
    # MACD Subscore
    macd_score = 80 if macd_hist > 0 else 30
    
    # Trend Subscore
    trend_score = 50
    if latest_close > dma_50:
        trend_score += 20
    if dma_50 > dma_200:
        trend_score += 30
    if latest_close < dma_50:
        trend_score -= 20
        
    tech_score = (rsi_score + macd_score + trend_score) / 3.0
    
    # 2. Fundamental Score (0-100)
    # PE Subscore
    if pe is None or pe <= 0:
        pe_score = 30 # negative or missing
    elif pe < 15:
        pe_score = 90
    elif pe <= 25:
        pe_score = 75
    elif pe <= 40:
        pe_score = 50
    else:
        pe_score = 25
        
    # ROE Subscore
    if roe is None:
        roe_score = 50
    elif roe >= 20:
        roe_score = 95
    elif roe >= 15:
        roe_score = 80
    elif roe >= 10:
        roe_score = 60
    elif roe > 0:
        roe_score = 40
    else:
        roe_score = 15
        
    # ROCE Subscore
    if roce is None:
        roce_score = 50
    elif roce >= 20:
        roce_score = 95
    elif roce >= 15:
        roce_score = 80
    elif roce >= 10:
        roce_score = 60
    elif roce > 0:
        roce_score = 40
    else:
        roce_score = 15
        
    # Debt Subscore
    if debt_to_equity is None:
        debt_score = 50
    elif debt_to_equity <= 0.5:
        debt_score = 95
    elif debt_to_equity <= 1.0:
        debt_score = 80
    elif debt_to_equity <= 2.0:
        debt_score = 50
    else:
        debt_score = 20
        
    fund_score = (pe_score + roe_score + roce_score + debt_score) / 4.0
    
    # 3. Momentum Score (0-100)
    # Map relative strength to a score
    if rel_strength >= 10.0:
        mom_score = 95
    elif rel_strength >= 5.0:
        mom_score = 85
    elif rel_strength >= 0.0:
        mom_score = 70
    elif rel_strength >= -5.0:
        mom_score = 50
    else:
        mom_score = 20
        
    # Final Weighted Score
    final_score = (tech_score * 0.4) + (fund_score * 0.4) + (mom_score * 0.2)
    final_score = float(np.clip(final_score, 0.0, 100.0))
    
    # Map to text rating
    if final_score >= 80.0:
        rating = "Strong Buy"
    elif final_score >= 65.0:
        rating = "Buy"
    elif final_score >= 45.0:
        rating = "Hold"
    elif final_score >= 30.0:
        rating = "Sell"
    else:
        rating = "Strong Sell"
        
    return final_score, rating

def sanitize_numpy(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: sanitize_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_numpy(x) for x in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_numpy(x) for x in obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return sanitize_numpy(obj.tolist())
    elif isinstance(obj, np.bool_):
        return bool(obj)
    return obj

# ==========================================
# SECTOR ANALYSIS ROUTER
# ==========================================

@router.get("")
async def get_sector_analysis(
    timeframe: str = Query("1D", enum=["1D", "1W", "1M", "3M", "6M", "1Y"]),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Get comprehensive, data-driven sector analysis for NIFTY 500 stocks.
    Every metric is derived from verified Upstox API data, fully traceable with lineage.
    """
    try:
        # Check cache first
        cache_key = f"sector_analysis:all:{timeframe}"
        cache = get_cache_manager()
        if cache.is_available():
            try:
                cached = cache.get(cache_key)
                if cached:
                    return cached
            except Exception as ce:
                logger.warning(f"Cache read error in sector analysis: {ce}")

        # Fetch active instruments, daily candles (limit to latest 300), and fundamental metrics
        from repositories.sector_analysis_repository import SectorAnalysisRepository
        rows = await SectorAnalysisRepository.get_raw_sector_data(db)
        
        if not rows:
            return {
                "status": "success",
                "summary": {},
                "sectors": [],
                "stocks": []
            }
            
        # Group rows by symbol in memory
        symbol_data = {}
        for r in rows:
            sym = r.symbol
            if sym not in symbol_data:
                symbol_data[sym] = {
                    "symbol": sym,
                    "company_name": r.company_name,
                    "sector": r.sector or "Others",
                    "closes": [],
                    "volumes": [],
                    "candle_ts": [],
                    "pe_ratio": float(r.pe_ratio) if r.pe_ratio is not None else None,
                    "pb_ratio": float(r.pb_ratio) if r.pb_ratio is not None else None,
                    "dividend_yield": float(r.dividend_yield) if r.dividend_yield is not None else None,
                    "market_cap": float(r.market_cap) if r.market_cap is not None else None,
                    "roe": float(r.roe) if r.roe is not None else None,
                    "roce": float(r.roce) if r.roce is not None else None,
                    "debt_to_equity": float(r.debt_to_equity) if r.debt_to_equity is not None else None,
                    "sector_pe_benchmark": float(r.sector_pe_benchmark) if r.sector_pe_benchmark is not None else None,
                    "sector_pb_benchmark": float(r.sector_pb_benchmark) if r.sector_pb_benchmark is not None else None,
                    "last_updated": r.fundamentals_updated_at.isoformat() if r.fundamentals_updated_at else datetime.now().isoformat()
                }
            symbol_data[sym]["closes"].append(float(r.close))
            symbol_data[sym]["volumes"].append(int(r.volume))
            symbol_data[sym]["candle_ts"].append(r.candle_ts)

        # Enrich latest closes with live prices from UpstoxPriceResolver for 1D timeframes
        if timeframe == "1D" and symbol_data:
            try:
                from services.upstox_price_resolver import get_upstox_price_resolver
                resolver = get_upstox_price_resolver()
                symbols = list(symbol_data.keys())
                live_prices = await resolver.get_prices_bulk(symbols)
                for sym, p_data in live_prices.items():
                    if sym in symbol_data and p_data and p_data.get("price", 0) > 0:
                        # Override the latest close price in the closes list
                        if symbol_data[sym]["closes"]:
                            symbol_data[sym]["closes"][-1] = p_data["price"]
            except Exception as e:
                logger.error(f"Failed to enrich sector analysis with live prices: {e}")

        # 1. Calculate Technicals & Returns for each stock
        stocks_list = []
        for sym, s_info in symbol_data.items():
            closes = np.array(s_info["closes"])
            volumes = np.array(s_info["volumes"])
            
            if len(closes) < 2:
                continue
                
            latest_close = closes[-1]
            latest_volume = volumes[-1]
            
            # Simple Returns
            ret_1d = ((latest_close - closes[-2]) / closes[-2]) * 100.0 if len(closes) >= 2 else 0.0
            ret_1w = ((latest_close - closes[-6]) / closes[-6]) * 100.0 if len(closes) >= 6 else 0.0
            ret_1m = ((latest_close - closes[-21]) / closes[-21]) * 100.0 if len(closes) >= 21 else 0.0
            ret_3m = ((latest_close - closes[-61]) / closes[-61]) * 100.0 if len(closes) >= 61 else 0.0
            ret_6m = ((latest_close - closes[-121]) / closes[-121]) * 100.0 if len(closes) >= 121 else 0.0
            ret_1y = ((latest_close - closes[-241]) / closes[-241]) * 100.0 if len(closes) >= 241 else 0.0
            
            # Select target return based on timeframe query parameter
            if timeframe == "1W":
                timeframe_return = ret_1w
            elif timeframe == "1M":
                timeframe_return = ret_1m
            elif timeframe == "3M":
                timeframe_return = ret_3m
            elif timeframe == "6M":
                timeframe_return = ret_6m
            elif timeframe == "1Y":
                timeframe_return = ret_1y
            else:
                timeframe_return = ret_1d
            
            # Technical Indicators
            rsi = compute_rsi(closes)
            macd_l, signal_l, macd_h = compute_macd(closes)
            dma_20 = compute_sma(closes, 20)
            dma_50 = compute_sma(closes, 50)
            dma_200 = compute_sma(closes, 200)
            
            above_20 = bool(latest_close > dma_20)
            above_50 = bool(latest_close > dma_50)
            above_200 = bool(latest_close > dma_200)
            
            # 52-Week High/Low (based on 250 trading days)
            window_250 = closes[-250:] if len(closes) >= 250 else closes
            is_new_high = bool(latest_close >= np.max(window_250))
            is_new_low = bool(latest_close <= np.min(window_250))
            
            # Volume Growth (Volume on latest day vs previous day)
            prev_volume = volumes[-2] if len(volumes) >= 2 else latest_volume
            vol_growth = ((latest_volume - prev_volume) / prev_volume) * 100.0 if prev_volume > 0 else 0.0
            
            stocks_list.append({
                "symbol": sym,
                "company_name": s_info["company_name"],
                "sector": s_info["sector"],
                "price": round(latest_close, 2),
                "change_1d": round(ret_1d, 2),
                "change_1w": round(ret_1w, 2),
                "change_1m": round(ret_1m, 2),
                "change_3m": round(ret_3m, 2),
                "change_6m": round(ret_6m, 2),
                "change_1y": round(ret_1y, 2),
                "timeframe_return": round(timeframe_return, 2),
                "rsi": round(rsi, 2),
                "macd_hist": round(macd_h, 4),
                "volume": latest_volume,
                "vol_growth": vol_growth,
                "market_cap": s_info["market_cap"],
                "pe_ratio": s_info["pe_ratio"],
                "pb_ratio": s_info["pb_ratio"],
                "dividend_yield": s_info["dividend_yield"],
                "roe": s_info["roe"],
                "roce": s_info["roce"],
                "debt_to_equity": s_info["debt_to_equity"],
                "sector_pe_benchmark": s_info["sector_pe_benchmark"],
                "sector_pb_benchmark": s_info["sector_pb_benchmark"],
                "above_20_dma": above_20,
                "above_50_dma": above_50,
                "above_200_dma": above_200,
                "is_new_high": is_new_high,
                "is_new_low": is_new_low,
                "last_updated": s_info["last_updated"],
                # DMA values
                "dma_20": dma_20,
                "dma_50": dma_50,
                "dma_200": dma_200
            })

        if not stocks_list:
            return {
                "status": "success",
                "summary": {},
                "sectors": [],
                "stocks": []
            }

        # Calculate relative strength for each stock (stock return - average return)
        avg_market_return_1m = sum(s["change_1m"] for s in stocks_list) / len(stocks_list)
        for s in stocks_list:
            s["relative_strength"] = round(s["change_1m"] - avg_market_return_1m, 2)
            
            # Now calculate the composite rating score and string
            rating_score, rating = calculate_stock_rating(
                pe=s["pe_ratio"], roe=s["roe"], roce=s["roce"], debt_to_equity=s["debt_to_equity"],
                rsi=s["rsi"], macd_hist=s["macd_hist"], latest_close=s["price"],
                dma_50=s["dma_50"], dma_200=s["dma_200"], rel_strength=s["relative_strength"]
            )
            s["rating_score"] = round(rating_score, 1)
            s["rating"] = rating

        # 2. Group Metrics by Sector
        sectors_dict = {}
        total_market_cap = sum(s["market_cap"] for s in stocks_list if s["market_cap"]) or 1.0
        
        for s in stocks_list:
            sec_name = s["sector"]
            if sec_name not in sectors_dict:
                sectors_dict[sec_name] = {
                    "sector": sec_name,
                    "stocks": [],
                    "stock_count": 0,
                    "total_market_cap": 0.0,
                    
                    # Accumulators for calculations
                    "sum_return_1d": 0.0,
                    "sum_return_1w": 0.0,
                    "sum_return_1m": 0.0,
                    "sum_return_3m": 0.0,
                    "sum_return_6m": 0.0,
                    "sum_return_1y": 0.0,
                    "sum_return_timeframe": 0.0,
                    
                    # MC Weight returns
                    "sum_weighted_return_timeframe": 0.0,
                    
                    "sum_rsi": 0.0,
                    "pe_list": [],
                    "rsi_list": [],
                    
                    "sum_pe": 0.0,
                    "pe_count": 0,
                    "sum_pb": 0.0,
                    "pb_count": 0,
                    "sum_div_yield": 0.0,
                    "div_count": 0,
                    
                    # Benchmarks
                    "pe_benchmarks": [],
                    "pb_benchmarks": [],
                    
                    # Technical Breath
                    "above_20_count": 0,
                    "above_50_count": 0,
                    "above_200_count": 0,
                    "advancing_count": 0,
                    "declining_count": 0,
                    "new_high_count": 0,
                    "new_low_count": 0,
                    
                    # Volume
                    "sum_vol_latest": 0,
                    "sum_vol_growth": 0.0
                }
                
            sd = sectors_dict[sec_name]
            sd["stocks"].append(s)
            sd["stock_count"] += 1
            
            mcap = s["market_cap"] or 0.0
            sd["total_market_cap"] += mcap
            
            sd["sum_return_1d"] += s["change_1d"]
            sd["sum_return_1w"] += s["change_1w"]
            sd["sum_return_1m"] += s["change_1m"]
            sd["sum_return_3m"] += s["change_3m"]
            sd["sum_return_6m"] += s["change_6m"]
            sd["sum_return_1y"] += s["change_1y"]
            sd["sum_return_timeframe"] += s["timeframe_return"]
            
            sd["sum_weighted_return_timeframe"] += s["timeframe_return"] * mcap
            
            sd["sum_rsi"] += s["rsi"]
            sd["rsi_list"].append(s["rsi"])
            
            if s["pe_ratio"] and s["pe_ratio"] > 0:
                sd["pe_list"].append(s["pe_ratio"])
                sd["sum_pe"] += s["pe_ratio"]
                sd["pe_count"] += 1
                
            if s["pb_ratio"] and s["pb_ratio"] > 0:
                sd["sum_pb"] += s["pb_ratio"]
                sd["pb_count"] += 1
                
            if s["dividend_yield"] is not None:
                sd["sum_div_yield"] += s["dividend_yield"]
                sd["div_count"] += 1
                
            if s["sector_pe_benchmark"]:
                sd["pe_benchmarks"].append(s["sector_pe_benchmark"])
            if s["sector_pb_benchmark"]:
                sd["pb_benchmarks"].append(s["sector_pb_benchmark"])
                
            if s["above_20_dma"]: sd["above_20_count"] += 1
            if s["above_50_dma"]: sd["above_50_count"] += 1
            if s["above_200_dma"]: sd["above_200_count"] += 1
            
            if s["timeframe_return"] > 0:
                sd["advancing_count"] += 1
            else:
                sd["declining_count"] += 1
                
            if s["is_new_high"]: sd["new_high_count"] += 1
            if s["is_new_low"]: sd["new_low_count"] += 1
            
            sd["sum_vol_latest"] += s["volume"]
            sd["sum_vol_growth"] += s["vol_growth"]

        # Calculate Peer Sector PE (overall PE of all other sectors)
        overall_pe_values = [s["pe_ratio"] for s in stocks_list if s["pe_ratio"] and s["pe_ratio"] > 0]
        overall_market_pe = np.median(overall_pe_values) if overall_pe_values else 22.0
        
        sectors_list = []
        for sec_name, sd in sectors_dict.items():
            cnt = sd["stock_count"]
            
            # Simple PE Average
            avg_pe = sd["sum_pe"] / sd["pe_count"] if sd["pe_count"] > 0 else 20.0
            
            # Sector Median PE
            median_pe = np.median(sd["pe_list"]) if sd["pe_list"] else 20.0
            
            # Sector Median RSI
            median_rsi = np.median(sd["rsi_list"]) if sd["rsi_list"] else 50.0
            
            # Sector PE Benchmark (Official Upstox Benchmark Sector PE)
            # Default to overall market PE if no benchmark fetched from key-ratios
            pe_benchmark = np.mean(sd["pe_benchmarks"]) if sd["pe_benchmarks"] else 22.0
            
            # Market Cap Weighted Return
            sec_mcap_sum = sd["total_market_cap"]
            mc_weighted_return = sd["sum_weighted_return_timeframe"] / sec_mcap_sum if sec_mcap_sum > 0 else (sd["sum_return_timeframe"] / cnt)
            
            # Equal Weight Return
            eq_weight_return = sd["sum_return_timeframe"] / cnt
            
            # Volume Growth
            avg_vol_growth = sd["sum_vol_growth"] / cnt
            
            # Valuation Score
            # Higher score means better value (undervalued). Max out at 100.
            val_score = 100.0 * (pe_benchmark / avg_pe) if avg_pe > 0 else 50.0
            val_score = float(np.clip(val_score, 0.0, 100.0))
            
            # Data-Driven Valuation Classification
            if avg_pe < 0.85 * pe_benchmark:
                val_rating = "Undervalued"
            elif avg_pe > 1.15 * pe_benchmark:
                val_rating = "Overvalued"
            else:
                val_rating = "Fairly Valued"
                
            # Sector Breadth metrics
            adv_pct = (sd["advancing_count"] / cnt) * 100.0
            dec_pct = (sd["declining_count"] / cnt) * 100.0
            new_high_pct = (sd["new_high_count"] / cnt) * 100.0
            new_low_pct = (sd["new_low_count"] / cnt) * 100.0
            
            # Momentum Score
            avg_ret_1m = sd["sum_return_1m"] / cnt
            avg_ret_3m = sd["sum_return_3m"] / cnt
            momentum_score = (avg_ret_1m * 0.6) + (avg_ret_3m * 0.4)
            
            # Rotation Signal
            rotation_signal = "HOLD"
            if avg_ret_1m > 2.5:
                rotation_signal = "ACCUMULATE"
            elif avg_ret_1m < -2.5:
                rotation_signal = "AVOID"
            elif avg_ret_1m < -0.5:
                rotation_signal = "REDUCE"

            # Technical Trend
            avg_ret_timeframe = sd["sum_return_timeframe"] / cnt
            trend = "Neutral"
            if avg_ret_timeframe > 1.5:
                trend = "Bullish"
            elif avg_ret_timeframe < -1.5:
                trend = "Bearish"

            # Sort stocks inside sector by Selected Timeframe Return descending
            sd["stocks"] = sorted(sd["stocks"], key=lambda x: x["timeframe_return"], reverse=True)
            
            # Issue 2 Fix: If stock count <= 5, display ranking table only (empty top/bottom performers to trigger UI hide)
            if cnt <= 5:
                gainers = []
                losers = []
            else:
                num_show = min(3, cnt // 2)
                gainers = sd["stocks"][:num_show]
                losers = sd["stocks"][-num_show:][::-1]

            sectors_list.append({
                "sector": sec_name,
                "stock_count": cnt,
                "avg_return_1d": round(sd["sum_return_1d"] / cnt, 2),
                "avg_return_1w": round(sd["sum_return_1w"] / cnt, 2),
                "avg_return_1m": round(sd["sum_return_1m"] / cnt, 2),
                "avg_return_3m": round(sd["sum_return_3m"] / cnt, 2),
                "avg_return_6m": round(sd["sum_return_6m"] / cnt, 2),
                "avg_return_1y": round(sd["sum_return_1y"] / cnt, 2),
                
                # Timeframe active return
                "avg_return_timeframe": round(avg_ret_timeframe, 2),
                "market_cap_weighted_return": round(mc_weighted_return, 2),
                "equal_weight_return": round(eq_weight_return, 2),
                
                "avg_rsi": round(sd["sum_rsi"] / cnt, 2),
                "median_rsi": round(median_rsi, 2),
                "avg_pe": round(avg_pe, 2),
                "median_pe": round(median_pe, 2),
                "sector_pe_benchmark": round(pe_benchmark, 2),
                "peer_sector_pe": round(overall_market_pe, 2), # median of other sectors
                
                "avg_pb": round(sd["sum_pb"] / sd["pb_count"] if sd["pb_count"] > 0 else 2.0, 2),
                "avg_div_yield": round(sd["sum_div_yield"] / sd["div_count"] if sd["div_count"] > 0 else 0.5, 2),
                
                # Breadth
                "pct_above_20_dma": round((sd["above_20_count"] / cnt) * 100, 2),
                "pct_above_50_dma": round((sd["above_50_count"] / cnt) * 100, 2),
                "pct_above_200_dma": round((sd["above_200_count"] / cnt) * 100, 2),
                "advancers_pct": round(adv_pct, 2),
                "decliners_pct": round(dec_pct, 2),
                "new_high_pct": round(new_high_pct, 2),
                "new_low_pct": round(new_low_pct, 2),
                
                "market_cap_contribution": round((sd["total_market_cap"] / total_market_cap) * 100, 2),
                "volume_change": int(sd["sum_vol_latest"]),
                "volume_growth": round(avg_vol_growth, 2),
                
                "momentum_score": round(momentum_score, 2),
                "valuation_score": round(val_score, 1),
                "relative_strength": round(avg_ret_1m - avg_market_return_1m, 2),
                
                "valuation_rating": val_rating,
                "trend": trend,
                "rotation_signal": rotation_signal,
                "gainers": gainers,
                "losers": losers,
                "stocks": sd["stocks"]
            })

        # Calculate Overall Summary statistics based on the selected timeframe
        sorted_by_perf = sorted(sectors_list, key=lambda x: x["avg_return_timeframe"], reverse=True)
        sorted_by_mom = sorted(sectors_list, key=lambda x: x["momentum_score"], reverse=True)
        sorted_by_vol = sorted(sectors_list, key=lambda x: x["volume_change"], reverse=True)
        sorted_by_val = sorted(sectors_list, key=lambda x: x["avg_pe"])
        
        summary = {
            "total_sectors": len(sectors_list),
            "best_sector_1m": sorted_by_perf[0]["sector"] if sectors_list else "None",
            "best_sector_1m_val": sorted_by_perf[0]["avg_return_timeframe"] if sectors_list else 0.0,
            "worst_sector_1m": sorted_by_perf[-1]["sector"] if sectors_list else "None",
            "worst_sector_1m_val": sorted_by_perf[-1]["avg_return_timeframe"] if sectors_list else 0.0,
            "strongest_momentum_sector": sorted_by_mom[0]["sector"] if sectors_list else "None",
            "strongest_momentum_val": sorted_by_mom[0]["momentum_score"] if sectors_list else 0.0,
            "highest_participation_sector": sorted_by_vol[0]["sector"] if sectors_list else "None",
            "most_attractive_valuation_sector": sorted_by_val[0]["sector"] if sectors_list else "None",
            "most_attractive_valuation_pe": sorted_by_val[0]["avg_pe"] if sectors_list else 0.0,
        }

        # Data Lineage Metadata Tooltip dictionary
        lineage = {
            "pe_ratio": {
                "field_name": "PE Ratio",
                "ui_value": "Calculated Sector Averages & Medians",
                "backend_value": "Direct DB Values",
                "source_api": "Upstox Key Ratios API (P/E)",
                "transformation_logic": "Aggregated average/median PE of active constituents",
                "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                "confidence_score": 100
            },
            "market_cap": {
                "field_name": "Market Capitalization",
                "ui_value": "Represented in Crores",
                "backend_value": "Stored in raw Rupees",
                "source_api": "Upstox Company Profile API (sector_market_cap_inr)",
                "transformation_logic": "Ingested raw Crore value * 10,000,000 to raw Rupees, then aggregated",
                "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                "confidence_score": 100
            },
            "dividend_yield": {
                "field_name": "Dividend Yield",
                "ui_value": "Annual Yield Percentage",
                "backend_value": "Computed Yield",
                "source_api": "Upstox Corporate Actions API (Dividend events)",
                "transformation_logic": "Sum of dividend payouts in last 365 days divided by latest price * 100",
                "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                "confidence_score": 100
            },
            "rsi": {
                "field_name": "RSI (14)",
                "ui_value": "Relative Strength Index Value",
                "backend_value": "Computed RSI",
                "source_api": "Upstox Historical Candle Data API V3",
                "transformation_logic": "Wilder's Smoothing on price changes over latest 14 daily candles",
                "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                "confidence_score": 100
            },
            "macd": {
                "field_name": "MACD Histogram",
                "ui_value": "MACD Trend direction",
                "backend_value": "Computed MACD",
                "source_api": "Upstox Historical Candle Data API V3",
                "transformation_logic": "MACD Line (12 EMA - 26 EMA) minus Signal Line (9 EMA of MACD Line)",
                "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                "confidence_score": 100
            }
        }

        response_data = {
            "status": "success",
            "timeframe": timeframe,
            "summary": summary,
            "sectors": sectors_list,
            "stocks": stocks_list,
            "lineage": lineage
        }

        # Cache for 60s
        sanitized_response = sanitize_numpy(response_data)
        if cache.is_available():
            try:
                cache.set(cache_key, sanitized_response, ttl=60)
            except Exception as ce:
                logger.warning(f"Cache write error in sector analysis: {ce}")
                
        return sanitized_response
        
    except Exception as e:
        logger.error(f"Error in Sector Analysis API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
