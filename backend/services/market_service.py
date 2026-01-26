import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.dragonfly_client import get_cache
from services.market_hours_service import get_market_hours_service
from services.nifty100_ranking_service import get_nifty100_ranking_service
from utils.market_fallback import fetch_live_indices_yfinance

logger = logging.getLogger(__name__)

class MarketService:
    async def get_nifty100_top_movers(self, limit: int = 5) -> Dict[str, Any]:
        """Get top gainers and losers from Nifty 100."""
        service = get_nifty100_ranking_service()
        rankings = await service.get_rankings()
        
        # Rankings structure contains 'gainers', 'losers', 'timestamp', 'source'
        return {
            "status": "success",
            "timestamp": rankings.get("timestamp", datetime.now().isoformat()),
            "gainers": rankings.get("gainers", [])[:limit],
            "losers": rankings.get("losers", [])[:limit],
            "source": rankings.get("source", "unknown")
        }

    async def get_global_market_context(self) -> Dict[str, Any]:
        """Fetch global market context for sentiment analysis."""
        # This originally used fetch_live_indices_yfinance but with specific symbols
        # For now, we'll reuse the unified yfinance fetcher
        indices = await fetch_live_indices_yfinance()
        
        # Calculate a simple sentiment
        bullish = sum(1 for i in indices if i.get('percent', 0) > 0)
        total = len(indices)
        sentiment = "NEUTRAL"
        if total > 0:
            ratio = bullish / total
            if ratio > 0.6: sentiment = "BULLISH"
            elif ratio < 0.4: sentiment = "BEARISH"

        return {
            "status": "success",
            "sentiment": sentiment,
            "indices": indices,
            "timestamp": datetime.now().isoformat()
        }

    async def get_sector_performance(self) -> List[Dict[str, Any]]:
        """Fetch real-time industry/sector performance from cache."""
        cache = get_cache()
        heatmap = cache.get("qai:market:sector_heatmap")
        if heatmap:
            return heatmap
        
        # Minimal default if cache empty
        return []

    async def get_sector_stocks(self, sector_name: str) -> List[Dict[str, Any]]:
        """Get stocks performance within a specific sector."""
        cache = get_cache()
        # The key pattern is usually qai:market:sector_stocks:{sector_name}
        stocks = cache.get(f"qai:market:sector_stocks:{sector_name}")
        return stocks or []

_market_service = None
def get_market_service():
    global _market_service
    if _market_service is None:
        _market_service = MarketService()
    return _market_service
