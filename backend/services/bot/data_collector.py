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
import numpy as np
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
        Load NIFTY 500 symbols from the CSV file.
        
        Returns:
            List of (symbol_name, instrument_key) tuples
        """
        if self._nifty500_cache is not None:
            return self._nifty500_cache

        # Search multiple candidate locations for nifty_500.csv
        candidates = [
            Path(__file__).parent.parent.parent / "nifty_500.csv",      # backend/nifty_500.csv (Docker /app/)
            Path(__file__).parent.parent.parent.parent / "nifty_500.csv",  # project_root/nifty_500.csv
            Path.cwd() / "nifty_500.csv",                                 # working directory
        ]
        csv_path = None
        for p in candidates:
            if p.exists():
                csv_path = p
                break

        symbols = []

        if csv_path is None:
            logger.error(f"nifty_500.csv not found in any of: {[str(p) for p in candidates]}")
            return []

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = row.get("symbol", "").strip()
                    instrument_key = row.get("instrument_key", "").strip()
                    if symbol and instrument_key:
                        symbols.append((symbol, instrument_key))
            
            logger.info(f"Loaded {len(symbols)} NIFTY 500 symbols from CSV")
            self._nifty500_cache = symbols
            return symbols

        except FileNotFoundError:
            logger.error(f"nifty_500.csv not found at {csv_path}")
            return []
        except Exception as e:
            logger.error(f"Error loading NIFTY 500 symbols: {e}")
            return []

    async def fetch_nifty50_history(self, days: int = 90) -> pd.DataFrame:
        """
        Fetch NIFTY 50 index historical daily candles from Upstox.
        
        Args:
            days: Number of calendar days to fetch
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        from services.upstox_client import get_upstox_client

        client = get_upstox_client()
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        try:
            df = await client.get_historical_data(
                symbol="NIFTY 50",
                instrument_key=self.NIFTY50_INSTRUMENT_KEY,
                from_date=from_date,
                to_date=to_date,
                interval="day"
            )

            if df.empty:
                logger.warning("No NIFTY 50 index data returned from Upstox")
                return pd.DataFrame()

            df = df.sort_values("timestamp").reset_index(drop=True)
            logger.info(f"Fetched {len(df)} days of NIFTY 50 data")
            return df

        except Exception as e:
            logger.error(f"Error fetching NIFTY 50 history: {e}")
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
                    SELECT symbol, timestamp, open, high, low, close, volume
                    FROM stock_candle
                    WHERE timeframe = '1d'
                      AND timestamp >= :cutoff
                    ORDER BY symbol, timestamp
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
                    "open": float(row[2]) if row[2] else 0,
                    "high": float(row[3]) if row[3] else 0,
                    "low": float(row[4]) if row[4] else 0,
                    "close": float(row[5]) if row[5] else 0,
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
        Fetch live market quotes in batches.
        
        Args:
            instrument_keys: List of Upstox instrument keys
            batch_size: Number of keys per API call (Upstox limit)
            
        Returns:
            Dict mapping instrument_key → quote data
        """
        from services.upstox_client import get_upstox_client

        client = get_upstox_client()
        all_quotes: Dict[str, Dict] = {}

        # Split into batches
        batches = [
            instrument_keys[i : i + batch_size]
            for i in range(0, len(instrument_keys), batch_size)
        ]

        for i, batch in enumerate(batches):
            try:
                quotes = await client.get_live_quotes(batch)
                all_quotes.update(quotes)
                logger.debug(f"Fetched batch {i+1}/{len(batches)}: {len(quotes)} quotes")
                
                # Small delay between batches to respect rate limits
                if i < len(batches) - 1:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching quote batch {i+1}: {e}")
                continue

        logger.info(f"Fetched {len(all_quotes)} live quotes total")
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
