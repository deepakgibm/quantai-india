"""
Daily Top Gainers/Losers Snapshot ETL

Scheduled to run at 15:40 IST (10 minutes after market close).
Fetches official close prices from Upstox REST API and persists snapshot.

Usage:
    python daily_snapshot_etl.py          # Run ETL
    python daily_snapshot_etl.py --check  # Check today's snapshot
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DailySnapshotETL:
    """
    ETL to snapshot official close prices from Upstox REST API.
    
    Runs after market close to capture:
    - Official LTP/close price
    - Previous close
    - Calculate change %
    - Rank and persist top 10 gainers/losers
    """
    
    TOP_N = 10  # Top 10 gainers and losers
    
    def __init__(self):
        # Convert async database URL to sync (asyncpg -> psycopg2)
        db_url = settings.DATABASE_URL
        if "asyncpg" in db_url:
            db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
        
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Create table if not exists."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_top_gainers_snapshot (
                    id SERIAL PRIMARY KEY,
                    trade_date DATE NOT NULL,
                    symbol TEXT NOT NULL,
                    company_name TEXT,
                    close_price NUMERIC(12,2) NOT NULL,
                    prev_close NUMERIC(12,2) NOT NULL,
                    change NUMERIC(12,2) NOT NULL,
                    change_percent NUMERIC(8,2) NOT NULL,
                    volume BIGINT,
                    rank INTEGER NOT NULL,
                    category TEXT DEFAULT 'GAINER',
                    data_source TEXT DEFAULT 'UPSTOX',
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(trade_date, symbol)
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_snapshot_trade_date 
                ON daily_top_gainers_snapshot(trade_date)
            """))
            conn.commit()
        logger.info("Table daily_top_gainers_snapshot ready")
    
    def get_trading_date(self) -> date:
        """Get the last completed trading date."""
        # For EOD ETL, we usually want YESTERDAY's data if running early morning
        # or Today's data if running post-market.
        now = datetime.now()
        today = now.date()
        
        # If running before 9 AM, use yesterday
        if now.hour < 9:
            target_date = today - timedelta(days=1)
        else:
            target_date = today
            
        # Adjust for weekends
        if target_date.weekday() == 5:  # Saturday
            return target_date - timedelta(days=1)
        elif target_date.weekday() == 6:  # Sunday
            return target_date - timedelta(days=2)
        return target_date
    
    def is_market_closed(self) -> bool:
        """Check if market is closed (after 15:30 IST)."""
        now = datetime.now()
        if now.weekday() >= 5:  # Weekend
            return True
        current_minutes = now.hour * 60 + now.minute
        # Market closes at 15:30 (930 minutes from midnight)
        return current_minutes > 930
    
    def _load_symbols_sync(self) -> List[Dict[str, str]]:
        """Load NIFTY 500 symbols and instrument keys synchronously from DB."""
        try:
            session = self.Session()
            # Try to get from instrument_master first
            res = session.execute(text("SELECT symbol, instrument_key FROM instrument_master WHERE is_active = TRUE"))
            data = [{"symbol": r[0], "instrument_key": r[1]} for r in res]
            session.close()
            if data:
                return data
            
            # Fallback to hardcoded list (might not have instrument keys)
            fallback_symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "ADANIENT", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK"]
            return [{"symbol": sym, "instrument_key": f"NSE_EQ|{sym}"} for sym in fallback_symbols]
        except Exception as e:
            logger.error(f"Error loading symbols from DB: {e}")
            session.close()
            return []
        
        # Fallback: NIFTY 100 hardcoded symbols
        logger.info("Using hardcoded NIFTY 100 symbol list")
        return [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
            "KOTAKBANK", "SBIN", "BHARTIARTL", "BAJFINANCE", "AXISBANK", "LT",
            "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN", "DMART", "ULTRACEMCO",
            "WIPRO", "ONGC", "NTPC", "POWERGRID", "M&M", "COALINDIA", "BAJAJFINSV",
            "NESTLEIND", "TATAMOTORS", "HCLTECH", "JSWSTEEL", "TATASTEEL", "ADANIGREEN",
            "ADANIPORTS", "INDUSINDBK", "TECHM", "DRREDDY", "HDFCLIFE", "SBILIFE",
            "DIVISLAB", "CIPLA", "EICHERMOT", "BRITANNIA", "HEROMOTOCO", "HINDALCO",
            "GRASIM", "UPL", "APOLLOHOSP", "TATACONSUM", "BPCL", "DABUR", "PIDILITIND",
            "SIEMENS", "SHREECEM", "VEDL", "GODREJCP", "BIOCON", "MARICO", "COLPAL",
            "BERGEPAINT", "HAVELLS", "MCDOWELL-N", "AMBUJACEM", "ICICIPRULI", "LUPIN",
            "ACC", "JINDALSTEL", "DLF", "GAIL", "IOC", "MOTHERSON", "INDIGO",
            "TATAPOWER", "MUTHOOTFIN", "BAJAJ-AUTO", "LICI", "ADANIENT", "ZOMATO",
            "PAYTM", "NYKAA", "POLICYBZR", "CARTRADE", "DELHIVERY", "PNB", "BANKBARODA",
            "CANBK", "IDFCFIRSTB", "BANDHANBNK", "FEDERALBNK", "RBLBANK", "IDBI",
            "AUBANK", "ABCAPITAL", "L&TFH", "MFSL", "CHOLAFIN", "TATACOMM",
            "TRENT", "TORNTPHARM", "ABBOTINDIA", "PAGEIND", "NAUKRI", "PERSISTENT"
        ]
    
    async def fetch_upstox_quotes(self) -> List[Dict[str, Any]]:
        """Fetch all NIFTY 500 quotes from Upstox REST API."""
        import httpx
        
        logger.info("Fetching quotes from Upstox REST API...")
        
        # Load symbol/key pairs from database
        symbol_data = self._load_symbols_sync()
        
        if not symbol_data:
            logger.error("No symbols loaded")
            return []
        
        logger.info(f"Loaded {len(symbol_data)} symbols")
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        if not access_token:
            logger.error("UPSTOX_ACCESS_TOKEN not configured")
            return []
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        all_quotes = []
        batch_size = 50
        
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            for i in range(0, len(symbol_data), batch_size):
                batch = symbol_data[i:i + batch_size]
                # Use provided instrument_key or fallback to NSE_EQ|SYMBOL
                instrument_keys = [s.get("instrument_key") or f"NSE_EQ|{s['symbol']}" for s in batch]
                
                try:
                    # Upstox market quotes endpoint
                    url = "https://api.upstox.com/v2/market-quote/quotes"
                    # Upstox V2 quotes API uses 'instrument_key' as comma-separated list
                    params = {"instrument_key": ",".join(instrument_keys)}
                    
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        quotes = data.get("data", {})
                        
                        for key, quote in quotes.items():
                            # Extract symbol from key (NSE_EQ:RELIANCE -> RELIANCE)
                            symbol = key.split(":")[-1] if ":" in key else key.split("|")[-1]
                            
                            ltp = quote.get("last_price", 0)
                            change = quote.get("net_change", 0)
                            prev_close = ltp - change
                            
                            if ltp > 0 and prev_close > 0:
                                change_pct = (change / prev_close) * 100
                                
                                all_quotes.append({
                                    "symbol": symbol,
                                    "company_name": quote.get("name", symbol),
                                    "close_price": round(ltp, 2),
                                    "prev_close": round(prev_close, 2),
                                    "change": round(change, 2),
                                    "change_percent": round(change_pct, 2),
                                    "volume": quote.get("volume", 0)
                                })
                    else:
                        logger.warning(f"Upstox API batch {i//batch_size} returned {response.status_code}: {response.text}")
                        
                except Exception as e:
                    logger.error(f"Error fetching batch {i//batch_size}: {e}")
                
                await asyncio.sleep(0.5)  # Slightly more conservative rate limiting
        
        logger.info(f"Fetched {len(all_quotes)} valid quotes from Upstox")
        return all_quotes
    
    async def fetch_yfinance_quotes(self) -> List[Dict[str, Any]]:
        """Fallback: Fetch quotes from yfinance when Upstox fails."""
        import yfinance as yf
        import pandas as pd
        
        logger.info("Fetching quotes from yfinance (fallback - BATCH)...")
        
        symbols_data = self._load_symbols_sync()
        symbols = [s['symbol'] for s in symbols_data]
        yf_symbols = [f"{s}.NS" for s in symbols]
        
        all_quotes = []
        
        try:
            # Download 2 days of data for ALL symbols at once
            # period="2d" ensures we have 오늘의 close and yesterday's close for % change
            # auto_adjust=False is CRITICAL for official non-adjusted close prices
            data = await asyncio.to_thread(
                yf.download, yf_symbols, period="2d", interval="1d", 
                group_by='ticker', progress=False, auto_adjust=False
            )
            
            if data.empty:
                logger.warning("yfinance returned no data for the requested symbols")
                return []
            
            for symbol in symbols:
                try:
                    ticker_data = data[f"{symbol}.NS"]
                    if ticker_data.empty or len(ticker_data) < 1:
                        continue
                    
                    # If 2 days available, get prev_close
                    if len(ticker_data) >= 2:
                        ltp = float(ticker_data.iloc[-1]['Close'])
                        prev_close = float(ticker_data.iloc[-2]['Close'])
                    else:
                        ltp = float(ticker_data.iloc[-1]['Close'])
                        prev_close = ltp # Fallback
                    
                    if pd.isna(ltp) or ltp <= 0:
                        continue
                        
                    change = ltp - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close > 0 else 0
                    
                    all_quotes.append({
                        "symbol": symbol,
                        "company_name": symbol,
                        "close_price": round(ltp, 2),
                        "prev_close": round(prev_close, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_pct, 2),
                        "volume": int(ticker_data.iloc[-1].get('Volume', 0))
                    })
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"Batch yfinance fetch failed: {e}")
        
        logger.info(f"Fetched {len(all_quotes)} valid quotes from yfinance (batch)")
        return all_quotes

    
    def compute_top_gainers_losers(
        self, 
        quotes: List[Dict[str, Any]]
    ) -> tuple:
        """Compute top gainers and losers from quotes."""
        if not quotes:
            return [], []
        
        # Sort by change percent
        sorted_quotes = sorted(quotes, key=lambda x: x["change_percent"], reverse=True)
        
        # Top gainers (highest positive change)
        gainers = []
        for i, q in enumerate(sorted_quotes[:self.TOP_N]):
            if q["change_percent"] > 0:
                gainers.append({**q, "rank": i + 1, "category": "GAINER"})
        
        # Top losers (most negative change)
        losers = []
        for i, q in enumerate(reversed(sorted_quotes[-self.TOP_N:])):
            if q["change_percent"] < 0:
                losers.append({**q, "rank": -(i + 1), "category": "LOSER"})
        
        return gainers, losers
    
    def persist_snapshot(
        self,
        trade_date: date,
        gainers: List[Dict[str, Any]],
        losers: List[Dict[str, Any]]
    ) -> int:
        """Persist snapshot to database."""
        session = self.Session()
        
        try:
            # Clear existing snapshot for this date
            session.execute(
                text("DELETE FROM daily_top_gainers_snapshot WHERE trade_date = :date"),
                {"date": trade_date}
            )
            
            # Insert gainers
            for g in gainers:
                session.execute(
                    text("""
                        INSERT INTO daily_top_gainers_snapshot 
                        (trade_date, symbol, company_name, close_price, prev_close, 
                         change, change_percent, volume, rank, category, data_source)
                        VALUES (:date, :symbol, :name, :close, :prev, :change, :pct, :vol, :rank, :cat, 'UPSTOX')
                    """),
                    {
                        "date": trade_date,
                        "symbol": g["symbol"],
                        "name": g.get("company_name", g["symbol"]),
                        "close": g["close_price"],
                        "prev": g["prev_close"],
                        "change": g["change"],
                        "pct": g["change_percent"],
                        "vol": g.get("volume", 0),
                        "rank": g["rank"],
                        "cat": "GAINER"
                    }
                )
            
            # Insert losers
            for l in losers:
                session.execute(
                    text("""
                        INSERT INTO daily_top_gainers_snapshot 
                        (trade_date, symbol, company_name, close_price, prev_close, 
                         change, change_percent, volume, rank, category, data_source)
                        VALUES (:date, :symbol, :name, :close, :prev, :change, :pct, :vol, :rank, :cat, 'UPSTOX')
                    """),
                    {
                        "date": trade_date,
                        "symbol": l["symbol"],
                        "name": l.get("company_name", l["symbol"]),
                        "close": l["close_price"],
                        "prev": l["prev_close"],
                        "change": l["change"],
                        "pct": l["change_percent"],
                        "vol": l.get("volume", 0),
                        "rank": l["rank"],
                        "cat": "LOSER"
                    }
                )
            
            session.commit()
            total = len(gainers) + len(losers)
            logger.info(f"Persisted {total} records for {trade_date}")
            return total
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to persist snapshot: {e}")
            raise
        finally:
            session.close()
    
    def write_to_cache(
        self,
        trade_date: date,
        gainers: List[Dict[str, Any]],
        losers: List[Dict[str, Any]]
    ):
        """Write snapshot to Dragonfly cache."""
        try:
            from services.dragonfly_client import get_cache
            cache = get_cache()
            
            date_str = trade_date.strftime("%Y-%m-%d")
            
            # Cache gainers
            cache.set(
                f"top_gainers:{date_str}",
                {"data": gainers, "source": "UPSTOX", "trade_date": date_str},
                ttl=86400  # 24 hours
            )
            
            # Cache losers
            cache.set(
                f"top_losers:{date_str}",
                {"data": losers, "source": "UPSTOX", "trade_date": date_str},
                ttl=86400  # 24 hours
            )
            
            logger.info(f"Cached snapshot for {date_str}")
            
        except Exception as e:
            logger.warning(f"Failed to cache snapshot: {e}")
    
    async def run(self) -> Dict[str, Any]:
        """Execute the ETL pipeline."""
        start_time = datetime.now()
        trade_date = self.get_trading_date()
        
        logger.info(f"="*60)
        logger.info(f"Daily Snapshot ETL - {trade_date}")
        logger.info(f"="*60)
        
        # Step 1: Fetch quotes from Upstox (primary source)
        quotes = await self.fetch_upstox_quotes()
        data_source = "UPSTOX"
        
        # Step 1b: Fallback to yfinance if Upstox fails
        if not quotes:
            logger.warning("Upstox returned no quotes, falling back to yfinance")
            quotes = await self.fetch_yfinance_quotes()
            data_source = "YFINANCE"
        
        if not quotes:
            logger.error("No quotes fetched from any source")
            return {"status": "error", "message": "No quotes available from any source"}
        
        # Step 2: Compute top gainers/losers
        gainers, losers = self.compute_top_gainers_losers(quotes)
        
        logger.info(f"Top {len(gainers)} Gainers | Top {len(losers)} Losers")
        
        # Step 3: Persist to database
        total = self.persist_snapshot(trade_date, gainers, losers)
        
        # Step 4: Write to cache
        self.write_to_cache(trade_date, gainers, losers)
        
        # Step 5: Snapshot scanner signals from quotes
        scanner_results = self.snapshot_scanner_signals(trade_date, quotes)
        
        # Step 6: Snapshot heatmap sector data
        heatmap_results = self.snapshot_heatmap_sectors(trade_date, quotes)
        
        # Step 7: Sync official prices to primary tables (HP Scanner Source)
        sync_results = self.sync_official_prices_to_system(trade_date, quotes)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        result = {
            "status": "success",
            "trade_date": str(trade_date),
            "gainers_count": len(gainers),
            "losers_count": len(losers),
            "total_quotes": len(quotes),
            "scanner_signals": scanner_results,
            "heatmap_sectors": heatmap_results,
            "primary_sync_count": sync_results,
            "elapsed_seconds": round(elapsed, 2)
        }
        
        logger.info(f"ETL completed in {elapsed:.2f}s")
        logger.info(f"Result: {result}")
        
        return result
    
    def snapshot_scanner_signals(self, trade_date: date, quotes: List[Dict]) -> Dict[str, int]:
        """
        Compute and cache scanner signals (momentum, breakout, reversal).
        
        Uses the quote data to compute simple signal classifications.
        """
        from services.dragonfly_client import get_cache
        
        date_str = trade_date.strftime("%Y-%m-%d")
        cache = get_cache()
        
        # Classify stocks based on change percentage
        momentum_signals = []
        breakout_signals = []
        reversal_signals = []
        
        for q in quotes:
            change_pct = q.get("change_percent", 0)
            
            # Momentum: Strong directional move (>2%)
            if abs(change_pct) > 2.0:
                momentum_signals.append({
                    "symbol": q["symbol"],
                    "close_price": q["close_price"],
                    "change_percent": change_pct,
                    "signal": "BULLISH" if change_pct > 0 else "BEARISH",
                    "strength": "STRONG" if abs(change_pct) > 4 else "MODERATE"
                })
            
            # Breakout: >3% move with high absolute price
            if change_pct > 3.0:
                breakout_signals.append({
                    "symbol": q["symbol"],
                    "close_price": q["close_price"],
                    "change_percent": change_pct,
                    "signal": "BREAKOUT",
                    "prev_close": q.get("prev_close", 0)
                })
            
            # Reversal: Large negative move (potential reversal candidates)
            if change_pct < -3.0:
                reversal_signals.append({
                    "symbol": q["symbol"],
                    "close_price": q["close_price"],
                    "change_percent": change_pct,
                    "signal": "OVERSOLD",
                    "prev_close": q.get("prev_close", 0)
                })
        
        # Sort by strength
        momentum_signals.sort(key=lambda x: abs(x["change_percent"]), reverse=True)
        breakout_signals.sort(key=lambda x: x["change_percent"], reverse=True)
        reversal_signals.sort(key=lambda x: x["change_percent"])
        
        # Cache each signal type
        try:
            cache.set(f"snapshot:scanner_momentum:{date_str}", 
                     {"data": momentum_signals[:20], "count": len(momentum_signals)}, ttl=86400)
            cache.set(f"snapshot:scanner_breakout:{date_str}", 
                     {"data": breakout_signals[:20], "count": len(breakout_signals)}, ttl=86400)
            cache.set(f"snapshot:scanner_reversal:{date_str}", 
                     {"data": reversal_signals[:20], "count": len(reversal_signals)}, ttl=86400)
            
            # Also cache combined signals for HP scanner
            cache.set(f"snapshot:hp_scanner_signals:{date_str}", {
                "momentum": momentum_signals[:20],
                "breakout": breakout_signals[:20],
                "reversal": reversal_signals[:20],
                "total_signals": len(momentum_signals) + len(breakout_signals) + len(reversal_signals)
            }, ttl=86400)
            
            logger.info(f"Cached scanner signals: {len(momentum_signals)} momentum, {len(breakout_signals)} breakout, {len(reversal_signals)} reversal")
            
        except Exception as e:
            logger.warning(f"Failed to cache scanner signals: {e}")
        
        return {
            "momentum": len(momentum_signals),
            "breakout": len(breakout_signals),
            "reversal": len(reversal_signals)
        }
    
    def snapshot_heatmap_sectors(self, trade_date: date, quotes: List[Dict]) -> Dict[str, Any]:
        """
        Compute and cache sector heatmap data.
        
        Aggregates stock performance by sector.
        """
        from services.dragonfly_client import get_cache
        
        date_str = trade_date.strftime("%Y-%m-%d")
        cache = get_cache()
        
        # Load sector mapping from database
        sector_map = self._load_sector_map_sync()
        
        # Aggregate by sector
        sector_data = {}
        for q in quotes:
            symbol = q["symbol"]
            sector = sector_map.get(symbol, "Unknown")
            
            if sector not in sector_data:
                sector_data[sector] = {
                    "sector": sector,
                    "stocks": [],
                    "total_change": 0,
                    "count": 0
                }
            
            sector_data[sector]["stocks"].append({
                "symbol": symbol,
                "close_price": q["close_price"],
                "change_percent": q["change_percent"]
            })
            sector_data[sector]["total_change"] += q["change_percent"]
            sector_data[sector]["count"] += 1
        
        # Compute sector averages
        sector_list = []
        for sector, data in sector_data.items():
            if data["count"] > 0:
                avg_change = data["total_change"] / data["count"]
                sector_list.append({
                    "sector": sector,
                    "avg_change_percent": round(avg_change, 2),
                    "stock_count": data["count"],
                    "top_stocks": sorted(data["stocks"], key=lambda x: x["change_percent"], reverse=True)[:5],
                    "bottom_stocks": sorted(data["stocks"], key=lambda x: x["change_percent"])[:5]
                })
        
        # Sort sectors by performance
        sector_list.sort(key=lambda x: x["avg_change_percent"], reverse=True)
        
        # Cache heatmap data
        try:
            cache.set(f"snapshot:heatmap_sectors:{date_str}", {
                "sectors": sector_list,
                "total_sectors": len(sector_list),
                "trade_date": date_str
            }, ttl=86400)
            
            # Also cache individual sector data
            for sector_data in sector_list:
                sector_key = sector_data["sector"].replace(" ", "_").lower()
                cache.set(f"snapshot:heatmap_sector_{sector_key}:{date_str}", 
                         sector_data, ttl=86400)
            
            logger.info(f"Cached heatmap data for {len(sector_list)} sectors")
            
        except Exception as e:
            logger.warning(f"Failed to cache heatmap data: {e}")
        
        return {"sectors_count": len(sector_list)}
    
    def sync_official_prices_to_system(self, trade_date: date, quotes: List[Dict]) -> int:
        """
        Sync official exchange-validated prices to the primary system.
        1. Updates stock_candles table (PostgreSQL) for timeframe='1d'
        2. Updates Dragonfly cache (qai:snap:all) with official EOD state
        """
        session = self.Session()
        from services.dragonfly_client import get_cache, CacheKeys
        cache = get_cache()
        
        sync_count = 0
        all_snapshots = []
        
        # 1. Load Symbol -> ID map from instrument_master
        try:
            res = session.execute(text("SELECT symbol, instrument_id, instrument_key FROM instrument_master WHERE is_active = TRUE"))
            inst_info = {r[0]: (r[1], r[2]) for r in res}
        except Exception as e:
            logger.warning(f"Could not load instrument info map: {e}")
            inst_info = {}

        # 2. Fetch current qai:snap:all to preserve indicators but update price
        try:
            current_snapshots = cache.get(CacheKeys.all_snapshots()) or []
            # Create a map for quick lookup. Normalize symbol names to uppercase.
            snapshot_map = {s['symbol'].upper(): s for s in current_snapshots if 'symbol' in s}
        except Exception:
            snapshot_map = {}

        logger.info(f"Syncing {len(quotes)} official prices to primary tables...")
        
        updated_snapshot_map = {}
        
        for q in quotes:
            try:
                symbol = q["symbol"].upper()
                close_price = q["close_price"]
                prev_close = q.get("prev_close") or 0
                change_pct = q.get("change_percent") or 0
                volume = q.get("volume") or 0
                timestamp = datetime.combine(trade_date, datetime.min.time())
                
                # Get instrument info from map
                info = inst_info.get(symbol)
                if not info:
                    logger.warning(f"Symbol {symbol} not found in instrument_master. Skipping sync.")
                    continue
                
                inst_id, instrument_key = info
                
                if symbol == "MINDACORP":
                    logger.info(f"DEBUG: Syncing MINDACORP - Close: {close_price}, Prev Close: {prev_close}, ID: {inst_id}")
                
                # A. Update/Upsert stock_candle table (NEW SCHEMA)
                # timeframe = 1440 for daily
                session.execute(
                    text("""
                        INSERT INTO stock_candle (instrument_id, timeframe, candle_ts, open, high, low, close, volume)
                        VALUES (:iid, 1440, :ts, :close, :close, :close, :close, :vol)
                        ON CONFLICT (instrument_id, timeframe, candle_ts) 
                        DO UPDATE SET close = EXCLUDED.close, volume = EXCLUDED.volume
                    """),
                    {"iid": inst_id, "ts": timestamp, "close": close_price, "vol": volume}
                )

                # A.1 Update/Upsert legacy stock_candles table (for backward compatibility during transition)
                session.execute(
                    text("""
                        INSERT INTO stock_candles (symbol, instrument_key, timeframe, timestamp, open, high, low, close, volume)
                        VALUES (:symbol, :inst, '1d', :ts, :close, :close, :close, :close, :vol)
                        ON CONFLICT (instrument_key, timeframe, timestamp) 
                        DO UPDATE SET close = EXCLUDED.close, volume = EXCLUDED.volume
                    """),
                    {"symbol": symbol, "inst": instrument_key, "ts": timestamp, "close": close_price, "vol": volume}
                )
                
                # A.2 Update/Upsert legacy nifty100_daily table (for backward compatibility)
                session.execute(
                    text("""
                        INSERT INTO nifty100_daily (symbol, timestamp, open, high, low, close, volume, source)
                        VALUES (:symbol, :ts, :close, :close, :close, :close, :vol, 'official_etl')
                        ON CONFLICT (symbol, timestamp)
                        DO UPDATE SET close = EXCLUDED.close, volume = EXCLUDED.volume
                    """),
                    {"symbol": symbol, "ts": timestamp, "close": close_price, "vol": volume}
                )
                
                # B. Update/Reconstruct Snapshot for Cache
                # ... [Snapshot logic same as before] ...
                existing_snap = snapshot_map.get(symbol)
                
                # Look for name-based entry if not found by ticker
                if not existing_snap:
                    name_key = q.get("company_name", "").upper()
                    if name_key and name_key in snapshot_map:
                        existing_snap = snapshot_map[name_key]
                        logger.info(f"Merging name-based snapshot '{name_key}' into ticker '{symbol}'")
                
                if existing_snap:
                    snap = existing_snap.copy()
                    snap['symbol'] = symbol # Ensure it uses ticker
                    snap['ltp'] = close_price
                    snap['prev_close'] = prev_close
                    snap['change_pct'] = round(change_pct, 2)
                    snap['updated_at'] = datetime.now().isoformat()
                    # Preserve/Update indicators if they exist
                    if 'indicators' not in snap: snap['indicators'] = {}
                    snap['indicators'].update({'current_close': close_price, 'prev_close': prev_close})
                else:
                    snap = {
                        'symbol': symbol,
                        'interval': '1day',
                        'ltp': close_price,
                        'prev_close': prev_close,
                        'change_pct': round(change_pct, 2),
                        'indicators': {'current_close': close_price, 'prev_close': prev_close},
                        'signals': ['EOD_SYNC'],
                        'trend': 'BULLISH' if change_pct > 0 else 'BEARISH',
                        'updated_at': datetime.now().isoformat()
                    }
                
                # Save individual symbol cache
                cache.set(CacheKeys.snapshot(symbol), snap, ttl=86400)
                
                # Add to master map (this will naturally deduplicate and prioritize current tickers)
                updated_snapshot_map[symbol] = snap
                sync_count += 1
                
                # Commit after EACH symbol for maximum reliability (prevents one error rolling back other successful updates)
                session.commit()
                    
            except Exception as e:
                session.rollback()
                logger.error(f"Error syncing {q.get('symbol', 'unknown')}: {e}")
                continue
        
        # Final cleanup and cache sync
        try:
            session.commit()
            
            # Important: We ONLY want ticker-based symbols in qai:snap:all.
            # Convert map back to list.
            final_snapshots = list(updated_snapshot_map.values())
            
            if final_snapshots:
                cache.set(CacheKeys.all_snapshots(), final_snapshots, ttl=86400)
                logger.info(f"Cleaned and updated qai:snap:all with {len(final_snapshots)} ticker-based official prices")
                
                # Invalidate AI strategy caches to force recalculation with fresh prices
                strategy_ids = [
                    "trend-finder", "breakout-detector", "top5-picks", 
                    "momentum-scanner", "mean-reversion", "vwap-scanner", "sr-bounce"
                ]
                for sid in strategy_ids:
                    cache.delete(f"qai:ai:strategy:{sid}")
                logger.info("Invalidated AI strategy caches")
                
        except Exception as e:
            logger.error(f"Final sync cleanup failed: {e}")
        finally:
            session.close()
            
        return sync_count

    def _load_sector_map_sync(self) -> Dict[str, str]:
        """Load symbol -> sector mapping from database."""
        session = self.Session()
        try:
            result = session.execute(
                text("SELECT symbol, sector FROM instrument_master WHERE sector IS NOT NULL AND is_active = TRUE")
            )
            rows = result.fetchall()
            return {r[0]: r[1] for r in rows}
        except Exception as e:
            logger.warning(f"Could not load sector map: {e}")
            return {}
        finally:
            session.close()
    
    def check_snapshot(self, trade_date: date = None) -> Dict[str, Any]:
        """Check if snapshot exists for a given date."""
        if trade_date is None:
            trade_date = self.get_trading_date()
        
        session = self.Session()
        try:
            result = session.execute(
                text("""
                    SELECT category, COUNT(*), 
                           MIN(change_percent) as min_change, 
                           MAX(change_percent) as max_change
                    FROM daily_top_gainers_snapshot 
                    WHERE trade_date = :date
                    GROUP BY category
                """),
                {"date": trade_date}
            )
            
            rows = result.fetchall()
            if not rows:
                return {"exists": False, "trade_date": str(trade_date)}
            
            return {
                "exists": True,
                "trade_date": str(trade_date),
                "summary": [
                    {"category": r[0], "count": r[1], "min_change": float(r[2]), "max_change": float(r[3])}
                    for r in rows
                ]
            }
        finally:
            session.close()


async def main():
    parser = argparse.ArgumentParser(description="Daily Top Gainers/Losers ETL")
    parser.add_argument("--check", action="store_true", help="Check today's snapshot")
    args = parser.parse_args()
    
    etl = DailySnapshotETL()
    
    if args.check:
        result = etl.check_snapshot()
        print(f"\nSnapshot Status: {result}")
    else:
        result = await etl.run()
        print(f"\nETL Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
