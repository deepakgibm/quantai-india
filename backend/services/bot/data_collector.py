"""
Bot Data Collector

Handles data ingestion for the signal generation pipeline:
- Loads NIFTY 500 symbol registry from CSV
- Fetches NIFTY 50 index historical data
- Fetches stock OHLCV data (DB-first, Upstox fallback)
- Batch live quote fetching
"""

import csv
import logging
import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Data ingestion layer for the Bot pipeline.
    
    Strategy:
    1. Historical data: Read from PostgreSQL stock_candle table (populated by ETL).
    2. Fallback: Fetch from Upstox API if DB data is stale.
    3. Live quotes: Batch fetch from Upstox in groups of 50.
    4. NIFTY 50 index: Always fetch from Upstox (index data not in stock_candle).
    """

    # NIFTY 50 instrument key on Upstox
    NIFTY50_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
    
    def __init__(self):
        self._nifty500_cache: Optional[List[Tuple[str, str]]] = None

    def load_nifty500_symbols(self) -> List[Tuple[str, str]]:
        """
        Load NIFTY 500 symbols using a multi-tier fallback approach:
        1. Cache (in-memory)
        2. Database (instrument_master table)
        3. Static python module (data.nifty500_instruments)
        4. CSV file (nifty_500.csv) with name-to-symbol resolution
        5. Hardcoded fallback list (top NIFTY symbols)
        
        Returns:
            List of (symbol_name, instrument_key) tuples
        """
        if self._nifty500_cache is not None:
            return self._nifty500_cache

        # Tier 2: Database Source
        try:
            from database import SessionLocal
            from sqlalchemy import text
            db_symbols = []
            with SessionLocal() as session:
                res = session.execute(text(
                    "SELECT symbol, instrument_key FROM instrument_master "
                    "WHERE is_active = TRUE AND exchange = 'NSE' AND series = 'EQ' "
                    "AND instrument_key IS NOT NULL"
                ))
                for row in res:
                    sym = row[0]
                    ik = row[1]
                    if sym and ik:
                        db_symbols.append((sym.strip(), ik.strip()))
            
            if db_symbols:
                logger.info(f"Loaded {len(db_symbols)} active symbols from instrument_master database")
                db_symbols.sort()
                self._nifty500_cache = db_symbols
                return db_symbols
        except Exception as db_err:
            logger.warning(f"Database symbol loading failed: {db_err}")

        # Tier 3: Static Python Mapping
        try:
            from data.nifty500_instruments import NIFTY_500_MAPPING
            if NIFTY_500_MAPPING:
                static_symbols = [(sym.strip(), ik.strip()) for sym, ik in NIFTY_500_MAPPING.items() if sym and ik]
                if static_symbols:
                    logger.info(f"Loaded {len(static_symbols)} symbols from static NIFTY_500_MAPPING")
                    static_symbols.sort()
                    self._nifty500_cache = static_symbols
                    return static_symbols
        except Exception as static_err:
            logger.warning(f"Static mapping symbol loading failed: {static_err}")

        # Tier 4: CSV File
        candidates = [
            Path(__file__).parent.parent.parent / "data" / "nifty_500.csv", # backend/data/nifty_500.csv
            Path(__file__).parent.parent.parent / "nifty_500.csv",         # backend/nifty_500.csv (Docker /app/)
            Path(__file__).parent.parent.parent.parent / "nifty_500.csv",  # project_root/nifty_500.csv
            Path.cwd() / "nifty_500.csv",                                  # working directory
            Path.cwd() / "data" / "nifty_500.csv",                            # working directory / data
            Path("/app/data/nifty_500.csv"),                                  # Docker volume path
            Path("/app/nifty_500.csv"),                                       # Docker app root
        ]
        csv_path = None
        for p in candidates:
            if p.exists():
                csv_path = p
                break

        if csv_path is not None:
            try:
                # Load ik to symbol mappings from static mapping if possible to translate company name
                ik_to_symbol = {}
                try:
                    from data.nifty500_instruments import NIFTY_500_MAPPING
                    ik_to_symbol = {ik.strip(): sym.strip() for sym, ik in NIFTY_500_MAPPING.items() if sym and ik}
                except Exception:
                    pass

                csv_symbols = []
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        symbol = row.get("symbol", "").strip()
                        instrument_key = row.get("instrument_key", "").strip()
                        if symbol and instrument_key:
                            # Map to proper trading symbol if possible, otherwise use name from CSV
                            resolved_symbol = ik_to_symbol.get(instrument_key, symbol)
                            csv_symbols.append((resolved_symbol, instrument_key))
                
                if csv_symbols:
                    logger.info(f"Loaded {len(csv_symbols)} symbols from CSV file at {csv_path}")
                    csv_symbols.sort()
                    self._nifty500_cache = csv_symbols
                    return csv_symbols
            except Exception as csv_err:
                logger.error(f"Error loading symbols from CSV {csv_path}: {csv_err}")

        # Tier 5: Hardcoded Fallback List
        logger.warning("All symbol loading sources failed. Using hardcoded NIFTY fallback list.")
        hardcoded_symbols = [
            ("RELIANCE", "NSE_EQ|INE002A01018"),
            ("TCS", "NSE_EQ|INE467B01029"),
            ("HDFCBANK", "NSE_EQ|INE040A01034"),
            ("INFY", "NSE_EQ|INE009A01021"),
            ("ICICIBANK", "NSE_EQ|INE090A01021"),
            ("HINDUNILVR", "NSE_EQ|INE030A01027"),
            ("ITC", "NSE_EQ|INE154A01025"),
            ("SBIN", "NSE_EQ|INE062A01020"),
            ("BHARTIARTL", "NSE_EQ|INE397D01024"),
            ("KOTAKBANK", "NSE_EQ|INE237A01028"),
            ("LT", "NSE_EQ|INE018A01030"),
            ("AXISBANK", "NSE_EQ|INE238A01034"),
            ("ASIANPAINT", "NSE_EQ|INE021A01026"),
            ("MARUTI", "NSE_EQ|INE585B01010"),
            ("BAJFINANCE", "NSE_EQ|INE296A01024"),
            ("TITAN", "NSE_EQ|INE280A01028"),
            ("SUNPHARMA", "NSE_EQ|INE044A01036"),
            ("ULTRACEMCO", "NSE_EQ|INE481G01011"),
            ("HCLTECH", "NSE_EQ|INE860A01027"),
            ("WIPRO", "NSE_EQ|INE075A01022"),
        ]
        self._nifty500_cache = hardcoded_symbols
        return hardcoded_symbols

    async def fetch_nifty50_history(self, days: int = 90) -> pd.DataFrame:
        """
        Fetch NIFTY 50 index historical daily candles from PostgreSQL database.
        
        Args:
            days: Number of calendar days to fetch
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        from sqlalchemy import text
        from database import AsyncSessionLocal

        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        try:
            async with AsyncSessionLocal() as session:
                query = text("""
                    SELECT sc.candle_ts, sc.open, sc.high, sc.low, sc.close, sc.volume
                    FROM stock_candle sc
                    JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                    WHERE im.symbol = 'NIFTY 50'
                      AND sc.timeframe = 1440
                      AND sc.candle_ts >= :cutoff
                    ORDER BY sc.candle_ts ASC
                """)
                result = await session.execute(query, {"cutoff": cutoff_date})
                rows = result.fetchall()

            if not rows:
                logger.warning("No NIFTY 50 index data returned from DB")
                return pd.DataFrame()

            records = []
            for row in rows:
                records.append({
                    "timestamp": row[0],
                    "open": float(row[1]) if row[1] else 0.0,
                    "high": float(row[2]) if row[2] else 0.0,
                    "low": float(row[3]) if row[3] else 0.0,
                    "close": float(row[4]) if row[4] else 0.0,
                    "volume": int(row[5]) if row[5] else 0,
                })

            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)
            logger.info(f"Loaded {len(df)} days of NIFTY 50 data from DB")
            return df

        except Exception as e:
            logger.error(f"Error fetching NIFTY 50 history from DB: {e}")
            return pd.DataFrame()

    async def fetch_stock_data_from_db(self, days: int = 90) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical daily candle data from PostgreSQL stock_candle table.
        
        Returns:
            Dict mapping symbol → DataFrame of OHLCV data
        """
        from sqlalchemy import text
        from database import AsyncSessionLocal

        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        stock_data: Dict[str, pd.DataFrame] = {}

        try:
            async with AsyncSessionLocal() as session:
                query = text("""
                    SELECT im.symbol, sc.candle_ts, sc.open, sc.high, sc.low, sc.close, sc.volume
                    FROM stock_candle sc
                    JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                    WHERE sc.timeframe = 1440
                      AND sc.candle_ts >= :cutoff
                    ORDER BY im.symbol, sc.candle_ts
                """)
                result = await session.execute(query, {"cutoff": cutoff_date})
                rows = result.fetchall()

            if not rows:
                logger.warning("No stock candle data found in DB")
                return {}

            # Build DataFrames per symbol
            data_by_symbol: Dict[str, list] = {}
            for row in rows:
                sym = row[0]
                if sym not in data_by_symbol:
                    data_by_symbol[sym] = []
                data_by_symbol[sym].append({
                    "timestamp": row[1],
                    "open": float(row[2]) if row[2] else 0.0,
                    "high": float(row[3]) if row[3] else 0.0,
                    "low": float(row[4]) if row[4] else 0.0,
                    "close": float(row[5]) if row[5] else 0.0,
                    "volume": int(row[6]) if row[6] else 0,
                })

            for sym, records in data_by_symbol.items():
                df = pd.DataFrame(records)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp").reset_index(drop=True)
                stock_data[sym] = df

            logger.info(f"Loaded DB data for {len(stock_data)} stocks")
            return stock_data

        except Exception as e:
            logger.error(f"Error fetching stock data from DB: {e}")
            return {}

    async def fetch_live_quotes(
        self, instrument_keys: List[str], batch_size: int = 50
    ) -> Dict[str, Dict]:
        """
        Fetch live market quotes from Dragonfly cache with DB fallback.
        
        Args:
            instrument_keys: List of Upstox instrument keys
            batch_size: Not used (maintained for backward compatibility)
            
        Returns:
            Dict mapping instrument_key → quote data
        """
        from database import SessionLocal
        from sqlalchemy import text
        from services.dragonfly_client import get_cache
        import json

        if not instrument_keys:
            return {}

        all_quotes: Dict[str, Dict] = {}

        # 1. Resolve instrument keys to symbols using the DB
        ik_to_symbol = {}
        try:
            with SessionLocal() as session:
                res = session.execute(text(
                    "SELECT instrument_key, symbol FROM instrument_master "
                    "WHERE instrument_key = ANY(:keys)"
                ), {"keys": instrument_keys})
                for row in res:
                    if row[0] and row[1]:
                        ik_to_symbol[row[0].strip()] = row[1].strip()
        except Exception as e:
            logger.warning(f"Failed to resolve instrument keys to symbols in fetch_live_quotes: {e}")

        # 2. Query Dragonfly cache first
        cache = get_cache()
        if cache.is_available() and ik_to_symbol:
            try:
                symbols = list(ik_to_symbol.values())
                keys_new = [f"price:{s}" for s in symbols]
                keys_legacy = [f"qai:tick:{s}" for s in symbols]
                
                cached_new = await cache.mget_async(keys_new)
                cached_legacy = await cache.mget_async(keys_legacy)
                
                symbol_to_data = {}
                for idx, symbol in enumerate(symbols):
                    val = cached_new[idx] or cached_legacy[idx]
                    if val:
                        if isinstance(val, str):
                            try:
                                val = json.loads(val)
                            except:
                                pass
                        symbol_to_data[symbol] = val

                for ik, symbol in ik_to_symbol.items():
                    val = symbol_to_data.get(symbol)
                    if val:
                        ltp = val.get("ltp") or val.get("last_price") or val.get("price")
                        prev_close = val.get("prev_close") or val.get("previous_close") or ltp
                        
                        all_quotes[ik] = {
                            "last_price": float(ltp) if ltp else 0.0,
                            "previous_close": float(prev_close) if prev_close else 0.0,
                            "volume": int(val.get("volume") or 0),
                            "timestamp": val.get("timestamp")
                        }
            except Exception as e:
                logger.error(f"Failed to fetch live quotes from Dragonfly: {e}")

        # 3. For any missing instrument keys, fall back to DB stock_candle daily close
        missing_iks = [ik for ik in instrument_keys if ik not in all_quotes]
        if missing_iks and ik_to_symbol:
            try:
                with SessionLocal() as session:
                    for ik in missing_iks:
                        symbol = ik_to_symbol.get(ik)
                        if not symbol:
                            continue
                        # Query the 2 latest daily candles
                        stmt = text("""
                            SELECT sc.close, sc.candle_ts
                            FROM stock_candle sc
                            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                            WHERE im.symbol = :symbol AND sc.timeframe = 1440
                            ORDER BY sc.candle_ts DESC
                            LIMIT 2
                        """)
                        res = session.execute(stmt, {"symbol": symbol}).fetchall()
                        if res:
                            ltp = float(res[0][0])
                            prev_close = float(res[1][0]) if len(res) > 1 else ltp
                            all_quotes[ik] = {
                                "last_price": ltp,
                                "previous_close": prev_close,
                                "volume": 0,
                                "timestamp": res[0][1]
                            }
            except Exception as db_err:
                logger.warning(f"Database fallback failed in fetch_live_quotes: {db_err}")

        logger.info(f"Resolved {len(all_quotes)} live quotes via Cache/DB")
        return all_quotes


    async def fetch_stock_data_from_api(
        self,
        symbols: List[Tuple[str, str]],
        days: int = 90,
        progress_callback=None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fallback: fetch historical data from Upstox API for stocks missing in DB.
        Rate-limited; use sparingly.
        
        Args:
            symbols: List of (symbol, instrument_key) tuples to fetch
            days: Calendar days of history
            progress_callback: Optional async callable(current, total)
            
        Returns:
            Dict mapping symbol → DataFrame
        """
        from services.upstox_client import get_upstox_client

        client = get_upstox_client()
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        results: Dict[str, pd.DataFrame] = {}

        for idx, (symbol, ikey) in enumerate(symbols):
            try:
                df = await client.get_historical_data(
                    symbol=symbol,
                    instrument_key=ikey,
                    from_date=from_date,
                    to_date=to_date,
                    interval="day",
                )
                if not df.empty:
                    df = df.sort_values("timestamp").reset_index(drop=True)
                    results[symbol] = df

            except Exception as e:
                logger.warning(f"Failed to fetch API data for {symbol}: {e}")

            if progress_callback and idx % 10 == 0:
                await progress_callback(idx + 1, len(symbols))

            # Rate limit compliance
            await asyncio.sleep(0.1)

        logger.info(f"Fetched API data for {len(results)}/{len(symbols)} stocks")
        return results
