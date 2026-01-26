import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

# Mock genai to avoid API calls and protobuf issues in test
import google.generativeai as genai
genai.configure = MagicMock()
genai.GenerativeModel = MagicMock()
genai.list_models = MagicMock(return_value=[MagicMock(name="models/gemini-1.5-flash", supported_generation_methods=["generateContent"])])

from services.ai_service import get_ai_service
from schemas import AIPromptRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_ai_refactor():
    logger.info("Verifying AI Refactor...")
    
    # 1. Test AIService Initialization
    service = get_ai_service()
    if service._model is not None:
        logger.info("✅ AIService initialized with mocked model")
    else:
        logger.error("❌ AIService failed to initialize model (check GEMINI_API_KEY)")

    # 2. Test Router Wrapper (simulated)
    # We won't start a real server, just check if we can call the service methods
    # Mocking price enricher for speed
    import services.live_price_enricher
    services.live_price_enricher.get_live_ltp = AsyncMock(return_value={"ltp": 2500.0})
    
    # Mock model response
    mock_response = MagicMock()
    mock_response.text = '[{"symbol": "RELIANCE", "action": "BUY", "confidence": 85, "reason": "Strong momentum"}]'
    service._model.generate_content = MagicMock(return_value=mock_response)
    
    logger.info("Testing prompt processing...")
    results = await service.process_prompt("Buy some stocks")
    if len(results) > 0 and results[0]['symbol'] == "RELIANCE":
        logger.info(f"✅ Prompt processed successfully: {results}")
    else:
        logger.error(f"❌ Prompt processing failed: {results}")

    # 3. Test Scanner Runner
    logger.info("Testing scanner runner delegation...")
    from services.breakout_detector import BreakoutDetector
    # Mock detector
    BreakoutDetector.scan_all = MagicMock(return_value=[{"symbol": "TCS", "score": 80}])
    
    # Mock dragonfly cache
    import services.dragonfly_client
    services.dragonfly_client.get_cache = MagicMock()
    services.dragonfly_client.get_cache().is_available = MagicMock(return_value=False)

    scan_result = await service.run_scanner(BreakoutDetector, "Breakout", "test-key")
    if scan_result['status'] == 'success' and len(scan_result['stocks']) > 0:
        logger.info("✅ Scanner runner delegated successfully")
    else:
        logger.error(f"❌ Scanner runner failed: {scan_result}")

if __name__ == "__main__":
    asyncio.run(verify_ai_refactor())
