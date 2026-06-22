
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from services.upstox_client import get_upstox_client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings

# Create sync engine for fallback queries
_sync_engine = create_engine(settings.SYNC_DATABASE_URL)
_SyncSession = sessionmaker(bind=_sync_engine)

class ResearchAgent:
    """
    Agent 1: Research Agent
    Goal: Perform deep research on stocks (Market Data, Technicals, ML Score).
    """
    
    def __init__(self):
        self.client = get_upstox_client()
        self.db = _SyncSession()
    
    def _get_fallback_quote_from_db(self, symbol: str) -> Optional[Dict]:
        """
        Fallback: Get latest quote from database when Upstox API fails.
        """
        try:
            from sqlalchemy import text
            # Use raw SQL to join stock_candle and instrument_master
            sql = text("""
                SELECT sc.candle_ts, sc.open, sc.high, sc.low, sc.close, sc.volume
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE im.symbol = :symbol AND sc.timeframe = 1440
                ORDER BY sc.candle_ts DESC
                LIMIT 1
            """)
            result = self.db.execute(sql, {"symbol": symbol}).fetchone()
            
            if result:
                ts, o, h, l, c, v = result
                print(f"📊 Using database fallback for {symbol} (date: {ts.date()})")
                return {
                    "symbol": symbol,
                    "timestamp": ts,
                    "open": float(o),
                    "high": float(h),
                    "low": float(l),
                    "close": float(c),
                    "last_price": float(c),
                    "volume": int(v or 0),
                }
            return None
        except Exception as e:
            print(f"⚠️ Database fallback error for {symbol}: {e}")
            return None
    
    def _get_historical_from_db(self, symbol: str, days: int = 150) -> pd.DataFrame:
        """
        Fallback: Get historical data from database when Upstox API fails.
        """
        try:
            from sqlalchemy import text
            from_date = datetime.now() - timedelta(days=days)
            
            sql = text("""
                SELECT sc.candle_ts as timestamp, sc.open, sc.high, sc.low, sc.close, sc.volume
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE im.symbol = :symbol AND sc.timeframe = 1440
                AND sc.candle_ts >= :from_date
                ORDER BY sc.candle_ts ASC
            """)
            result = self.db.execute(sql, {"symbol": symbol, "from_date": from_date})
            rows = result.fetchall()
            
            if rows:
                data = [{
                    "timestamp": r[0],
                    "open": float(r[1]),
                    "high": float(r[2]),
                    "low": float(r[3]),
                    "close": float(r[4]),
                    "volume": int(r[5] or 0)
                } for r in rows]
                return pd.DataFrame(data)
            return pd.DataFrame()
        except Exception as e:
            print(f"⚠️ Database historical fallback error for {symbol}: {e}")
            return pd.DataFrame()

        
    async def analyze(self, symbols: List[str]) -> List[Dict[str, Any]]:
        print(f"🕵️ Research Agent: Analyzing {len(symbols)} stocks...")
        results = []
        
        # Get instrument keys from database first
        symbol_map = {}
        try:
            from sqlalchemy import text
            res = self.db.execute(text(
                "SELECT symbol, instrument_key FROM instrument_master "
                "WHERE is_active = TRUE AND exchange = 'NSE' AND series = 'EQ' "
                "AND instrument_key IS NOT NULL"
            ))
            for row in res:
                if row[0] and row[1]:
                    symbol_map[row[0].strip()] = row[1].strip()
        except Exception as e:
            print(f"⚠️ Failed to load symbols from DB: {e}")

        if not symbol_map:
            nifty_symbols = await self.client.get_nifty_200_symbols()
            symbol_map = {s: k for s, k in nifty_symbols}
        
        for symbol in symbols:
            if symbol not in symbol_map:
                print(f"⚠️ Symbol {symbol} not found in instrument list. Skipping.")
                continue
                
            key = symbol_map[symbol]
            
            # 1. Fetch Market Data (Live Quote) - with DB/cache first
            quote = None
            try:
                from services.upstox_price_resolver import get_price_resolver
                resolver = get_price_resolver()
                res = await resolver.get_price(symbol)
                if res and res.get("price"):
                    quote = {
                        "symbol": symbol,
                        "timestamp": res.get("timestamp"),
                        "open": res.get("open", 0.0),
                        "high": res.get("high", 0.0),
                        "low": res.get("low", 0.0),
                        "close": res.get("close", 0.0),
                        "last_price": res.get("price", 0.0),
                        "volume": res.get("volume", 0),
                    }
            except Exception:
                pass

            if not quote:
                quote = self._get_fallback_quote_from_db(symbol)

            if not quote:
                quote = await self.client.get_live_quote(key, symbol)

            if not quote:
                print(f"❌ No data available for {symbol} (API and DB both failed)")
                continue
                
            # 2. Fetch Historical Data (for Technicals) - with DB first
            # Fetch last 150 days for daily indicators
            to_date = datetime.now()
            from_date = to_date - timedelta(days=150)
            
            hist_df = self._get_historical_from_db(symbol, days=150)
            
            if hist_df.empty:
                print(f"📡 Database empty. Calling Upstox API historical data for {symbol}")
                hist_df = await self.client.get_historical_data(
                    symbol=symbol,
                    instrument_key=key,
                    from_date=from_date,
                    to_date=to_date,
                    interval="1day"
                )
            
            technicals = self._calculate_technicals(hist_df)
            ml_score = self._calculate_ml_score(technicals)
            
            result = {
                "symbol": symbol,
                "ltp": quote.get("last_price", 0),
                "change_percent": 0.0, # TODO: Calculate if close available
                "volume": quote.get("volume", 0),
                "trend_score": technicals["trend_score"],
                "ml_score": ml_score,
                "technical_summary": technicals["summary"],
                "52_week_high": technicals["high_52w"],
                "52_week_low": technicals["low_52w"],
                "rsi": technicals["rsi"],
                "macd": technicals["macd"],
                "overall_research_summary": f"Trend: {technicals['trend']}. ML Score: {ml_score}/100."
            }
            results.append(result)
            
        return results

    def _calculate_technicals(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {
                "trend_score": 50, "summary": "No Data", "high_52w": 0, "low_52w": 0, 
                "rsi": 50, "macd": 0, "trend": "Neutral"
            }
            
        # Simple Technicals
        close = df['close']
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1] if not rs.empty else 50
        
        # MACD
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_val = macd.iloc[-1] if not macd.empty else 0
        signal_val = signal.iloc[-1] if not signal.empty else 0
        
        # 52 Week High/Low
        high_52w = df['high'].max()
        low_52w = df['low'].min()
        
        # Trend Score (0-100)
        score = 50
        if rsi > 50: score += 10
        if rsi > 70: score -= 5 # Overbought
        if macd_val > signal_val: score += 15
        if close.iloc[-1] > close.rolling(50).mean().iloc[-1]: score += 15
        if close.iloc[-1] > close.rolling(200).mean().iloc[-1]: score += 10
        
        score = min(100, max(0, score))
        
        trend = "Bullish" if score > 60 else "Bearish" if score < 40 else "Neutral"
        
        return {
            "trend_score": score,
            "summary": f"RSI: {rsi:.1f}, MACD: {'Bullish' if macd_val > signal_val else 'Bearish'}",
            "high_52w": high_52w,
            "low_52w": low_52w,
            "rsi": rsi,
            "macd": macd_val,
            "trend": trend
        }

    def _calculate_ml_score(self, technicals: Dict) -> int:
        # Placeholder for complex ML model
        # In reality, this would load a trained model
        base_score = technicals["trend_score"]
        # Add some randomness or other factors
        return int(base_score * 0.9 + np.random.randint(0, 10))
