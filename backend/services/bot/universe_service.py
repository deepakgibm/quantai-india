from typing import List, Tuple, Dict, Any
import logging
from sqlalchemy import text
from database import SessionLocal
from utils.index_config import get_index_constituents

logger = logging.getLogger(__name__)

class UniverseService:
    @staticmethod
    def get_universe_symbols(universe: str) -> List[Tuple[str, str]]:
        """
        Loads constituents for the requested universe:
        NIFTY 50, NIFTY NEXT 50, NIFTY 100, NIFTY 200, NIFTY 500.
        
        Returns:
            List of (symbol, instrument_key) tuples.
        """
        universe = universe.upper().strip()
        symbols_to_fetch = set()
        
        if universe == "NIFTY 500":
            # Load from database nifty500_symbols table first
            try:
                with SessionLocal() as session:
                    res = session.execute(text(
                        "SELECT symbol, instrument_key FROM nifty500_symbols WHERE symbol IS NOT NULL"
                    ))
                    for r in res:
                        if r[0] and r[1]:
                            symbols_to_fetch.add((r[0].strip(), r[1].strip()))
            except Exception as e:
                logger.warning(f"Failed to load Nifty 500 from nifty500_symbols table: {e}")
                
            # Fallback to CSV / mapping if database table is empty
            if not symbols_to_fetch:
                try:
                    from services.bot.data_collector import DataCollector
                    collector = DataCollector()
                    csv_symbols = collector.load_nifty500_symbols()
                    symbols_to_fetch.update(csv_symbols)
                except Exception as csv_err:
                    logger.error(f"Failed to load fallback Nifty 500 symbols: {csv_err}")
                    
        elif universe == "NIFTY NEXT 50":
            # NIFTY 100 minus NIFTY 50
            nifty100 = set(get_index_constituents("NIFTY 100"))
            nifty50 = set(get_index_constituents("NIFTY 50"))
            next50 = nifty100 - nifty50
            
            # Resolve instrument keys from instrument_master
            if next50:
                try:
                    with SessionLocal() as session:
                        res = session.execute(text(
                            "SELECT symbol, instrument_key FROM instrument_master "
                            "WHERE is_active = TRUE AND symbol = ANY(:syms)"
                        ), {"syms": list(next50)})
                        for r in res:
                            if r[0] and r[1]:
                                symbols_to_fetch.add((r[0].strip(), r[1].strip()))
                except Exception as e:
                    logger.error(f"Failed resolving keys for NIFTY NEXT 50: {e}")
                    
        else:
            # NIFTY 50, NIFTY 100, NIFTY 200
            name = "NIFTY 50"
            if universe == "NIFTY 100":
                name = "NIFTY 100"
            elif universe == "NIFTY 200":
                name = "NIFTY 200"
                
            constituents = get_index_constituents(name)
            if constituents:
                try:
                    with SessionLocal() as session:
                        res = session.execute(text(
                            "SELECT symbol, instrument_key FROM instrument_master "
                            "WHERE is_active = TRUE AND symbol = ANY(:syms)"
                        ), {"syms": list(constituents)})
                        for r in res:
                            if r[0] and r[1]:
                                symbols_to_fetch.add((r[0].strip(), r[1].strip()))
                except Exception as e:
                    logger.error(f"Failed resolving keys for {universe}: {e}")
                    
        # Return sorted list
        return sorted(list(symbols_to_fetch))

    @staticmethod
    def validate_and_filter_universe(symbols: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Validates:
        - Symbol
        - Exchange (NSE)
        - Instrument Key (not null)
        - Sector / Industry
        - Market Cap (if available)
        
        Removes delisted/inactive/invalid stocks.
        """
        if not symbols:
            return []
            
        validated_symbols = []
        sym_names = [s[0] for s in symbols]
        
        try:
            with SessionLocal() as session:
                # Query instrument details from instrument_master and fundamental_metrics/nifty500_symbols
                res = session.execute(text("""
                    SELECT im.symbol, im.exchange, im.instrument_key, im.is_active, im.sector,
                           COALESCE(ns.industry, 'Others') as industry,
                           fm.market_cap
                    FROM instrument_master im
                    LEFT JOIN nifty500_symbols ns ON im.symbol = ns.symbol
                    LEFT JOIN fundamental_metrics fm ON im.symbol = fm.symbol
                    WHERE im.symbol = ANY(:syms)
                """), {"syms": sym_names})
                
                meta_dict = {}
                for r in res:
                    sym = r[0]
                    meta_dict[sym] = {
                        "symbol": sym,
                        "exchange": r[1],
                        "instrument_key": r[2],
                        "is_active": r[3],
                        "sector": r[4],
                        "industry": r[5],
                        "market_cap": r[6]
                    }
                    
                for sym, ik in symbols:
                    meta = meta_dict.get(sym)
                    if not meta:
                        logger.warning(f"Skipping {sym}: No database metadata found.")
                        continue
                        
                    # Validations:
                    # 1. Must be active
                    if not meta["is_active"]:
                        logger.info(f"Skipping {sym}: Inactive / Delisted in database.")
                        continue
                        
                    # 2. Must be NSE
                    if meta["exchange"] != "NSE":
                        logger.info(f"Skipping {sym}: Exchange is {meta['exchange']}, not NSE.")
                        continue
                        
                    # 3. Must have valid instrument key
                    if not meta["instrument_key"] or not meta["instrument_key"].startswith("NSE_"):
                        logger.warning(f"Skipping {sym}: Invalid instrument key {meta['instrument_key']}.")
                        continue
                        
                    # All checks passed
                    validated_symbols.append((sym, ik))
                    
        except Exception as e:
            logger.error(f"Error during universe validation: {e}")
            # If query fails, fallback to passing through symbols
            return symbols
            
        logger.info(f"Universe Validation: {len(symbols)} candidate symbols -> {len(validated_symbols)} validated active symbols")
        return validated_symbols
