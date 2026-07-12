import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from services.price_manager.models import StockPrice, PriceSource
from services.price_manager.price_repository import get_price_repository
from services.price_manager.price_calculation_engine import get_price_calculation_engine
from services.price_manager.price_formatter import get_price_formatter
from services.price_manager.market_status_service import get_market_status_service

logger = logging.getLogger(__name__)

class PriceService:
    """
    Main Service Gateway for resolving and retrieving stock prices.
    Implements single source of truth routing, standard validation,
    formatting, event dispatching, and concurrent request deduplication.
    """

    def __init__(self):
        self._repo = get_price_repository()
        self._calc = get_price_calculation_engine()
        self._formatter = get_price_formatter()
        self._status_service = get_market_status_service()
        self._pending_requests: Dict[str, asyncio.Future] = {}

    async def get_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get the unified, formatted StockPrice details for a symbol.
        Leverages request deduplication to prevent redundant queries.
        """
        symbol_upper = symbol.upper().strip()
        if not symbol_upper:
            return self._empty_stock_price_dict("NONE")

        # Request Deduplication logic
        if symbol_upper in self._pending_requests:
            logger.debug(f"PriceService: Deduplicating concurrent request for {symbol_upper}")
            return await self._pending_requests[symbol_upper]

        future = asyncio.get_running_loop().create_future()
        self._pending_requests[symbol_upper] = future

        try:
            price_dict = await self._resolve_price_dict(symbol_upper)
            dto = self._build_dto(symbol_upper, price_dict)
            future.set_result(dto.to_dict())
        except Exception as e:
            logger.error(f"PriceService: Resolution error for {symbol_upper}: {e}")
            future.set_result(self._empty_stock_price_dict(symbol_upper))
        finally:
            self._pending_requests.pop(symbol_upper, None)

        return await future

    async def get_prices_bulk(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch and format prices for a bulk list of symbols."""
        results = {}
        if not symbols:
            return results
            
        unique_symbols = list(set([s.upper().strip() for s in symbols if s]))
        
        # 1. Resolve what we can from WS Cache
        ws_tasks = [self._repo.get_from_ws(s) for s in unique_symbols]
        ws_results = await asyncio.gather(*ws_tasks)
        
        pending_symbols = []
        for i, res in enumerate(ws_results):
            s = unique_symbols[i]
            if res:
                results[s] = self._build_dto(s, res).to_dict()
            else:
                pending_symbols.append(s)
                
        if not pending_symbols:
            return results

        # 2. Resolve remaining from REST quote bulk
        try:
            rest_results = await self._repo.get_from_rest_bulk(pending_symbols)
            for s, res in rest_results.items():
                results[s] = self._build_dto(s, res).to_dict()
                
            pending_symbols = [s for s in pending_symbols if s not in results]
        except Exception as e:
            logger.error(f"PriceService: Bulk REST resolution failed: {e}")

        if not pending_symbols:
            return results

        # 3. Resolve final leftovers from EOD DB
        try:
            db_results = await self._repo.get_from_db_bulk(pending_symbols)
            for s, res in db_results.items():
                results[s] = self._build_dto(s, res).to_dict()
                
            pending_symbols = [s for s in pending_symbols if s not in results]
        except Exception as e:
            logger.error(f"PriceService: Bulk DB fallback failed: {e}")

        # 4. Fill defaults for completely failed symbols
        for s in pending_symbols:
            results[s] = self._empty_stock_price_dict(s)

        return results

    async def _resolve_price_dict(self, symbol: str) -> Dict[str, Any]:
        """Resolves the raw price dictionary sequentially."""
        # 1. WS
        res = await self._repo.get_from_ws(symbol)
        if res:
            return res
            
        # 2. REST
        res = await self._repo.get_from_rest(symbol)
        if res:
            return res
            
        # 3. DB
        res = await self._repo.get_from_db(symbol)
        if res:
            return res
            
        raise ValueError(f"No price data available for {symbol}")

    def _build_dto(self, symbol: str, data: Dict[str, Any]) -> StockPrice:
        """Constructs the unified type-safe StockPrice DTO."""
        from services.instrument_resolver import resolve_instrument_info
        info = resolve_instrument_info(symbol)
        inst_key = info.instrument_key if info else None
        
        ltp = self._formatter.round_field(data.get("ltp") or data.get("price"))
        prev_close = self._formatter.round_field(data.get("prev_close"))
        
        change = self._calc.calculate_change(ltp, prev_close)
        change_pct = self._calc.calculate_change_percent(ltp, prev_close)
        
        market_status = self._status_service.get_status().value
        source = data.get("price_source", PriceSource.NONE.value)
        ts = self._formatter.format_timestamp(data.get("timestamp"))

        return StockPrice(
            symbol=symbol.upper(),
            instrument_key=inst_key,
            ltp=ltp,
            open=self._formatter.round_field(data.get("open") or ltp),
            high=self._formatter.round_field(data.get("high") or ltp),
            low=self._formatter.round_field(data.get("low") or ltp),
            close=self._formatter.round_field(data.get("close") or ltp),
            previous_close=prev_close,
            change=self._formatter.round_field(change),
            change_percent=self._formatter.round_field(change_pct),
            volume=int(data.get("volume") or 0),
            timestamp=ts,
            market_status=market_status,
            source=source,
            last_updated=datetime.now(timezone.utc).isoformat()
        )

    def _empty_stock_price_dict(self, symbol: str) -> dict:
        ts = datetime.now(timezone.utc).isoformat()
        return {
            "symbol": symbol.upper(),
            "instrument_key": None,
            "ltp": 0.0,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "close": 0.0,
            "previous_close": 0.0,
            "change": 0.0,
            "change_percent": 0.0,
            "volume": 0,
            "timestamp": ts,
            "market_status": self._status_service.get_status().value,
            "source": PriceSource.NONE.value,
            "last_updated": ts
        }

_price_service = None

def get_price_service() -> PriceService:
    global _price_service
    if _price_service is None:
        _price_service = PriceService()
    return _price_service
