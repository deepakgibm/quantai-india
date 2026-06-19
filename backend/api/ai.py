from fastapi import APIRouter, Depends
import logging
from typing import Dict, Any
from models import User
from schemas import (
    AIPromptRequest, AIPromptResponse, ScannerResponse, MarketAnalysisResponse
)
from utils.auth import get_current_user
from services.ai_service import get_ai_service
from config import settings

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

@router.get("/momentum")
async def get_momentum_scanner_alias(current_user: User = Depends(get_current_user)):
    """Intraday Momentum Scanner alias."""
    return await get_momentum_scanner(current_user)

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

@router.get("/vwap")
async def get_vwap_scanner_alias(current_user: User = Depends(get_current_user)):
    """VWAP Scanner alias."""
    return await get_vwap_scanner(current_user)

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

from database import get_db
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Holding, Position

@router.post("/prompt", response_model=AIPromptResponse)
async def process_ai_prompt(
    request: AIPromptRequest, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Natural language market query processing with portfolio and watchlist context."""
    try:
        # 1. Fetch user holdings & positions context
        holdings_query = select(Holding).where(Holding.user_id == current_user.id)
        holdings_res = await db.execute(holdings_query)
        holdings = holdings_res.scalars().all()
        
        positions_query = select(Position).where(Position.user_id == current_user.id)
        positions_res = await db.execute(positions_query)
        positions = positions_res.scalars().all()
        
        # 2. Formulate context
        portfolio_desc = ""
        if holdings:
            portfolio_desc += "Holdings: " + ", ".join([f"{h.symbol} ({h.quantity} shares @ avg ₹{h.avg_price})" for h in holdings]) + ". "
        else:
            portfolio_desc += "Holdings: RELIANCE (100 shares @ ₹2400), TCS (50 shares @ ₹3200), HDFCBANK (150 shares @ ₹1450). "
            
        if positions:
            portfolio_desc += "Open Positions: " + ", ".join([f"{p.symbol} ({p.quantity} @ ₹{p.avg_price}, PnL: ₹{p.pnl})" for p in positions]) + ". "
        else:
            portfolio_desc += "Open Positions: None active. "
            
        portfolio_desc += "Watchlist: INFY, BHEL, SBIN, ITC."
        
        # 3. Inject context into prompt
        enriched_prompt = f"[USER CONTEXT - {portfolio_desc}] User Query: {request.prompt}"
        
        results = await ai_service.process_prompt(enriched_prompt, getattr(current_user, "upstox_access_token", None))
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

@router.get("/explain-signal")
async def explain_trading_signal(
    symbol: str,
    signal_type: str,
    price: float,
    conviction: str,
    current_user: User = Depends(get_current_user)
):
    """Generates LLM-backed explanation for generated signals."""
    if not settings.ENABLE_AI_FEATURES or settings.MOCK_AI_RESPONSES:
        return {
            "status": "success",
            "explanation": f"The {conviction} conviction {signal_type} signal for {symbol} was triggered at ₹{price} due to a confluence of: (1) RSI bouncing from oversold/overbought boundaries, (2) EMA crossover indicating trend continuation, and (3) volume expansion confirming structural breakout strength."
        }
        
    try:
        from services.ai.provider import get_ai_provider
        provider = get_ai_provider()
        prompt = f"Explain to a trader why a {conviction} conviction {signal_type} signal was generated for stock {symbol} trading at ₹{price}. Keep the explanation under 250 characters and professional."
        explanation = await provider.generate_content(prompt)
        return {"status": "success", "explanation": explanation}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/market-summary")
async def generate_ai_market_summary(
    current_user: User = Depends(get_current_user)
):
    """Generates AI market summary."""
    if not settings.ENABLE_AI_FEATURES or settings.MOCK_AI_RESPONSES:
        return {
            "status": "unavailable",
            "message": "Market summary temporarily unavailable."
        }
        
    try:
        from services.ai.provider import get_ai_provider
        provider = get_ai_provider()
        prompt = "Provide a 2-sentence market summary for Indian stock indices today. Highlight energy/infra leadership and consolidation in tech."
        summary = await provider.generate_content(prompt)
        return {"status": "success", "summary": summary}
    except Exception as e:
        logger.error(f"AI Market Summary Generation failed: {e}")
        return {
            "status": "unavailable",
            "message": "Market summary temporarily unavailable."
        }

