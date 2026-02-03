import logging
import asyncio
import time
from typing import Dict, Any
from services.ai.provider import get_ai_provider
from services.dragonfly_client import get_cache
from utils.json_utils import sanitize_for_json

logger = logging.getLogger(__name__)

class MarketAnalyst:
    def __init__(self):
        self.provider = get_ai_provider()

    async def get_market_analysis(self) -> Dict[str, Any]:
        """AI Market Analysis - Summarizes current market state using technicals + Gemini."""
        cache_key = "market-analysis-daily"
        
        # 1. Check Cache
        cache = get_cache()
        if cache.is_available():
            cached = cache.get(f"qai:ai:strategy:{cache_key}")
            if cached:
                return cached

        prompt = """Perform a comprehensive daily market analysis for the Indian stock market (NIFTY 50).
Provide the analysis in the following JSON format strictly:
{
  "status": "success",
  "analysis": "A detailed 2-3 sentence analysis of current market trends and levels.",
  "sentiment": "BULLISH/BEARISH/NEUTRAL",
  "trend": "UPTREND/DOWNTREND/SIDEWAYS",
  "top_sectors": ["Sector 1", "Sector 2"],
  "stocks_to_watch": ["STOCK1", "STOCK2"],
  "timestamp": "YYYY-MM-DD"
}"""

        try:
            # Using wait_for to enforce timeout
            response_text = await asyncio.wait_for(
                self.provider.generate_content(prompt),
                timeout=15.0
            )
            
            result = self.provider.extract_json(response_text)
            
            if "timestamp" not in result:
                result["timestamp"] = time.strftime("%Y-%m-%d")
            
            # Sanitize before returning/caching
            result = sanitize_for_json(result)

            if cache.is_available():
                cache.set(f"qai:ai:strategy:{cache_key}", result, ttl=600)
                
            return result
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "analysis": "Market analysis is taking longer than expected.",
                "sentiment": "NEUTRAL",
                "trend": "SIDEWAYS",
                "top_sectors": [],
                "stocks_to_watch": [],
                "timestamp": time.strftime("%Y-%m-%d")
            }
        except Exception as e:
            logger.error(f"MarketAnalyst: Analysis failed: {e}")
            return {
                "status": "error",
                "analysis": f"Market analysis unavailable: {str(e)[:100]}",
                "sentiment": "NEUTRAL",
                "trend": "SIDEWAYS",
                "top_sectors": [],
                "stocks_to_watch": [],
                "timestamp": time.strftime("%Y-%m-%d")
            }

_analyst = None
def get_market_analyst() -> MarketAnalyst:
    global _analyst
    if _analyst is None:
        _analyst = MarketAnalyst()
    return _analyst
