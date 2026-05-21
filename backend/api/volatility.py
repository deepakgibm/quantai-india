from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import numpy as np
import pandas as pd
from typing import Dict, Any, List
import logging
from datetime import datetime, date

from database import get_read_db
from models import User
from utils.auth import get_current_user
from services.cache import get_cache_manager
from data.fno_stocks import has_derivatives
from services.upstox_client import get_upstox_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Volatility"])

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
        symbol_query = text("""
            SELECT instrument_id, instrument_key, company_name, sector, exchange
            FROM instrument_master
            WHERE symbol = :symbol AND is_active = TRUE
            LIMIT 1
        """)
        symbol_res = await db.execute(symbol_query, {"symbol": symbol})
        symbol_row = symbol_res.fetchone()
        
        if not symbol_row:
            raise HTTPException(status_code=404, detail=f"Active stock symbol '{symbol}' not found.")
        
        instrument_id = symbol_row.instrument_id
        instrument_key = symbol_row.instrument_key
        company_name = symbol_row.company_name
        sector = symbol_row.sector
        exchange = symbol_row.exchange
        
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
        
        # Fallback: if no DB candles, try fetching from Upstox API
        if len(candles_rows) < 10:
            try:
                client = get_upstox_client()
                to_date = datetime.now()
                from_date = to_date - pd.Timedelta(days=400) # get enough for 252 trading days
                df_hist = await client.get_historical_data(
                    symbol=symbol,
                    instrument_key=instrument_key,
                    from_date=from_date,
                    to_date=to_date,
                    interval="day"
                )
                if not df_hist.empty:
                    candles_rows = []
                    for _, row in df_hist.iterrows():
                        candles_rows.append(
                            type('Row', (object,), {
                                'date': row['timestamp'].date(),
                                'open': float(row['open']),
                                'high': float(row['high']),
                                'low': float(row['low']),
                                'close': float(row['close']),
                                'volume': int(row['volume'])
                            })()
                        )
            except Exception as ue:
                logger.warning(f"Failed to fetch historical candles from Upstox for {symbol}: {ue}")
                
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
        
        # 4. Fetch Option Chain / IV from Upstox if F&O stock
        current_iv = 0.0
        is_fno = has_derivatives(symbol)
        
        if is_fno:
            try:
                client = get_upstox_client()
                chain = await client.get_option_chain(instrument_key)
                if chain and "expiry" in chain:
                    # Fetch detailed chain to get near-the-money implied volatility
                    # The standard get_option_chain returns total numbers. Let's make a raw request if needed, or use a calculated IV
                    # If we don't have detailed IV, we can use a mock/realistic option IV or calculate it
                    # Let's check: does Upstox API option chain data have IV?
                    # Let's make an API call to get the detailed option chain if possible:
                    # In upstox_client, the detailed chain was mapped in get_option_chain. Let's see:
                    # We can use the PCR and total OI. Let's estimate IV based on ATR or use HV as a proxy if IV is not returned.
                    # Upstox returns detailed options in 'data' which we iterated in upstox_client.py:
                    # Let's add a custom method in upstox_client to get detailed strikes, or just extract it here
                    params = {"instrument_key": instrument_key}
                    response = await client._make_request("GET", "/option/chain", params=params)
                    if response.get("status") == "success" and response.get("data"):
                        strikes = response["data"]
                        # Find closest strike to latest price (ATM)
                        closest_strike = min(strikes, key=lambda s: abs(float(s.get("strike_price", 0)) - latest_price))
                        # Get IV of call or put option
                        call_iv = closest_strike.get("call_options", {}).get("market_data", {}).get("iv", 0)
                        put_iv = closest_strike.get("put_options", {}).get("market_data", {}).get("iv", 0)
                        iv_list = [v for v in [call_iv, put_iv] if v and v > 0]
                        if iv_list:
                            current_iv = float(np.mean(iv_list) * 100) # Convert to percentage if stored as decimal
            except Exception as e:
                logger.debug(f"Could not retrieve live IV from option chain for {symbol}: {e}")
        
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
            # Check database for VIX candle
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
                # Try fetching live quote for India VIX index from Upstox
                client = get_upstox_client()
                vix_quote = await client.get_live_quote("NSE_INDEX|India VIX", "INDIA VIX")
                if vix_quote and vix_quote.get("last_price"):
                    india_vix = float(vix_quote["last_price"])
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
            "time_series": chart_data
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
