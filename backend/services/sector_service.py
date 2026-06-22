
"""
Sector Performance Service
Calculates real-time sector performance (heatmap) based on live stock prices.

Architecture:
- Fetches all Nifty 500 symbols & prices from UpstoxPriceResolver
- Groups stocks by Sector (from SymbolManager)
- Calculates sector-level Change % (simple average or market-cap weighted if available)
- Caches results to Dragonfly for API consumption
"""

import asyncio
import logging
from typing import List, Dict, Any

from services.dragonfly_client import get_cache
from services.upstox_price_resolver import get_upstox_price_resolver
from utils.symbol_utils import _symbol_manager

logger = logging.getLogger(__name__)

class SectorPerformanceService:
    """
    Periodically calculates sector performance and updates cache.
    Cache Keys:
      - qai:market:sector_heatmap : List of all sectors with summary
      - qai:market:sector_stocks:{sector} : List of stocks in a specific sector
    """
    
    def __init__(self):
        self._is_running = False
        self._task = None
        self._cache = get_cache()
        self.refresh_interval = 30 # Seconds
        
    async def start(self):
        if self._is_running:
            return
        logger.info("Starting SectorPerformanceService...")
        self._is_running = True
        self._task = asyncio.create_task(self._refresh_loop())
        
    async def stop(self):
        logger.info("Stopping SectorPerformanceService...")
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
    async def _refresh_loop(self):
        while self._is_running:
            try:
                await self._calculate_and_cache()
            except Exception as e:
                logger.error(f"Sector calculation failed: {e}")
            
            await asyncio.sleep(self.refresh_interval)
            
    async def _calculate_and_cache(self):
        # 1. Get Symbols & Sectors
        sector_map = _symbol_manager.get_sector_map() # symbol -> sector
        all_symbols = list(sector_map.keys())
        
        if not all_symbols:
            logger.warning("No symbols found for sector calculation")
            return

        # 2. Get Live Prices
        resolver = get_upstox_price_resolver()
        # Fetch in batches if needed, but resolver handles bulk
        prices = await resolver.get_prices_bulk(all_symbols)
        
        if not prices:
            logger.warning("No prices available for sector calculation")
            return

        # 3. Group by Sector
        sectors_data: Dict[str, List[Dict]] = {}
        
        for symbol, data in prices.items():
            sector = sector_map.get(symbol, "Others")
            if sector is None: sector = "Others"
            
            if sector not in sectors_data:
                sectors_data[sector] = []
                
            # Enhance data with company name if needed
            company_name = _symbol_manager.get_stock_name(symbol)
            
            # Use data from resolver
            ltp = data.get("price", 0)
            change_pct = data.get("change_pct", 0)
            
            if ltp > 0:
                sectors_data[sector].append({
                    "symbol": symbol,
                    "company_name": company_name,
                    "ltp": ltp,
                    "change_pct": change_pct,
                    "volume": data.get("volume", 0),
                    # Add other fields if API expects them
                })

        # 4. Calculate Sector Metrics
        heatmap_summary = []
        
        for sector, stocks in sectors_data.items():
            if not stocks:
                continue
                
            count = len(stocks)
            # Simple Average Change % (Market Cap weighting would be better if we had MC data)
            avg_change = sum(s["change_pct"] for s in stocks) / count
            
            heatmap_summary.append({
                "sector": sector,
                "change_pct": round(avg_change, 2),
                "stock_count": count,
                "top_gainer": max(stocks, key=lambda x: x["change_pct"])["symbol"],
                "top_loser": min(stocks, key=lambda x: x["change_pct"])["symbol"]
            })
            
            # Cache individual sector stocks
            # Sort by change_pct desc
            sorted_stocks = sorted(stocks, key=lambda x: x["change_pct"], reverse=True)
            
            sector_key_safe = sector # encodeURIComponent done in frontend, backend uses raw string usually
            # Redis keys can contain spaces
            await self._cache_set(f"qai:market:sector_stocks:{sector}", {"status": "success", "stocks": sorted_stocks})

        # 5. Cache Main Heatmap
        # Sort heatmap by performance
        heatmap_summary.sort(key=lambda x: x["change_pct"], reverse=True)
        await self._cache_set("qai:market:sector_heatmap", {"status": "success", "data": heatmap_summary})
        
        logger.info(f"Updated Sector Heatmap: {len(heatmap_summary)} sectors processed")

    async def _cache_set(self, key: str, value: Any):
        # Using 60s TTL to ensure freshness but allow some persistence if service crashes
        try:
            # Dragonfly client might expect dict directly if wrapper handles serialization
            # Or json string. Checking existing usage in Nifty100RankingService: 
            # self._cache.set(cache_key, asdict(result), ttl=ttl)
            # So passing dict is fine.
            self._cache.set(key, value, ttl=600) # 10 min TTL, overwritten every 30s
        except Exception as e:
            logger.error(f"Cache write failed for {key}: {e}")

# Singleton
_sector_service = None

def get_sector_service():
    global _sector_service
    if _sector_service is None:
        _sector_service = SectorPerformanceService()
    return _sector_service

async def start_sector_service():
    service = get_sector_service()
    await service.start()
