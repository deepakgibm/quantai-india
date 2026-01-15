import yfinance as yf
import pandas as pd
import logging
import asyncio
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Mapping from internal/Upstox names to yfinance tickers
INDEX_TICKER_MAP = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "INDIA VIX": "^INDIAVIX"
}

# Symbols will be fetched dynamically from the database

async def fetch_live_indices_yfinance() -> List[Dict[str, Any]]:
    """Fetch indices from yfinance as a fallback"""
    results = []
    try:
        # Use session with User-Agent to avoid blocking
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        tickers_str = " ".join(INDEX_TICKER_MAP.values())
        try:
            data = await asyncio.wait_for(
                asyncio.to_thread(yf.download, tickers_str, period="2d", interval="1m", progress=False, group_by='ticker', session=session),
                timeout=15.0
            )
        except Exception as e:
            logger.warning(f"yfinance indices download failed/timed out: {e}")
            return []
        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            # Fallback for 429 or no data
            return []
        
        for name, ticker in INDEX_TICKER_MAP.items():
            try:
                ticker_data = data[ticker] if len(INDEX_TICKER_MAP) > 1 else data
                
                if ticker_data.empty:
                    continue
                    
                # Latest row
                latest = ticker_data.iloc[-1]
                # For indices, we need to be careful: 
                ltp = 0
                prev_close = 0

                if not ticker_data.empty:
                    # Filter only rows with Close values
                    valid_rows = ticker_data.dropna(subset=['Close'])
                    if not valid_rows.empty:
                        ltp = valid_rows['Close'].iloc[-1]
                        
                        # Get previous close by looking for a different day
                        latest_date = valid_rows.index[-1].date()
                        for i in range(len(valid_rows)-2, -1, -1):
                            if valid_rows.index[i].date() < latest_date:
                                prev_close = valid_rows['Close'].iloc[i]
                                break
                        
                        if not prev_close:
                            # Fallback to the first available close if no previous day's close found
                            prev_close = valid_rows['Close'].iloc[0]
                
                # If still no price, try ticker.info (The "AlphaPrime" way)
                if not ltp or ltp <= 0:
                    try:
                        ticker_obj = yf.Ticker(ticker)
                        ltp = ticker_obj.info.get('currentPrice') or ticker_obj.info.get('regularMarketPrice')
                        prev_close = ticker_obj.info.get('regularMarketPreviousClose') or ticker_obj.info.get('previousClose')
                    except:
                        pass

                if not ltp or ltp <= 0:
                    continue
                
                net_change = ltp - prev_close
                percent = (net_change / prev_close) * 100 if prev_close else 0
                
                results.append({
                    "name": name,
                    "value": round(float(ltp), 2),
                    "change": round(float(net_change), 2),
                    "percent": round(float(percent), 2),
                    "source": "yfinance"
                })
            except Exception as e:
                logger.warning(f"Failed to process yfinance data for {name}: {e}")
                
        return results
    except Exception as e:
        logger.error(f"yfinance indices fetch failed: {e}")
        return []

async def fetch_top_movers_yfinance() -> Dict[str, Any]:
    """Fetch Nifty 100 top movers from yfinance as fallback"""
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import select
        from models_ml import Nifty100Daily
        
        # 1. Fetch symbols dynamically from the database
        async with AsyncSessionLocal() as db:
            stmt = select(Nifty100Daily.symbol).distinct()
            res = await db.execute(stmt)
            symbols = [r[0] for r in res.fetchall()][:20]  # Take top 20 symbols from DB
        
        if not symbols:
            logger.warning("No symbols found in database for yfinance fallback")
            return {"error": "No symbols available for analysis"}
            
        NIFTY_100_FALLBACK_SYMBOLS = [f"{s}.NS" for s in symbols]
        
        # Use session with User-Agent to avoid blocking
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        tickers_str = " ".join(NIFTY_100_FALLBACK_SYMBOLS)
        try:
            # We fetch 5 days of daily data for previous close and 1m data for today's price
            # But to keep it simple and avoid many calls, we fetch '1d' and handle the rows.
            data = await asyncio.wait_for(
                asyncio.to_thread(yf.download, tickers_str, period="5d", interval="1d", progress=False, group_by='ticker', session=session),
                timeout=15.0
            )
        except Exception as te:
            logger.warning(f"yfinance top movers timed out/failed: {te}")
            return {"error": "Timeout fetching market data"}

        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            return {"error": "No market data available"}
        
        # Determine today's date in IST-like comparison
        # yfinance dates are usually UTC but indexed by date.
        movers = []
        for full_symbol in NIFTY_100_FALLBACK_SYMBOLS:
            try:
                symbol = full_symbol.replace(".NS", "")
                ticker_data = data[full_symbol].dropna()
                
                if ticker_data.empty or len(ticker_data) < 2:
                    continue
                    
                # Improved yFinance detail fetching (same logic as live_price_enricher)
                ltp = 0
                prev_close = 0
                
                if not ticker_data.empty:
                    # Filter only rows with Close values
                    valid_rows = ticker_data.dropna(subset=['Close'])
                    if not valid_rows.empty:
                        ltp = valid_rows['Close'].iloc[-1]
                        
                        # Get previous close by looking for a different day
                        latest_date = valid_rows.index[-1].date()
                        for i in range(len(valid_rows)-2, -1, -1):
                            if valid_rows.index[i].date() < latest_date:
                                prev_close = valid_rows['Close'].iloc[i]
                                break
                        
                        if not prev_close:
                            prev_close = valid_rows['Close'].iloc[0]
                
                # If still no price, try ticker.info (The "AlphaPrime" way)
                if not ltp or ltp <= 0:
                    try:
                        ticker_obj = yf.Ticker(full_symbol)
                        ltp = ticker_obj.info.get('currentPrice') or ticker_obj.info.get('regularMarketPrice')
                        prev_close = ticker_obj.info.get('regularMarketPreviousClose') or ticker_obj.info.get('previousClose')
                    except:
                        pass

                if not ltp or ltp <= 0:
                    continue
                    
                change_pct = ((ltp - prev_close) / prev_close) * 100 if prev_close else 0
                
                movers.append({
                    "symbol": symbol,
                    "ltp": round(float(ltp), 2),
                    "change_pct": round(float(change_pct), 2),
                    "prev_close": round(float(prev_close), 2),
                    "volume": int(ticker_data.iloc[-1]['Volume']) if not ticker_data.empty and 'Volume' in ticker_data.iloc[-1] else 0,
                    "day_high": round(float(ticker_data.iloc[-1]['High']), 2) if not ticker_data.empty else round(float(ltp), 2),
                    "day_low": round(float(ticker_data.iloc[-1]['Low']), 2) if not ticker_data.empty else round(float(ltp), 2)
                })
            except Exception as e:
                continue
                
        # Sort and pick top 5 gainers and losers
        movers.sort(key=lambda x: x['change_pct'], reverse=True)
        gainers = [m for m in movers if m['change_pct'] > 0][:5]
        losers = sorted([m for m in movers if m['change_pct'] < 0], key=lambda x: x['change_pct'])[:5]
        
        return {
            "as_of": datetime.now().isoformat(),
            "gainers": gainers,
            "losers": losers,
            "source": "yfinance",
            "is_market_hours": False # yfinance for NSE is usually delayed
        }
    except Exception as e:
        logger.error(f"yfinance top movers fetch failed: {e}")
        return {"error": str(e)}

