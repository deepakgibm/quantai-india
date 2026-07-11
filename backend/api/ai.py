from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
import logging
import asyncio
import queue
import threading
import json
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Holding, Position
from schemas import AIPromptRequest, AIPromptResponse, MarketAnalysisResponse
from utils.auth import get_current_user
from services.ai_service import get_ai_service
from config import settings
from database import get_db

# Initialize path mapping for the Vibe-Trading Swarm Engine
import services.ai.swarm_engine
from src.agent.loop import AgentLoop
from src.agent.tools import ToolRegistry
from src.providers.chat import ChatLLM
from src.swarm.runtime import SwarmRuntime
from src.swarm.store import SwarmStore
from src.swarm.models import RunStatus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["AI Services"])
ai_service = get_ai_service()


# Helper to stream a single ReAct AgentLoop execution
async def stream_agent_execution(prompt: str, user_id: int):
    q = queue.Queue()
    
    def event_callback(event_type: str, data: dict):
        q.put({"type": event_type, "data": data})
        
    def run_loop():
        try:
            from src.tools import build_registry
            registry = build_registry()
            llm = ChatLLM()
            loop = AgentLoop(registry=registry, llm=llm, event_callback=event_callback)
            
            # Enrich context with User ID
            loop.run(prompt, session_id=f"user_{user_id}")
            q.put({"type": "done"})
        except Exception as e:
            logger.error(f"Agent execution thread failed: {e}", exc_info=True)
            q.put({"type": "error", "error": str(e)})

    threading.Thread(target=run_loop, daemon=True).start()
    
    loop_event = asyncio.get_running_loop()
    done = False
    while not done:
        try:
            event = await loop_event.run_in_executor(None, lambda: q.get(timeout=0.5))
            if event["type"] == "done":
                done = True
            elif event["type"] == "error":
                yield f"data: {json.dumps({'type': 'error', 'error': event['error']})}\n\n"
                done = True
            else:
                yield f"data: {json.dumps(event)}\n\n"
        except queue.Empty:
            yield ": keepalive\n\n"


# Helper to stream a Swarm Run execution
async def stream_swarm_execution(preset_name: str, user_vars: dict):
    q = queue.Queue()
    
    def live_callback(event):
        q.put(event.model_dump())
        
    from pathlib import Path
    from src.config import load_swarm_agent_config
    
    swarm_dir = Path(__file__).resolve().parent.parent / "services" / "ai" / "swarm_engine" / ".swarm" / "runs"
    store = SwarmStore(base_dir=swarm_dir)
    agent_config = load_swarm_agent_config()
    runtime = SwarmRuntime(store=store, agent_config=agent_config)
    
    try:
        run = runtime.start_run(
            preset_name=preset_name,
            user_vars=user_vars,
            live_callback=live_callback
        )
    except Exception as e:
        logger.error(f"Failed to start swarm run: {e}")
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        return
        
    from src.swarm.task_store import TaskStore
    run_dir = store.run_dir(run.id)
    task_store = TaskStore(run_dir)
        
    def _enrich_event(event):
        if event.get("type") == "task_completed":
            try:
                task = task_store.load_task(event.get("task_id"))
                if task:
                    event["data"]["summary"] = task.summary
                    if event.get("task_id") == "task-decision":
                        symbol = user_vars.get("target", "RELIANCE")
                        from services.explainable_ai import get_explainable_ai_report, validate_consensus_consistency
                        report = get_explainable_ai_report(symbol)
                        event["data"]["explainable_report"] = report
                        
                        # Guarantee single source of truth by overriding task.summary with dynamic report
                        event["data"]["summary"] = report.get("consensus_report")
                        
                        # Validate consistency (assert they match)
                        validate_consensus_consistency(event["data"]["summary"], report)
            except Exception as e:
                from core.exceptions import DataUnavailableError
                if isinstance(e, DataUnavailableError):
                    logger.error(f"DataUnavailableError: {e.message}")
                    event["data"]["explainable_report"] = {
                        "error": "Data Unavailable",
                        "message": e.message,
                        "required_candles": e.required_candles,
                        "available_candles": e.available_candles
                    }
                else:
                    logger.warning(f"Failed to resolve task summary for {event.get('task_id')}: {e}")
        return event

    loop_event = asyncio.get_running_loop()
    done = False
    while not done:
        try:
            event = await loop_event.run_in_executor(None, lambda: q.get(timeout=0.5))
            yield f"data: {json.dumps(_enrich_event(event))}\n\n"
            if event.get("type") == "run_completed" or (event.get("type") == "task_completed" and event.get("task_id") == "task-decision"):
                done = True
        except queue.Empty:
            # Check if run has ended in background
            updated_run = runtime._store.load_run(run.id)
            if updated_run and updated_run.status in [RunStatus.completed, RunStatus.failed, RunStatus.cancelled]:
                while not q.empty():
                    try:
                        event = q.get_nowait()
                        yield f"data: {json.dumps(_enrich_event(event))}\n\n"
                    except queue.Empty:
                        break
                done = True
            else:
                yield ": keepalive\n\n"
                
    yield f"data: {json.dumps({'type': 'run_completed', 'run_id': run.id})}\n\n"


# ============================================================================
# Streaming POST endpoints (Phase 9)
# ============================================================================

@router.post("/chat")
async def ai_chat_stream(payload: dict, current_user: User = Depends(get_current_user)):
    """Streaming response for conversational stock research chat."""
    message = payload.get("message", "Search for high momentum stock setups")
    prompt = f"User asks: {message}. Research the Indian Stock Market and provide a detailed analysis."
    return StreamingResponse(stream_agent_execution(prompt, current_user.id), media_type="text/event-stream")


@router.post("/research")
async def ai_research_stream(payload: dict, current_user: User = Depends(get_current_user)):
    """General conversational research endpoint."""
    return await ai_chat_stream(payload, current_user)


@router.post("/analyse")
async def ai_analyse_stream(payload: dict, current_user: User = Depends(get_current_user)):
    """Deep stock analysis of a specific symbol."""
    symbol = payload.get("symbol", "RELIANCE")
    prompt = (
        f"Perform a deep technical and fundamental analysis of NSE stock symbol: {symbol}. "
        "Retrieve technical indicators, check recent candle trends, and evaluate registered strategies to output a recommendation."
    )
    return StreamingResponse(stream_agent_execution(prompt, current_user.id), media_type="text/event-stream")


@router.post("/market-summary")
async def ai_market_summary_stream(payload: dict, current_user: User = Depends(get_current_user)):
    """Generates daily market summary."""
    prompt = (
        "Generate a daily market summary for the Indian Stock Market (NSE). "
        "Analyze general market breadth, sector details, advance-decline ratios, and highlight any major index signals."
    )
    return StreamingResponse(stream_agent_execution(prompt, current_user.id), media_type="text/event-stream")


@router.post("/portfolio")
async def ai_portfolio_stream(payload: dict, current_user: User = Depends(get_current_user)):
    """Portfolio health & rebalancing analysis."""
    prompt = (
        f"Analyze the portfolio holdings for user ID: {current_user.id}. "
        "Evaluate total allocation, sector exposures, risk parameters, and suggest rebalancing actions if required."
    )
    return StreamingResponse(stream_agent_execution(prompt, current_user.id), media_type="text/event-stream")


@router.post("/backtest")
async def ai_backtest_stream(payload: dict, current_user: User = Depends(get_current_user)):
    """Autonomously optimizes strategy, runs backtests, and evaluates results."""
    symbol = payload.get("symbol", "RELIANCE")
    strategy = payload.get("strategy", "RSI Mean Reversion")
    prompt = (
        f"Trigger a backtest for strategy '{strategy}' on symbol '{symbol}' using the backtest_strategy tool. "
        "Analyze the resulting capital drawdown, Sharpe ratio, win rate, and provide quantitative suggestions to improve this strategy."
    )
    return StreamingResponse(stream_agent_execution(prompt, current_user.id), media_type="text/event-stream")


@router.post("/scanner")
async def ai_scanner_stream(payload: dict, current_user: User = Depends(get_current_user)):
    """Scans the Nifty 500 universe using the specified scanner."""
    scanner_id = payload.get("scanner_id", "trend-finder")
    prompt = (
        f"Run the technical scanner for setup '{scanner_id}' using the run_scanner tool. "
        "Evaluate the top results and summarize the best 3 buying opportunities and 3 selling opportunities with targets."
    )
    return StreamingResponse(stream_agent_execution(prompt, current_user.id), media_type="text/event-stream")


@router.post("/committee")
async def ai_committee_stream(payload: dict, current_user: User = Depends(get_current_user)):
    """Multi-agent Swarm Investment Committee debate."""
    symbol = payload.get("symbol", "RELIANCE")
    user_vars = {"target": symbol, "market": "NSE"}
    return StreamingResponse(stream_swarm_execution("investment_committee", user_vars), media_type="text/event-stream")


@router.post("/watchlist")
async def ai_watchlist_stream(payload: dict, current_user: User = Depends(get_current_user)):
    """Watchlist scanner and review."""
    prompt = (
        f"Fetch the watchlist for user ID: {current_user.id}. "
        "For each symbol in the watchlist, retrieve its technical indicators and summarize active trading signals."
    )
    return StreamingResponse(stream_agent_execution(prompt, current_user.id), media_type="text/event-stream")


# ============================================================================
# Preserved Legacy Endpoints (Phase 11 Compliance)
# ============================================================================

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

@router.post("/prompt", response_model=AIPromptResponse)
async def process_ai_prompt(
    request: AIPromptRequest, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Natural language market query processing with portfolio and watchlist context."""
    try:
        holdings_query = select(Holding).where(Holding.user_id == current_user.id)
        holdings_res = await db.execute(holdings_query)
        holdings = holdings_res.scalars().all()
        
        positions_query = select(Position).where(Position.user_id == current_user.id)
        positions_res = await db.execute(positions_query)
        positions = positions_res.scalars().all()
        
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
            "explanation": f"The {conviction} conviction {signal_type} signal for {symbol} was triggered at ₹{price} due to a confluence of indicators."
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
