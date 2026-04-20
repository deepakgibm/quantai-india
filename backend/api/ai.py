from fastapi import APIRouter, Depends
import logging
from typing import Dict, Any
from models import User
from schemas import (
    AIPromptRequest, AIPromptResponse, ScannerResponse, MarketAnalysisResponse
)
from utils.auth import get_current_user
from services.ai_service import get_ai_service

# Detectors for scanner logic
from services.trend_analyzer import TrendAnalyzer
from services.breakout_detector import BreakoutDetector
from services.top5_buysell import Top5BuySellEngine
from services.mean_reversion_scanner import MeanReversionScanner
from services.relative_strength_scanner import RelativeStrengthScanner
from services.vwap_scanner import VWAPScanner
from services.gap_scanner import GapScanner
from services.momentum_scanner import MomentumScanner
from services.sr_bounce_scanner import SRBounceScanner

logger = logging.getLogger(__name__)
router = APIRouter(tags=["AI Services"])
ai_service = get_ai_service()

@router.get("/trend-finder")
async def get_trend_finder(current_user: User = Depends(get_current_user)):
    """AI Trend Finder Scanner."""
    from services.trend_analyzer import TrendAnalyzer
    return await ai_service.run_scanner(TrendAnalyzer, "Trend Finder", "trend-finder")

@router.get("/breakout-detector")
async def get_breakout_detector(current_user: User = Depends(get_current_user)):
    """AI Breakout Detector."""
    from services.breakout_detector import BreakoutDetector
    return await ai_service.run_scanner(BreakoutDetector, "Breakout Detector", "breakout-detector")

@router.get("/top5-picks")
async def get_top5_picks_ai(current_user: User = Depends(get_current_user)):
    """Daily Top 5 AI Picks."""
    from services.top5_buysell import Top5BuySellEngine
    return await ai_service.run_scanner(Top5BuySellEngine, "Top Picks", "top5-picks")

@router.get("/momentum-scanner")
async def get_momentum_scanner(current_user: User = Depends(get_current_user)):
    """Intraday Momentum Scanner."""
    from services.momentum_scanner import MomentumScanner
    return await ai_service.run_scanner(MomentumScanner, "Momentum Scanner", "momentum")

@router.get("/mean-reversion")
async def get_mean_reversion(current_user: User = Depends(get_current_user)):
    """Mean Reversion Scanner."""
    from services.mean_reversion_scanner import MeanReversionScanner
    return await ai_service.run_scanner(MeanReversionScanner, "Mean Reversion", "mean-reversion")

@router.get("/gap-scanner")
async def get_gap_scanner(current_user: User = Depends(get_current_user)):
    """Gap Up/Down Scanner."""
    from services.gap_scanner import GapScanner
    return await ai_service.run_scanner(GapScanner, "Gap Scanner", "gap")

@router.get("/relative-strength")
async def get_relative_strength(current_user: User = Depends(get_current_user)):
    """Relative Strength Scanner."""
    from services.relative_strength_scanner import RelativeStrengthScanner
    return await ai_service.run_scanner(RelativeStrengthScanner, "Relative Strength", "relative-strength")

@router.get("/vwap-scanner")
async def get_vwap_scanner(current_user: User = Depends(get_current_user)):
    """VWAP Scanner."""
    from services.vwap_scanner import VWAPScanner
    return await ai_service.run_scanner(VWAPScanner, "VWAP Scanner", "vwap")

@router.get("/sr-bounce")
async def get_sr_bounce(current_user: User = Depends(get_current_user)):
    """Support/Resistance Bounce Scanner."""
    from services.sr_bounce_scanner import SRBounceScanner
    return await ai_service.run_scanner(SRBounceScanner, "SR Bounce", "sr_bounce")

@router.get("/strategies")
async def get_ai_strategies(current_user: User = Depends(get_current_user)):
    """Get list of available AI strategies and bots."""
    return {
        "status": "success",
        "strategies": [
            {"id": "trend-finder", "name": "Trend Finder AI", "description": "Identifies strong trend continuation setups"},
            {"id": "breakout-detector", "name": "Breakout Detector", "description": "Detects volume-backed breakouts"},
            {"id": "quantai-chat", "name": "QuantAI Chat", "description": "Intelligent market analysis via LLM"}
        ]
    }

@router.post("/prompt", response_model=AIPromptResponse)
async def process_ai_prompt(request: AIPromptRequest, current_user: User = Depends(get_current_user)):
    """Natural language market query processing."""
    try:
        results = await ai_service.process_prompt(request.prompt, getattr(current_user, "upstox_access_token", None))
        return {"status": "success", "suggested_stocks": results}
    except Exception as e:
        logger.error(f"AI prompt processing failed: {e}")
        return {"status": "error", "message": str(e), "suggested_stocks": []}

@router.get("/market-analysis", response_model=MarketAnalysisResponse)
async def get_market_analysis(current_user: User = Depends(get_current_user)):
    """Deep market sentiment and structural analysis."""
    try:
        return await ai_service.get_market_analysis()
    except Exception as e:
        logger.error(f"Market analysis failed: {e}")
        from datetime import datetime
        return {
            "status": "error",
            "analysis": f"Market analysis unavailable: {str(e)}",
            "sentiment": "NEUTRAL", "trend": "SIDEWAYS",
            "top_sectors": [], "stocks_to_watch": [],
            "timestamp": datetime.now().isoformat()
        }

@router.get("/sentiment")
async def get_market_sentiment(current_user: User = Depends(get_current_user)):
    """Condensed market sentiment summary."""
    analysis = await ai_service.get_market_analysis()
    return {
        "status": "success",
        "sentiment": analysis.get("sentiment", "NEUTRAL"),
        "trend": analysis.get("trend", "SIDEWAYS"),
        "analysis": analysis.get("analysis", ""),
        "timestamp": analysis.get("timestamp", "")
    }
