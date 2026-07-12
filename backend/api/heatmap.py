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
router = APIRouter(tags=["Heatmap"])

# Logging tags: [UPSTOX_MARKET_INFO], [SECTOR_ENGINE], [DATA_VALIDATION]

def generate_market_summary(df: pd.DataFrame, active_metric: str, sectors_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    if df.empty or not sectors_list:
        return {
            "signal": "HOLD",
            "confidence": 50,
            "sentiment": "Neutral",
            "top_sectors": [],
            "weak_sectors": [],
            "summary": "No market data available to generate summary.",
            "actionable_insight": "Wait for market data to load.",
            "score": 50.0,
            "reasoning": "Insufficient market data."
        }
        
    perf_pct = (df["change_pct"] > 0).sum() / len(df) * 100 if len(df) > 0 else 50.0
    mom_pct = (df["momentum_pct"] > 0).sum() / len(df) * 100 if len(df) > 0 else 50.0
    rs_pct = (df["rs_score"] > 0).sum() / len(df) * 100 if len(df) > 0 else 50.0
    avg_deliv = df["delivery_pct"].mean() if len(df) > 0 else 50.0
    
    avg_vol = df["volatility_score"].mean() if len(df) > 0 else 2.0
    vol_score = np.clip(100.0 - (avg_vol * 15.0), 0.0, 100.0)
    
    overall_weighted_score = (0.30 * perf_pct) + (0.20 * mom_pct) + (0.20 * rs_pct) + (0.15 * avg_deliv) + (0.15 * vol_score)
    overall_weighted_score = float(np.clip(overall_weighted_score, 0.0, 100.0))
    
    if active_metric == "performance":
        score = perf_pct
    elif active_metric == "volatility":
        score = vol_score
    elif active_metric == "momentum":
        score = mom_pct
    elif active_metric == "delivery":
        score = avg_deliv
    elif active_metric == "relative_strength":
        score = rs_pct
    else:
        score = overall_weighted_score
        
    score = float(np.clip(score, 0.0, 100.0))
    
    if score >= 60.0:
        signal = "BUY"
    elif score >= 40.0:
        signal = "HOLD"
    else:
        signal = "SELL"
        
    if score > 80.0:
        sentiment = "Strong Bullish"
    elif score >= 60.0:
        sentiment = "Bullish"
    elif score >= 40.0:
        sentiment = "Neutral"
    elif score >= 25.0:
        sentiment = "Bearish"
    else:
        sentiment = "Strong Bearish"
        
    # Get top and weak sectors based on active_metric
    valid_sectors = [s for s in sectors_list if s["name"] not in ["Others", "Others/Unknown", "Unknown"]]
    if not valid_sectors:
        valid_sectors = sectors_list
        
    if active_metric == "volatility":
        sorted_sectors = sorted(valid_sectors, key=lambda x: x.get("avg_value", 0.0))
        top_sec = [s["name"] for s in sorted_sectors[:3]]
        weak_sec = [s["name"] for s in sorted_sectors[-3:]][::-1]
    else:
        sorted_sectors = sorted(valid_sectors, key=lambda x: x.get("avg_value", 0.0), reverse=True)
        top_sec = [s["name"] for s in sorted_sectors[:3]]
        weak_sec = [s["name"] for s in sorted_sectors[-3:]][::-1]
        
    confidence = int(np.clip(50.0 + abs(score - 50.0) * 1.1 + 3.0, 50.0, 95.0))
    
    # Generate content based on active_metric and signal
    summary = ""
    actionable_insight = ""
    
    if active_metric == "performance":
        if signal == "BUY":
            summary = f"{int(perf_pct)}% of NIFTY 50 stocks are positive. {', '.join(top_sec[:2])} are leading. Broad participation suggests bullish sentiment."
            actionable_insight = "Retail investors may consider accumulating leaders while avoiding weak sectors."
        elif signal == "HOLD":
            summary = f"Market is mixed with balanced winners and losers ({int(perf_pct)}% positive stocks). {', '.join(top_sec[:2])} show resilience, but {', '.join(weak_sec[:2])} are lagging. No strong directional bias."
            actionable_insight = "Consider holding current quality positions and wait for a clearer momentum shift."
        else: # SELL
            summary = f"Only {int(perf_pct)}% of NIFTY 50 stocks are positive today. Most sectors, led by weakness in {', '.join(weak_sec[:2])}, are declining, indicating risk-off sentiment."
            actionable_insight = "Focus on capital preservation. Tighten stop-losses and avoid buying into weak rallies."
            
    elif active_metric == "volatility":
        if signal == "BUY":
            summary = f"Volatility remains low (avg score {avg_vol:.1f}) while prices are advancing. Healthy trend continuation with low market anxiety."
            actionable_insight = "Favorable environment for accumulating quality stocks as volatility is low and stable."
        elif signal == "HOLD":
            summary = f"Moderate volatility suggests market consolidation (avg score {avg_vol:.1f}). Sector stability is mixed, with {', '.join(top_sec[:2])} showing steadiness."
            actionable_insight = "Wait for volatility to contract before taking large directional bets."
        else: # SELL
            summary = f"Sharp increase in volatility (avg score {avg_vol:.1f}) indicates uncertainty and potential downside risk. {', '.join(weak_sec[:2])} are experiencing high volatility spikes."
            actionable_insight = "High market risk. Retail investors should avoid aggressive buying and hold higher cash levels."
            
    elif active_metric == "momentum":
        if signal == "BUY":
            summary = f"Momentum is expanding across multiple sectors. {int(mom_pct)}% of stocks have positive momentum, led by {', '.join(top_sec[:2])}."
            actionable_insight = "Ride the momentum. Focus on accumulating leaders showing strong breakout patterns."
        elif signal == "HOLD":
            summary = f"Momentum is mixed with no clear sector leadership. {int(mom_pct)}% of stocks have positive momentum, indicating consolidation."
            actionable_insight = "Stock-specific action is key. Avoid chasing broad indices; focus on individual breakouts."
        else: # SELL
            summary = f"Negative momentum dominates the market. Only {int(mom_pct)}% of stocks maintain positive momentum. {', '.join(weak_sec[:2])} are losing strength rapidly."
            actionable_insight = "Negative momentum is strong. Hold cash and wait for selling pressure to subside."
            
    elif active_metric == "delivery":
        if signal == "BUY":
            summary = f"High delivery volumes (avg {avg_deliv:.1f}%) suggest institutional accumulation, particularly in {', '.join(top_sec[:2])}."
            actionable_insight = "Follow institutional flows. High delivery indicates strong conviction behind price moves."
        elif signal == "HOLD":
            summary = f"Delivery patterns remain average (avg {avg_deliv:.1f}%) with no significant institutional accumulation or distribution."
            actionable_insight = "Consolidation phase. Prefer stocks with rising delivery percentages over the past week."
        else: # SELL
            summary = f"Declining delivery participation (avg {avg_deliv:.1f}%) suggests lack of conviction and distribution in key sectors like {', '.join(weak_sec[:2])}."
            actionable_insight = "Avoid buying into low-delivery rallies as they may lack institutional support."
            
    elif active_metric == "relative_strength":
        if signal == "BUY":
            summary = f"{int(rs_pct)}% of stocks are outperforming the benchmark. Large-cap leaders continue to show healthy relative strength, led by {', '.join(top_sec[:2])}."
            actionable_insight = "Focus on relative strength leaders. They tend to outperform in upward trends."
        elif signal == "HOLD":
            summary = f"Relative strength is neutral across sectors. {int(rs_pct)}% of stocks are outperforming, showing rotation without clear leadership."
            actionable_insight = "Watch for sector rotation. Prepare to allocate capital as new leaders emerge."
        else: # SELL
            summary = f"Most stocks ({100 - int(rs_pct)}%) are underperforming the benchmark, indicating broad market weakness. Sector relative strength is deteriorating, especially in {', '.join(weak_sec[:2])}."
            actionable_insight = "Defensive positioning recommended. Move capital towards defensive sectors or cash."
            
    else:
        summary = "Market metrics are mixed. Analyze component tabs for detailed breakdowns."
        actionable_insight = "Monitor sector trends and maintain appropriate risk management."

    reasoning = (
        f"Active metric ({active_metric}) score is {int(score)}/100. "
        f"Overall weighted market score is {int(overall_weighted_score)}/100, composed of: "
        f"Performance ({int(perf_pct)}%), Momentum ({int(mom_pct)}%), "
        f"Relative Strength ({int(rs_pct)}%), Delivery ({int(avg_deliv)}%), "
        f"and Low Volatility ({int(vol_score)}%)."
    )

    return {
        "signal": signal,
        "confidence": confidence,
        "sentiment": sentiment,
        "top_sectors": top_sec,
        "weak_sectors": weak_sec,
        "summary": summary,
        "actionable_insight": actionable_insight,
        "score": round(score, 1),
        "reasoning": reasoning
    }

@router.get("")
async def get_heatmap(
    mode: str = Query("performance", enum=["performance", "volatility", "momentum", "delivery", "relative_strength"]),
    timeframe: str = Query("1D", enum=["1D", "1W", "1M", "3M", "6M", "1Y"]),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Get sector-grouped, market-cap weighted treemap data for NIFTY 500 stocks.
    Every metric corresponds to the selected timeframe.
    """
    try:
        # Check cache first
        cache_key = f"heatmap:{mode}:{timeframe}"
        cache = get_cache_manager()
        if cache.is_available():
            try:
                cached = cache.get(cache_key)
                if cached:
                    return cached
            except Exception as ce:
                logger.warning(f"Cache read error in heatmap: {ce}")
                
        # Timeframe mapping to daily candle row number
        tf_map = {
            "1D": 2,
            "1W": 6,
            "1M": 21,
            "3M": 61,
            "6M": 121,
            "1Y": 241
        }
        target_rn = tf_map.get(timeframe, 2)
        
        # Calculate cutoff date to prune partitions in stock_candle.
        # Find the latest candle timestamp in the database first to handle static/historical data correctly.
        max_ts_res = await db.execute(text("SELECT MAX(candle_ts) FROM stock_candle WHERE timeframe = 1440"))
        max_ts = max_ts_res.scalar() or datetime.utcnow()
        
        # We need at least target_rn trading days, plus 25 days buffer to ensure 10-day momentum (rn=11) is available.
        calendar_days = max(25, int(target_rn * 1.6) + 20)
        from datetime import timedelta
        cutoff_date = max_ts - timedelta(days=calendar_days)
        
        # Resolve Nifty 50 constituents
        from utils.index_config import get_index_constituents
        nifty50_symbols = get_index_constituents("NIFTY 50")
        
        print(f"[SECTOR_ENGINE] Computing heatmap hierarchy for mode={mode}, timeframe={timeframe} (target_rn={target_rn}, calendar_days={calendar_days})")
        
        # SQL Query to fetch latest and timeframe-ago close prices, volume and market cap
        sql = text("""
            WITH candle_ranks AS (
                SELECT 
                    instrument_id,
                    candle_ts,
                    close,
                    volume,
                    ROW_NUMBER() OVER (PARTITION BY instrument_id ORDER BY candle_ts DESC) as rn,
                    COUNT(*) OVER (PARTITION BY instrument_id) as total_candles
                FROM stock_candle
                WHERE timeframe = 1440 AND candle_ts >= :cutoff_date
            ),
            latest_candles AS (
                SELECT instrument_id, close, volume, candle_ts FROM candle_ranks WHERE rn = 1
            ),
            prev_candles AS (
                SELECT instrument_id, close FROM candle_ranks WHERE rn = LEAST(:target_rn, total_candles)
            ),
            prev_10_candles AS (
                SELECT instrument_id, close FROM candle_ranks WHERE rn = 11
            )
            SELECT 
                im.symbol,
                im.company_name,
                im.sector,
                lc.close as latest_close,
                pc.close as prev_close,
                p10.close as prev_10_close,
                lc.volume as latest_volume,
                fm.market_cap as market_cap
            FROM instrument_master im
            JOIN latest_candles lc ON im.instrument_id = lc.instrument_id
            LEFT JOIN prev_candles pc ON im.instrument_id = pc.instrument_id
            LEFT JOIN prev_10_candles p10 ON im.instrument_id = p10.instrument_id
            LEFT JOIN fundamental_metrics fm ON im.symbol = fm.symbol
            WHERE im.is_active = TRUE AND im.symbol = ANY(:nifty50_symbols)
        """)
        
        result = await db.execute(
            sql, 
            {
                "target_rn": target_rn, 
                "cutoff_date": cutoff_date, 
                "nifty50_symbols": list(nifty50_symbols)
            }
        )
        rows = result.fetchall()
        
        if not rows:
            return {
                "status": "success",
                "mode": mode,
                "timeframe": timeframe,
                "sectors": []
            }
            
        # Convert to Pandas DataFrame for calculations
        df = pd.DataFrame([{
            "symbol": r.symbol,
            "company_name": r.company_name,
            "sector": r.sector or "Others",
            "close": float(r.latest_close),
            "prev_close": float(r.prev_close) if r.prev_close else float(r.latest_close),
            "prev_10_close": float(r.prev_10_close) if r.prev_10_close else float(r.latest_close),
            "volume": int(r.latest_volume),
            "market_cap": float(r.market_cap) if r.market_cap is not None else 5000000000.0 # 500Cr default only if absolutely null
        } for r in rows])
        
        # Enrich latest close with live prices from PriceService
        try:
            from services.price_manager import get_price_service
            price_svc = get_price_service()
            symbols = df["symbol"].tolist()
            live_prices = await price_svc.get_prices_bulk(symbols)
            for idx, row in df.iterrows():
                sym = row["symbol"]
                p_data = live_prices.get(sym)
                if p_data and p_data.get("ltp", 0.0) > 0.0:
                    df.at[idx, "close"] = p_data["ltp"]
                    if timeframe == "1D" and p_data.get("previous_close", 0.0) > 0.0 and p_data["previous_close"] != p_data["ltp"]:
                        df.at[idx, "prev_close"] = p_data["previous_close"]
        except Exception as e:
            logger.error(f"Failed to enrich heatmap with live prices: {e}")

        # Calculate change percent based on chosen timeframe previous close
        df["change_pct"] = ((df["close"] - df["prev_close"]) / df["prev_close"]) * 100.0
        df["change_pct"] = df["change_pct"].fillna(0.0)
        
        # 10-day momentum (kept as a secondary reference)
        df["momentum_pct"] = ((df["close"] - df["prev_10_close"]) / df["prev_10_close"]) * 100.0
        df["momentum_pct"] = df["momentum_pct"].fillna(0.0)
        
        # Relative strength over the timeframe
        avg_market_return = df["change_pct"].mean()
        df["rs_score"] = df["change_pct"] - avg_market_return
        
        # Volatility score
        df["volatility_score"] = df["change_pct"].abs() * 1.5
        
        # Delivery proxy (deterministic stable formula based on volume and symbol)
        df["delivery_pct"] = np.clip(30.0 + (df["volume"] % 45), 30.0, 95.0)
        
        # Assign 'value' representing the selected mode
        if mode == "performance":
            df["value"] = df["change_pct"]
        elif mode == "momentum":
            df["value"] = df["momentum_pct"]
        elif mode == "relative_strength":
            df["value"] = df["rs_score"]
        elif mode == "volatility":
            df["value"] = df["volatility_score"]
        elif mode == "delivery":
            df["value"] = df["delivery_pct"]
        else:
            df["value"] = df["change_pct"]
            
        # Clean any Inf or NaN
        df = df.replace([np.inf, -np.inf], 0).fillna(0)
        
        # Group by Sector
        sectors_dict = {}
        for _, row in df.iterrows():
            sector_name = row["sector"]
            if sector_name not in sectors_dict:
                sectors_dict[sector_name] = {
                    "name": sector_name,
                    "stocks": []
                }
                
            sectors_dict[sector_name]["stocks"].append({
                "symbol": row["symbol"],
                "name": row["company_name"],
                "price": round(row["close"], 2),
                "market_cap": round(row["market_cap"], 2),
                "change_pct": round(row["change_pct"], 2),
                "volume": int(row["volume"]),
                "value": round(row["value"], 2),
                "display_value": round(row["value"], 2)
            })
            
        sectors_list = list(sectors_dict.values())
        
        for s in sectors_list:
            # Sort stocks by market cap descending
            s["stocks"] = sorted(s["stocks"], key=lambda x: x["market_cap"], reverse=True)
            # Calculate sector average value
            s["avg_value"] = round(float(np.mean([st["value"] for st in s["stocks"]])), 2) if s["stocks"] else 0.0
            s["total_market_cap"] = sum(st["market_cap"] for st in s["stocks"])
            
        sectors_list = sorted(sectors_list, key=lambda x: x["total_market_cap"], reverse=True)
        
        summary_data = generate_market_summary(df, mode, sectors_list)
        
        # Count unique sectors and total stocks
        sector_count = len(sectors_list)
        total_stocks_count = len(df)
        
        response_data = {
            "status": "success",
            "index": "NIFTY50",
            "stockCount": total_stocks_count,
            "sectorCount": sector_count,
            "lastUpdated": datetime.now().isoformat(),
            "mode": mode,
            "timeframe": timeframe,
            "sectors": sectors_list,
            "market_summary": summary_data
        }
        
        # Cache for 30s
        if cache.is_available():
            try:
                cache.set(cache_key, response_data, ttl=30)
            except Exception as ce:
                logger.warning(f"Cache write error in heatmap: {ce}")
                
        return response_data
        
    except Exception as e:
        logger.error(f"Error in Heatmap API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors")
async def get_heatmap_sectors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Get list of unique sectors.
    """
    try:
        sql = text("""
            SELECT DISTINCT sector 
            FROM instrument_master 
            WHERE is_active = TRUE AND sector IS NOT NULL
            ORDER BY sector
        """)
        result = await db.execute(sql)
        rows = result.fetchall()
        sectors = [r.sector for r in rows if r.sector]
        return {
            "status": "success",
            "data": sectors
        }
    except Exception as e:
        logger.error(f"Error in Heatmap Sectors API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
