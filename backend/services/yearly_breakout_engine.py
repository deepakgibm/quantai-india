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
            
            history = await self.upstox.get_historical_data(
                symbol=symbol,
                instrument_key=instrument_key,
                from_date=from_date,
                to_date=to_date,
                interval="day"
            )
            
            if history.empty or len(history) < 200:
                return None

            df = history.copy()
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

    async def run_scanner(self):
        """Run breakout detection for all Nifty 500 stocks."""
        logger.info("Starting Yearly Breakout Scanner...")
        
        # Clear existing cache to ensure we don't serve stale data if the scan takes a while
        cache = get_cache_manager()
        cache.delete(self.cache_key)
        
        symbols = await self.get_nifty500_symbols()
        if not symbols:
            logger.error("No symbols found for scanning.")
            return

        results = []
        # Process in batches to respect rate limits
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            tasks = [self.process_stock(s) for s in batch]
            batch_results = await asyncio.gather(*tasks)
            
            # Enrich batch with LIVE prices for absolute accuracy before caching
            valid_batch_results = [res.dict() for res in batch_results if res]
            if valid_batch_results:
                from services.live_price_enricher import enrich_scanner_results
                enriched_batch = await enrich_scanner_results(valid_batch_results)
                
                # Recalculate breakout_pct based on enriched price if it changed
                for res in enriched_batch:
                    current_price = res.get("current_price", 0)
                    if current_price > 0:
                        if res.get("breakout_type") == "Breakout":
                            # Use high_52w from engine if available,不然 from res
                            high = res.get("yearly_high", 0)
                            if high > 0:
                                res["breakout_pct"] = round(((current_price - high) / high) * 100, 2)
                        elif res.get("breakout_type") == "Yearly Low":
                            low = res.get("yearly_low", 0)
                            if low > 0:
                                res["breakout_pct"] = round(((current_price - low) / low) * 100, 2)
                    
                results.extend(enriched_batch)
            
            await asyncio.sleep(0.1)

        if results:
            cache = get_cache_manager()
            cache.set(self.cache_key, results, ttl=3600)
            logger.info(f"Yearly Breakout Scan complete. Found {len(results)} stocks.")
        else:
            logger.warning("No breakout results found.")

    async def get_cached_results(self) -> List[Dict]:
        """Retrieve results from cache."""
        cache = get_cache_manager()
        return cache.get(self.cache_key) or []

