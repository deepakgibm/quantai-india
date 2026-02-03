import logging
from typing import List, Dict, Any, Optional
from services.ai.provider import get_ai_provider
from services.ai.market_analyst import get_market_analyst
from services.ai.scanner_runner import get_scanner_runner
from utils.json_utils import sanitize_for_json
from services.live_price_enricher import enrich_scanner_results

logger = logging.getLogger(__name__)

class AIService:
    """
    Facade for AI services.
    Delegates to specialized components:
    - AIProvider (Gemini connection)
    - MarketAnalyst (Market analysis)
    - ScannerRunner (Scanner execution)
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIService, cls).__new__(cls)
            # Initialize sub-components
            cls._instance.provider = get_ai_provider()
            cls._instance.analyst = get_market_analyst()
            cls._instance.runner = get_scanner_runner()
        return cls._instance

    async def process_prompt(self, prompt: str, access_token: Optional[str] = None) -> List[Dict[str, Any]]:
        
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
            # provider.generate_content is now async and non-blocking
            response_text = await self.provider.generate_content(enhanced_prompt)
            parsed_response = self.provider.extract_json(response_text)

            if not isinstance(parsed_response, list):
                if isinstance(parsed_response, dict):
                    parsed_response = [parsed_response]
                else:
                    return []

            results = []
            from config import settings
            for stock_rec in parsed_response:
                symbol = stock_rec.get("symbol")
                if not symbol: continue
                
                # Enrich with live price and validate trade levels
                try:
                    # Pass as a single-item list to enrichment service
                    enriched_list = await enrich_scanner_results([stock_rec], access_token or settings.UPSTOX_ACCESS_TOKEN)
                    if enriched_list:
                        results.append(enriched_list[0])
                    else:
                        logger.warning(f"AIService: Recommendation for {symbol} rejected by logic guardrails")
                except Exception as pe:
                    logger.warning(f"AIService: Price enrichment failed for {symbol}: {pe}")
            
            logger.info(f"AIService: Successfully processed {len(results)} recommendations")
            return results
        except Exception as e:
            logger.error(f"AIService: Prompt processing failed: {e}", exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")

    def _sanitize_for_json(self, data: Any) -> Any:
        return sanitize_for_json(data)

    async def run_scanner(self, scanner_class, scanner_name: str, cache_key: str, limit: int = 10, timeout: float = 10.0) -> Dict[str, Any]:
        return await self.runner.run_scanner(scanner_class, scanner_name, cache_key, limit, timeout)

    async def get_market_analysis(self) -> Dict[str, Any]:
        return await self.analyst.get_market_analysis()

_ai_service = None

def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
