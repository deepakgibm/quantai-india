import yfinance as yf
import pandas as pd
import logging
import asyncio
import requests
from datetime import datetime
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
                timeout=2.5
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
    """Fetch Nifty 100 top movers from yfinance using fast batch download"""
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import text
        
        # 1. Fetch symbols dynamically from instrument_master (new schema)
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT symbol FROM instrument_master 
                WHERE is_active = TRUE AND exchange = 'NSE' AND series = 'EQ'
                ORDER BY symbol
                LIMIT 30
            """))
            symbols = [r[0] for r in result.fetchall()]
        
        if not symbols:
            logger.warning("No symbols found in instrument_master for yfinance fallback")
            return {"error": "No symbols available for analysis"}
        
        logger.info(f"yfinance fallback: batch downloading {len(symbols)} symbols")
            
        NIFTY_SYMBOLS = [f"{s}.NS" for s in symbols]
        tickers_str = " ".join(NIFTY_SYMBOLS)
        
        # Use session with User-Agent to avoid blocking
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Fast batch download - use 1d period with 1m interval to get latest prices
        try:
            data = await asyncio.wait_for(
                asyncio.to_thread(
                    yf.download, 
                    tickers_str, 
                    period="1d",  # Just today's data
                    interval="1m",  # 1-minute bars give current price
                    progress=False, 
                    group_by='ticker',
                    session=session
                ),
                timeout=30.0  # 30 second timeout
            )
        except asyncio.TimeoutError:
            logger.warning("yfinance batch download timed out")
            return {"error": "Timeout fetching market data"}

        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            logger.warning("yfinance returned no data")
            return {"error": "No market data available"}
        
        movers = []
        
        for full_symbol in NIFTY_SYMBOLS:
            try:
                symbol = full_symbol.replace(".NS", "")
                
                # Get ticker's data - handle both single and multi-ticker DataFrames
                if len(NIFTY_SYMBOLS) > 1 and full_symbol in data.columns.get_level_values(0):
                    ticker_data = data[full_symbol]
                elif len(NIFTY_SYMBOLS) == 1:
                    ticker_data = data
                else:
                    continue
                
                # Drop NaN rows for valid Close prices
                valid_rows = ticker_data.dropna(subset=['Close']) if 'Close' in ticker_data.columns else pd.DataFrame()
                
                if valid_rows.empty or len(valid_rows) < 1:
                    continue
                
                # Latest price is the last valid row
                ltp = float(valid_rows['Close'].iloc[-1])
                day_high = float(valid_rows['High'].max()) if 'High' in valid_rows else ltp
                day_low = float(valid_rows['Low'].min()) if 'Low' in valid_rows else ltp
                volume = int(valid_rows['Volume'].sum()) if 'Volume' in valid_rows else 0
                
                # Get previous close from the first row's Open (start of day represents previous close continuation)
                prev_close = float(valid_rows['Open'].iloc[0]) if 'Open' in valid_rows else ltp
                
                if ltp <= 0 or prev_close <= 0:
                    continue
                    
                change_pct = ((ltp - prev_close) / prev_close) * 100
                
                movers.append({
                    "symbol": symbol,
                    "ltp": round(ltp, 2),
                    "change_pct": round(change_pct, 2),
                    "prev_close": round(prev_close, 2),
                    "volume": volume,
                    "day_high": round(day_high, 2),
                    "day_low": round(day_low, 2)
                })
            except Exception as e:
                logger.debug(f"yfinance processing failed for {full_symbol}: {e}")
                continue
        
        logger.info(f"yfinance processed {len(movers)} symbols from batch download")
        
        if not movers:
            return {"error": "No live market data available"}
                
        # Sort and pick top 5 gainers and losers
        movers.sort(key=lambda x: x['change_pct'], reverse=True)
        gainers = [m for m in movers if m['change_pct'] > 0][:5]
        losers = sorted([m for m in movers if m['change_pct'] < 0], key=lambda x: x['change_pct'])[:5]
        
        return {
            "as_of": datetime.now().isoformat(),
            "gainers": gainers,
            "losers": losers,
            "source": "yfinance_live",
            "is_market_hours": True
        }
    except Exception as e:
        logger.error(f"yfinance top movers fetch failed: {e}")
        return {"error": str(e)}

