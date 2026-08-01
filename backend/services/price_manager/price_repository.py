import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import pytz

from services.price_manager.models import PriceSource
from services.price_manager.price_cache import get_price_cache
from services.price_manager.price_validator import get_price_validator

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

class PriceRepository:
    """
    Data Repository for retrieving stock prices.
    Manages querying Cache, WebSocket sources, Upstox REST APIs, and EOD Database.
    """

    def __init__(self):
        self._cache = get_price_cache()
        self._validator = get_price_validator()

    async def get_from_ws(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieve price from the live WebSocket cache namespace."""
        data = self._cache.get(symbol)
        if data:
            # Check validation
            if self._validator.validate_price_dict(symbol, data):
                data["price_source"] = PriceSource.UPSTOX_WS.value
                return data
        return None

    async def get_from_rest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch a single live quote from Upstox REST API."""
        try:
            from services.upstox_client import get_upstox_client
            from services.instrument_resolver import resolve_instrument_info
            
            info = resolve_instrument_info(symbol)
            if not info or not info.instrument_key:
                return None
                
            client = get_upstox_client()
            quote = await client.get_live_quote(info.instrument_key, symbol)
            
            if quote and quote.get("last_price") and quote["last_price"] > 0:
                ltp = float(quote["last_price"])
                prev_close = float(quote.get("previous_close") or ltp)
                
                # Construct standard dict structure
                price_dict = {
                    "symbol": symbol.upper(),
                    "ltp": ltp,
                    "open": float(quote.get("open") or ltp),
                    "high": float(quote.get("high") or ltp),
                    "low": float(quote.get("low") or ltp),
                    "close": float(quote.get("close") or ltp),
                    "prev_close": prev_close,
                    "volume": int(quote.get("volume") or 0),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "price_source": PriceSource.UPSTOX_REST.value
                }
                
                if self._validator.validate_price_dict(symbol, price_dict):
                    # Write back to cache
                    self._cache.set(symbol, price_dict)
                    return price_dict
        except Exception as e:
            logger.error(f"Repository: REST API failed for {symbol}: {e}")
            
        return None

    async def get_from_rest_bulk(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch quotes in batch from Upstox REST API."""
        results = {}
        if not symbols:
            return results
            
        try:
            from services.upstox_client import get_upstox_client
            from services.instrument_resolver import resolve_instrument_info
            
            client = get_upstox_client()
            
            # Resolve instrument keys - separate API keys from response-matching lookup
            keys_to_sym = {}        # Broad lookup map for matching API response keys
            real_inst_keys = set()  # Only valid instrument keys to send to Upstox
            for s in symbols:
                info = resolve_instrument_info(s)
                if info and info.instrument_key:
                    real_key = info.instrument_key  # e.g. NSE_EQ|INE371A01025
                    real_inst_keys.add(real_key)
                    
                    # Map all possible response key formats back to the symbol
                    keys_to_sym[real_key] = s.upper()
                    keys_to_sym[real_key.upper()] = s.upper()
                    keys_to_sym[real_key.replace("|", ":")] = s.upper()
                    # Upstox sometimes returns NSE_EQ:SYMBOL format
                    symbol_key_pipe = f"{info.exchange.upper()}_{info.series.upper()}|{info.symbol.upper()}"
                    symbol_key_colon = f"{info.exchange.upper()}_{info.series.upper()}:{info.symbol.upper()}"
                    keys_to_sym[symbol_key_pipe] = s.upper()
                    keys_to_sym[symbol_key_colon] = s.upper()
                    keys_to_sym[f"{info.exchange.upper()}:{info.symbol.upper()}"] = s.upper()
                    
            if real_inst_keys:
                rest_res = await client.get_live_quotes(list(real_inst_keys))
                
                for inst_key, quote in rest_res.items():
                    s = keys_to_sym.get(inst_key)
                    if s and quote and quote.get("last_price"):
                        ltp = float(quote["last_price"])
                        prev_close = float(quote.get("previous_close") or ltp)
                        
                        price_dict = {
                            "symbol": s,
                            "ltp": ltp,
                            "open": float(quote.get("open") or ltp),
                            "high": float(quote.get("high") or ltp),
                            "low": float(quote.get("low") or ltp),
                            "close": float(quote.get("close") or ltp),
                            "prev_close": prev_close,
                            "volume": int(quote.get("volume") or 0),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "price_source": PriceSource.UPSTOX_REST.value
                        }
                        
                        if self._validator.validate_price_dict(s, price_dict):
                            results[s] = price_dict
                            self._cache.set(s, price_dict)
        except Exception as e:
            logger.error(f"Repository: Bulk REST API failed: {e}")
            
        return results

    async def get_from_db(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieve price from the local EOD stock_candle database. Disabled per Phase 7 specifications."""
        logger.debug(f"PriceRepository: Database fallback is disabled for live prices. Symbol: {symbol}")
        return None

    async def get_from_db_bulk(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Retrieve price in batch from the local EOD stock_candle database. Disabled per Phase 7 specifications."""
        logger.debug(f"PriceRepository: Database fallback is disabled for live prices. Symbols: {symbols}")
        return {}

_price_repository = None

def get_price_repository() -> PriceRepository:
    global _price_repository
    if _price_repository is None:
        _price_repository = PriceRepository()
    return _price_repository
