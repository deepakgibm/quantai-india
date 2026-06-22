import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel
import pandas as pd

from services.upstox_client import UpstoxClient
from services.cache import get_cache_manager
from services.nifty500_fetcher import Nifty500Fetcher

logger = logging.getLogger(__name__)

class YearlyBreakoutStock(BaseModel):
    symbol: str
    instrument_key: str
    current_price: float
    yearly_high: float
    yearly_low: float
    breakout_type: str  # "Breakout", "Yearly High", "Yearly Low"
    breakout_pct: float
    volume_ratio: float
    volume_strength: str  # "Weak", "Normal", "Strong"
    change_pct: float
    industry: str
    timestamp: str

class YearlyBreakoutEngine:
    def __init__(self):
        self.upstox = UpstoxClient()
        self.fetcher = Nifty500Fetcher()
        self.cache_key = "qai:scan:yearly_breakouts"
        self.volume_threshold = 1.5

    async def get_nifty500_symbols(self) -> List[Dict]:
        """Fetch strict NIFTY 500 equity symbols from NSE."""
        try:
            # Load single source of truth for NIFTY 500
            # Nifty500Fetcher methods are sync, call them directly
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                n500_raw = await loop.run_in_executor(pool, self.fetcher.fetch_nifty_500)
            
            # Validate every symbol: 
            # 1. Must exist in nifty_500_universe
            # 2. Must be NSE Equity (EQ)
            # 3. No ETFs (check symbol name and industry)
            # 4. Hard-exclude sector = NULL / N/A
            
            valid_symbols = []
            excluded_count = 0
            for s in n500_raw:
                # Basic validation
                if not s.symbol or not s.instrument_key:
                    continue
                
                symbol_upper = s.symbol.upper()
                
                # STRICT FILTERS:
                # 1. Enforce NSE EQ type
                if not s.instrument_key.startswith("NSE_EQ|"):
                    excluded_count += 1
                    continue
                
                # 2. Exclude symbols with missing or N/A industry/sector
                industry_upper = (s.industry or "").strip().upper()
                if not s.industry or industry_upper in ["N/A", "NULL", "NONE", "", "ETF"]:
                    excluded_count += 1
                    continue
                
                # 3. Exclude ETFs by symbol patterns
                if any(ext in symbol_upper for ext in ["ETF", "ADD", "GOLD", "SILVER", "LIQUID", "IETF", "BEES"]):
                    excluded_count += 1
                    continue
                
                valid_symbols.append({
                    "symbol": s.symbol,
                    "instrument_key": s.instrument_key,
                    "industry": s.industry
                })
            
            logger.info(f"NIFTY 500 Universe: {len(n500_raw)} raw, {len(valid_symbols)} valid equity stocks. Excluded {excluded_count} (ETFs/NA).")
            return valid_symbols
            
        except Exception as e:
            logger.error(f"Error fetching NIFTY 500 symbols: {e}")
            return []

    async def process_stock(self, symbol_data: Dict) -> Optional[YearlyBreakoutStock]:
        """Fetch historical data and detect breakouts for a single stock."""
        symbol = symbol_data.get('symbol')
        instrument_key = symbol_data.get('instrument_key')
        industry = symbol_data.get('industry')
        
        if not instrument_key:
            return None

        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=375)
            
            from services.db_data_fetcher import DBDataFetcher
            db_fetcher = DBDataFetcher()
            
            loop = asyncio.get_event_loop()
            history = await loop.run_in_executor(
                None,
                db_fetcher.get_historical_data,
                symbol,
                "day",
                from_date.strftime("%Y-%m-%d"),
                to_date.strftime("%Y-%m-%d")
            )
            
            if history is None or history.empty:
                return None

            df = history.reset_index()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # 52 weeks is approx 252 trading days
            window_52w = df.iloc[-252:] if len(df) >= 252 else df
            
            yearly_high = window_52w['high'].max()
            yearly_low = window_52w['low'].min()
            current_close = df.iloc[-1]['close']
            prev_close = df.iloc[-2]['close'] if len(df) > 1 else current_close
            
            # Volume Ratio calculation
            current_volume = df.iloc[-1]['volume']
            avg_volume = window_52w['volume'].mean()
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            # Previous 52W High (excluding today)
            prev_high_52w = window_52w.iloc[:-1]['high'].max() if len(window_52w) > 1 else yearly_high
            
            # Bucketing Logic (Mutually Exclusive)
            bucket_type = "NONE"
            breakout_pct = 0
            
            # 1. 52-Week Breakout
            if current_close > prev_high_52w and volume_ratio >= self.volume_threshold:
                bucket_type = "Breakout"
                breakout_pct = ((current_close - prev_high_52w) / prev_high_52w) * 100
            
            # 2. Yearly High (Near High, Not Breakout)
            elif current_close >= yearly_high * 0.98 and current_close <= yearly_high:
                bucket_type = "Yearly High"
                breakout_pct = ((current_close - yearly_high) / yearly_high) * 100
                
            # 3. Yearly Low
            elif current_close <= yearly_low * 1.02:
                bucket_type = "Yearly Low"
                breakout_pct = ((current_close - yearly_low) / yearly_low) * 100
            
            if bucket_type == "NONE":
                return None

            # Volume Strength Label
            if volume_ratio >= 2.0:
                volume_strength = "Strong"
            elif volume_ratio >= 1.0:
                volume_strength = "Normal"
            else:
                volume_strength = "Weak"

            return YearlyBreakoutStock(
                symbol=symbol,
                instrument_key=instrument_key,
                current_price=round(float(current_close), 2),
                yearly_high=round(float(yearly_high), 2),
                yearly_low=round(float(yearly_low), 2),
                breakout_type=bucket_type,
                breakout_pct=round(float(breakout_pct), 2),
                volume_ratio=round(float(volume_ratio), 2),
                volume_strength=volume_strength,
                change_pct=round(((current_close - prev_close) / prev_close) * 100, 2),
                industry=industry,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            return None

    async def run_scanner(self, timeout: float = 30.0):
        """
        Run breakout detection for all Nifty 500 stocks.
        Uses database-driven historical data for speed and reliability.
        """
        import time
        t_start = time.time()
        logger.info("Starting Database-driven Yearly Breakout Scanner...")
        
        # Clear existing cache
        cache = get_cache_manager()
        cache.delete(self.cache_key)
        
        symbols = await self.get_nifty500_symbols()
        if not symbols:
            logger.error("No symbols found for scanning.")
            return
            
        symbols_info = {s["symbol"]: s for s in symbols}
        
        from database import get_db_session_context
        from sqlalchemy import text
        
        query = text("""
            WITH max_ts AS (
                SELECT MAX(candle_ts) as max_candle_ts 
                FROM stock_candle 
                WHERE timeframe = 1440
            ),
            ordered_candles AS (
                SELECT 
                    mk.symbol,
                    mk.instrument_key,
                    sch.candle_ts,
                    sch.close,
                    sch.high,
                    sch.low,
                    sch.volume,
                    LAG(sch.close, 1) OVER (PARTITION BY mk.symbol ORDER BY sch.candle_ts ASC) as prev_close,
                    ROW_NUMBER() OVER (PARTITION BY mk.symbol ORDER BY sch.candle_ts DESC) as rn
                FROM stock_candle sch
                JOIN instrument_master mk ON sch.instrument_id = mk.instrument_id
                CROSS JOIN max_ts
                WHERE sch.timeframe = 1440
                  AND sch.candle_ts >= max_ts.max_candle_ts - INTERVAL '400 days'
            ),
            stats AS (
                SELECT 
                    symbol,
                    MAX(high) as year_high,
                    MIN(low) as year_low,
                    AVG(volume) as avg_volume,
                    MAX(CASE WHEN rn > 1 THEN high END) as prev_year_high
                FROM ordered_candles
                CROSS JOIN max_ts
                WHERE candle_ts > max_ts.max_candle_ts - INTERVAL '365 days'
                GROUP BY symbol
            ),
            latest AS (
                SELECT 
                    symbol,
                    instrument_key,
                    close as last_price,
                    prev_close,
                    volume as last_volume,
                    candle_ts
                FROM ordered_candles
                WHERE rn = 1
            )
            SELECT 
                s.symbol,
                s.year_high,
                s.year_low,
                s.prev_year_high,
                s.avg_volume,
                l.last_price,
                l.prev_close,
                l.last_volume,
                l.candle_ts,
                l.instrument_key
            FROM stats s
            JOIN latest l ON s.symbol = l.symbol
        """)
        
        try:
            async with get_db_session_context() as session:
                db_res = await session.execute(query)
                rows = db_res.fetchall()
        except Exception as e:
            logger.error(f"Failed to query breakout candles from database: {e}")
            return
            
        # Bulk resolve live prices using UpstoxPriceResolver
        symbols_list = [r.symbol for r in rows]
        from services.upstox_price_resolver import get_upstox_price_resolver
        resolver = get_upstox_price_resolver()
        live_prices = {}
        try:
            live_prices = await resolver.get_prices_bulk(symbols_list)
            logger.info(f"Yearly Breakout: Bulk resolved prices for {len(live_prices)}/{len(symbols_list)} symbols.")
        except Exception as e:
            logger.error(f"Yearly Breakout: Bulk price resolution failed: {e}")

        results = []
        for r in rows:
            symbol = r.symbol
            instrument_key = r.instrument_key
            
            # Map industry from self.get_nifty500_symbols() info
            symbol_data = symbols_info.get(symbol, {})
            industry = symbol_data.get("industry", "N/A")
            
            high_52w = float(r.year_high) if r.year_high else 0
            low_52w = float(r.year_low) if r.year_low else 0
            prev_high_52w = float(r.prev_year_high) if r.prev_year_high else high_52w
            
            # Fetch live price from resolver
            price_data = live_prices.get(symbol)
            if price_data and price_data.get("price", 0) > 0:
                ltp = float(price_data["price"])
                prev_close = float(price_data.get("prev_close") or r.prev_close or ltp)
                price_source = price_data.get("price_source", "UNKNOWN")
                source_timestamp = price_data.get("timestamp") or datetime.now().isoformat()
            else:
                ltp = float(r.last_price) if r.last_price else 0
                prev_close = float(r.prev_close) if r.prev_close else ltp
                price_source = "DB_EOD"
                source_timestamp = r.candle_ts.isoformat() if r.candle_ts else datetime.now().isoformat()
            
            volume = float(r.last_volume) if r.last_volume else 0
            avg_volume = float(r.avg_volume) if r.avg_volume else 0
            
            volume_ratio = volume / avg_volume if avg_volume > 0 else 0
            
            bucket_type = "NONE"
            breakout_pct = 0.0
            
            # 1. 52-Week Breakout (current close > previous 52W high and volume_ratio >= 1.5)
            if prev_high_52w > 0 and ltp > prev_high_52w and volume_ratio >= self.volume_threshold:
                bucket_type = "Breakout"
                breakout_pct = ((ltp - prev_high_52w) / prev_high_52w) * 100
            
            # 2. Yearly High (Near High)
            elif high_52w > 0 and ltp >= high_52w * 0.98 and ltp <= high_52w:
                bucket_type = "Yearly High"
                breakout_pct = ((ltp - high_52w) / high_52w) * 100
                
            # 3. Yearly Low (Near Low)
            elif low_52w > 0 and ltp <= low_52w * 1.02:
                bucket_type = "Yearly Low"
                breakout_pct = ((ltp - low_52w) / low_52w) * 100
                
            if bucket_type == "NONE":
                continue
                
            # Volume Strength Label
            if volume_ratio >= 2.0:
                volume_strength = "Strong"
            elif volume_ratio >= 1.0:
                volume_strength = "Normal"
            else:
                volume_strength = "Weak"
                
            change_pct = round(((ltp - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0
            
            stock_data = {
                "symbol": symbol,
                "instrument_key": instrument_key,
                "current_price": round(ltp, 2),
                "yearly_high": round(high_52w, 2),
                "yearly_low": round(low_52w, 2),
                "breakout_type": bucket_type,
                "breakout_pct": round(breakout_pct, 2),
                "volume_ratio": round(volume_ratio, 2),
                "volume_strength": volume_strength,
                "change_pct": change_pct,
                "industry": industry,
                "price_source": price_source,
                "source_timestamp": source_timestamp,
                "timestamp": datetime.now().isoformat()
            }
            results.append(stock_data)
            
        if results:
            cache.set(self.cache_key, results, ttl=300)
            logger.info(f"Yearly Breakout Scan complete. Found {len(results)} stocks in {time.time() - t_start:.2f}s.")
        else:
            logger.warning("No breakout results found.")

    async def get_cached_results(self) -> List[Dict]:
        """Retrieve results from cache."""
        cache = get_cache_manager()
        return cache.get(self.cache_key) or []

