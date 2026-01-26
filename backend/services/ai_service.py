import json
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from fastapi import HTTPException
from config import settings
from services.live_price_enricher import get_live_ltp, enrich_scanner_results
from services.dragonfly_client import get_cache

logger = logging.getLogger(__name__)

class AIService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIService, cls).__new__(cls)
            cls._instance._initialize_model()
        return cls._instance

    def _initialize_model(self):
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model_name = self._get_working_model()
                self._model = genai.GenerativeModel(model_name)
                logger.info(f"AIService: Initialized Gemini model: {model_name}")
            except Exception as e:
                logger.error(f"AIService: Failed to initialize Gemini AI: {e}")
                self._model = None
        else:
            logger.warning("AIService: GEMINI_API_KEY not set")
            self._model = None

    def _get_working_model(self) -> str:
        """Dynamically finds the best available 'flash' model."""
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # Prioritize flash models for speed
            flash_models = [m for m in available_models if 'flash' in m.lower()]
            if flash_models:
                # Use latest flash model
                return sorted(flash_models, reverse=True)[0]
            # Fallback to any model
            return "gemini-1.5-pro" if "models/gemini-1.5-pro" in available_models else "gemini-pro"
        except Exception:
            return "gemini-1.5-flash"

    async def process_prompt(self, prompt: str, access_token: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self._model:
            raise HTTPException(status_code=503, detail="Gemini AI service unavailable")

        enhanced_prompt = f"""You are a professional stock trading advisor for the Indian stock market (NSE Cash Segment only).

User Query: {prompt}

IMPORTANT: Respond ONLY with a valid JSON array of stock recommendations. Do not include any other text, markdown formatting, or code blocks.

Each stock recommendation must follow this exact structure:
[
  {{
    "symbol": "STOCK_SYMBOL",
    "name": "Company Full Name",
    "action": "BUY" or "SELL" or "WAIT",
    "trade_type": "Intraday" or "Short-Term" or "Weekly",
    "price": current_price_estimate,
    "entry_price": recommended_entry_price,
    "target_price": target_price_for_profit,
    "stop_loss": stop_loss_price,
    "risk_reward": "1:2" or "1:3" etc,
    "confidence": confidence_percentage (0-100),
    "reason": "Brief explanation of why this stock is recommended (max 200 characters)"
  }}
]

Guidelines:
- Provide 3-5 specific stock recommendations from NIFTY 50/200
- Use actual NSE stock symbols (e.g., "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK")
- Base recommendations on current market trends, technical analysis, and sector performance
- Only respond with the JSON array, nothing else"""

        try:
            response = self._model.generate_content(enhanced_prompt)
            response_text = response.text.strip()
            
            # Extract JSON from potential markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].strip()
            
            parsed_response = json.loads(response_text)
            if not isinstance(parsed_response, list):
                return []

            results = []
            for stock_rec in parsed_response:
                symbol = stock_rec.get("symbol")
                if not symbol: continue
                
                # Enrich with live price
                price_result = await get_live_ltp(symbol, access_token or settings.UPSTOX_ACCESS_TOKEN)
                current_price = price_result.get("ltp")
                
                if current_price and current_price > 0:
                    stock_rec["price"] = current_price
                    # Default levels if missing
                    if not stock_rec.get("entry_price"):
                        stock_rec["entry_price"] = round(current_price * 0.995, 2) if stock_rec.get("action") == "BUY" else round(current_price * 1.005, 2)
                    if not stock_rec.get("target_price"):
                        stock_rec["target_price"] = round(current_price * 1.03, 2) if stock_rec.get("action") == "BUY" else round(current_price * 0.97, 2)
                    if not stock_rec.get("stop_loss"):
                        stock_rec["stop_loss"] = round(current_price * 0.98, 2) if stock_rec.get("action") == "BUY" else round(current_price * 1.02, 2)
                
                results.append(stock_rec)
            return results
        except Exception as e:
            logger.error(f"AIService: Prompt processing failed: {e}")
            raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")

    async def run_scanner(self, scanner_class, scanner_name: str, cache_key: str, limit: int = 10, timeout: float = 10.0) -> Dict[str, Any]:
        """Generic runner for AI technical scanners with caching and enrichment."""
        start_time = time.time()
        enriched_cache_key = f"{cache_key}:enriched"
        
        # 1. Check Cache
        cache = get_cache()
        if cache.is_available():
            # Check enriched cache (short TTL)
            cached_enriched = cache.get(enriched_cache_key)
            if cached_enriched:
                logger.info(f"AIService: {scanner_name} enriched cache hit")
                return cached_enriched
            
            # Check raw cache (longer TTL)
            cached_raw = cache.get(cache_key)
            if cached_raw:
                logger.info(f"AIService: {scanner_name} raw cache hit, enriching...")
                try:
                    if isinstance(cached_raw, dict) and "stocks" in cached_raw:
                        cached_raw["stocks"] = await enrich_scanner_results(cached_raw["stocks"], settings.UPSTOX_ACCESS_TOKEN)
                        cache.set(enriched_cache_key, cached_raw, ttl=60)
                        return cached_raw
                except Exception as e:
                    logger.error(f"AIService: {scanner_name} enrichment failed: {e}")

        # 2. Run Scan
        try:
            loop = asyncio.get_event_loop()
            def execute_scan():
                detector = scanner_class()
                return detector.scan_all(limit=limit)
            
            stocks = await asyncio.wait_for(
                loop.run_in_executor(None, execute_scan),
                timeout=timeout
            )
            
            if stocks:
                if isinstance(stocks, dict):
                    # Handle scanners that return separate buy/sell lists (like Top 5 Picks)
                    buy_signals = stocks.get("buy", [])
                    sell_signals = stocks.get("sell", [])
                    
                    enriched_buy = await enrich_scanner_results(buy_signals, settings.UPSTOX_ACCESS_TOKEN)
                    enriched_sell = await enrich_scanner_results(sell_signals, settings.UPSTOX_ACCESS_TOKEN)
                    
                    response = {
                        "status": "success",
                        "count": len(enriched_buy) + len(enriched_sell),
                        "stocks": enriched_buy + enriched_sell,
                        "buy_signals": enriched_buy,
                        "sell_signals": enriched_sell,
                        "scan_type": f"{scanner_name.lower().replace(' ', '_')}_technical",
                        "description": f"{scanner_name} with LIVE prices"
                    }
                else:
                    # Standard list return
                    enriched_stocks = await enrich_scanner_results(stocks, settings.UPSTOX_ACCESS_TOKEN)
                    response = {
                        "status": "success",
                        "count": len(enriched_stocks),
                        "stocks": enriched_stocks,
                        "scan_type": f"{scanner_name.lower().replace(' ', '_')}_technical",
                        "description": f"{scanner_name} with LIVE prices"
                    }
                
                if cache.is_available():
                    cache.set(cache_key, response, ttl=600)
                    cache.set(enriched_cache_key, response, ttl=60)
                
                return response
            
            return {
                "status": "success", 
                "count": 0, 
                "stocks": [], 
                "scan_type": f"{scanner_name.lower().replace(' ', '_')}_technical", 
                "description": "No matches found"
            }
            
        except asyncio.TimeoutError:
            logger.warning(f"AIService: {scanner_name} timed out after {timeout}s")
            return {"status": "timeout", "count": 0, "stocks": [], "description": "Scan timed out."}
        except Exception as e:
            logger.error(f"AIService: {scanner_name} error: {e}")
            return {
                "status": "error", 
                "count": 0, 
                "stocks": [], 
                "scan_type": cache_key,
                "description": f"{scanner_name} error: {str(e)}"
            }

    async def get_market_analysis(self) -> Dict[str, Any]:
        """AI Market Analysis - Summarizes current market state using technicals + Gemini."""
        start_time = time.time()
        cache_key = "market-analysis-daily"
        
        # 1. Check Cache
        cache = get_cache()
        if cache.is_available():
            cached = cache.get(f"qai:ai:strategy:{cache_key}")
            if cached:
                return cached

        if not self._model:
            raise HTTPException(status_code=503, detail="Gemini AI service unavailable")

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
            loop = asyncio.get_event_loop()
            def fetch_analysis():
                response = self._model.generate_content(prompt)
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].strip()
                return json.loads(text)

            result = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_analysis),
                timeout=12.0
            )
            
            if "timestamp" not in result:
                result["timestamp"] = time.strftime("%Y-%m-%d")
            
            if cache.is_available():
                cache.set(f"qai:ai:strategy:{cache_key}", result, ttl=600)
                
            return result
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "analysis": "Market analysis is taking longer than expected.",
                "sentiment": "NEUTRAL",
                "trend": "SIDEWAYS",
                "timestamp": time.strftime("%Y-%m-%d")
            }
        except Exception as e:
            logger.error(f"AIService: Market analysis failed: {e}")
            return {
                "status": "error",
                "analysis": f"Market analysis unavailable: {str(e)[:100]}",
                "sentiment": "NEUTRAL",
                "trend": "SIDEWAYS",
                "timestamp": time.strftime("%Y-%m-%d")
            }

_ai_service = None

def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
