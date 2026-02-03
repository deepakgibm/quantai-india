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
from services.intraday_scanners import VWAPScannerV2, GapScannerV2, MomentumScannerV2, SRBounceScannerV2

logger = logging.getLogger(__name__)
router = APIRouter()
ai_service = get_ai_service()

@router.get("/strategies")
async def get_ai_strategies(current_user: User = Depends(get_current_user)):
    """Get available AI strategies"""
    return {
        "status": "success",
        "strategies": [
            {"id": "trend-finder", "name": "Trend Finder AI", "description": "Identifies strong trend continuation setups"},
            {"id": "breakout-detector", "name": "Breakout Detector", "description": "Detects volume-backed breakouts"},
            {"id": "top5-picks", "name": "Top 5 Picks", "description": "Daily top 5 buy/sell recommendations"},
            {"id": "momentum-scanner", "name": "Momentum Scanner", "description": "High momentum stocks"},
            {"id": "mean-reversion", "name": "Mean Reversion", "description": "Oversold/Overbought reversal setups"},
            {"id": "vwap-scanner", "name": "VWAP Trading", "description": "VWAP crossovers with LIVE prices"},
            {"id": "sr-bounce", "name": "Support/Resistance", "description": "Bounce signals from S/R levels"}
        ]
    }

@router.post("/prompt", response_model=AIPromptResponse)
async def process_ai_prompt(request: AIPromptRequest, current_user: User = Depends(get_current_user)):
    try:
        results = await ai_service.process_prompt(request.prompt, getattr(current_user, "upstox_access_token", None))
        return {
            "status": "success",
            "suggested_stocks": results
        }
    except Exception as e:
        logger.error(f"AI prompt processing failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "suggested_stocks": []
        }

@router.get("/market-analysis", response_model=MarketAnalysisResponse)
async def get_market_analysis(current_user: User = Depends(get_current_user)):
    try:
        return await ai_service.get_market_analysis()
    except Exception as e:
        logger.error(f"Market analysis failed: {e}")
        from datetime import datetime
        return {
            "status": "error",
            "analysis": f"Market analysis unavailable: {str(e)}",
            "sentiment": "NEUTRAL",
            "trend": "SIDEWAYS",
            "top_sectors": [],
            "stocks_to_watch": [],
            "timestamp": datetime.now().isoformat()
        }

# --- AI Scanners (Unversioned/Legacy) ---

@router.get("/trend-finder", response_model=ScannerResponse)
async def get_trend_finder_stocks(current_user: User = Depends(get_current_user)):
    return await ai_service.run_scanner(TrendAnalyzer, "Trend Finder", "trend-finder")

@router.get("/breakout-detector", response_model=ScannerResponse)
@router.get("/breakout-stocks", response_model=ScannerResponse)
async def get_breakout_stocks(current_user: User = Depends(get_current_user)):
    return await ai_service.run_scanner(BreakoutDetector, "Breakout Detector", "breakout-detector")

@router.get("/top5-picks", response_model=ScannerResponse)
@router.get("/top3-picks", response_model=ScannerResponse)
async def get_top5_picks(current_user: User = Depends(get_current_user)):
    return await ai_service.run_scanner(Top5BuySellEngine, "Top 5 Picks", "top5-picks")

@router.get("/momentum", response_model=ScannerResponse)
@router.get("/momentum-scanner", response_model=ScannerResponse)
async def get_momentum_stocks(current_user: User = Depends(get_current_user)):
    return await ai_service.run_scanner(MomentumScannerV2, "Momentum Scanner", "momentum")

@router.get("/mean-reversion", response_model=ScannerResponse)
@router.get("/mean-reversion-scanner", response_model=ScannerResponse)
async def get_mean_reversion_stocks(current_user: User = Depends(get_current_user)):
    return await ai_service.run_scanner(MeanReversionScanner, "Mean Reversion Scanner", "mean-reversion")

@router.get("/gap", response_model=ScannerResponse)
@router.get("/gap-scanner", response_model=ScannerResponse)
async def get_gap_stocks(current_user: User = Depends(get_current_user)):
    return await ai_service.run_scanner(GapScannerV2, "Gap Scanner", "gap")

@router.get("/relative-strength", response_model=ScannerResponse)
async def get_relative_strength_stocks(current_user: User = Depends(get_current_user)):
    return await ai_service.run_scanner(RelativeStrengthScanner, "Relative Strength Scanner", "relative-strength")

@router.get("/vwap", response_model=ScannerResponse)
@router.get("/vwap-scanner", response_model=ScannerResponse)
async def get_vwap_stocks(current_user: User = Depends(get_current_user)):
    return await ai_service.run_scanner(VWAPScannerV2, "VWAP Scanner", "vwap")

@router.get("/sr-bounce", response_model=ScannerResponse)
async def get_sr_bounce_stocks(current_user: User = Depends(get_current_user)):
    return await ai_service.run_scanner(SRBounceScannerV2, "S/R Bounce Scanner", "sr-bounce")

# Sentiment Consolidation
@router.get("/sentiment", response_model=Dict[str, Any])
async def get_market_sentiment(current_user: User = Depends(get_current_user)):
    """Get consolidated market sentiment analysis."""
    analysis = await ai_service.get_market_analysis()
    return {
        "status": "success",
        "sentiment": analysis.get("sentiment", "NEUTRAL"),
        "trend": analysis.get("trend", "SIDEWAYS"),
        "analysis": analysis.get("analysis", ""),
        "timestamp": analysis.get("timestamp", "")
    }
