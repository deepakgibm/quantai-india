from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
import google.generativeai as genai
import httpx
import json
from models import User
from config import settings
from sqlalchemy import desc, create_engine
from schemas import (
    AIPromptRequest, AIPromptResponse, AICommandRequest, AICommandResponse,
    ScannerResponse, MarketAnalysisResponse
)
from services.dragonfly_client import get_cache
from utils.auth import get_current_user, get_current_user
import logging

logger = logging.getLogger(__name__)

def get_cached_ai_data(strategy_id: str):
    """Get data from cache if valid."""
    cache = get_cache()
    if not cache.is_available():
        return None
    try:
        return cache.get(f"qai:ai:strategy:{strategy_id}")
    except Exception as e:
        logger.error(f"Cache get error for {strategy_id}: {e}")
        return None

def set_cached_ai_data(strategy_id: str, data: any):
    """Set data in cache with TTL."""
    cache = get_cache()
    if not cache.is_available():
        return
    try:
        cache.set(f"qai:ai:strategy:{strategy_id}", data, ttl=600)  # 10 min cache for performance
    except Exception as e:
        logger.error(f"Cache set error for {strategy_id}: {e}")

router = APIRouter()

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


def get_working_model():
    """
    Dynamically finds the best available 'flash' model 
    to prevent 404 errors.
    """
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name:
                    logger.info(f"✅ Found working Gemini model: {m.name}")
                    return m.name
    except Exception as e:
        logger.warning(f"Could not list Gemini models: {e}")
    
    # Default fallback
    return 'gemini-2.0-flash'

if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model_name = get_working_model()
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini AI: {e}")
        model = None
else:
    model = None


from services.live_price_enricher import get_live_ltp, enrich_scanner_results

async def _get_fallback_stocks_with_real_prices(stocks_template: list, access_token: str = None) -> list:
    """Update fallback stocks template with real prices from best available source"""
    # Batch enrichment is more efficient and now handles level calculations internally if missing
    return await enrich_scanner_results(stocks_template, access_token) or stocks_template


@router.post("/prompt", response_model=AIPromptResponse)
async def process_ai_prompt(request: AIPromptRequest, current_user: User = Depends(get_current_user)):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")
    
    try:
        enhanced_prompt = f"""You are a professional stock trading advisor for the Indian stock market (NSE Cash Segment only).

User Query: {request.prompt}

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
- entry_price should be slightly below current price for BUY (or above for SELL)
- target_price should reflect realistic profit target based on trend analysis
- stop_loss should be set at a logical support/resistance level
- risk_reward should be at least 1:1.5 or better
- Confidence should reflect how strong the signal is (80%+ for strong signals, 50-79% for moderate, below 50% for weak)
- Keep reasons concise and actionable
- Only respond with the JSON array, nothing else"""
        
        logger.info(f"Processing AI prompt: {request.prompt}")
        response = model.generate_content(enhanced_prompt)
        response_text = response.text.strip()
        logger.info(f"Got AI response, length: {len(response_text)}")
        
        suggested_stocks = []
        fallback_used = False
        
        # Clean up the response to extract JSON
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        try:
            # Attempt to parse the AI response as JSON
            parsed_response = json.loads(response_text)
            
            # Validate the structure of each recommendation and fetch LTP
            if isinstance(parsed_response, list):
                for stock_rec in parsed_response:
                    # Check for core required fields only
                    if not all(k in stock_rec for k in ["symbol", "action", "confidence", "reason"]):
                        print(f"Invalid stock recommendation structure from AI: {stock_rec}")
                        fallback_used = True
                        break # Break out of the loop if any recommendation is invalid
                    
                    # Fetch current price for the recommended stock
                    access_token = (current_user.upstox_access_token if current_user and getattr(current_user, "upstox_access_token", None) else None) or settings.UPSTOX_ACCESS_TOKEN
                    
                    price_result = await get_live_ltp(stock_rec["symbol"], access_token)
                    current_price = price_result.get("ltp")

                    if current_price and current_price > 0:
                        stock_rec["price"] = current_price
                        
                        # Calculate trade levels if not provided by AI
                        if not stock_rec.get("entry_price") or stock_rec.get("entry_price") == 0:
                            if stock_rec["action"] == "BUY":
                                stock_rec["entry_price"] = round(current_price * 0.995, 2)  # 0.5% below current
                            else:
                                stock_rec["entry_price"] = round(current_price * 1.005, 2)  # 0.5% above current
                        
                        if not stock_rec.get("target_price") or stock_rec.get("target_price") == 0:
                            if stock_rec["action"] == "BUY":
                                stock_rec["target_price"] = round(current_price * 1.03, 2)  # +3% target
                            else:
                                stock_rec["target_price"] = round(current_price * 0.97, 2)  # -3% target
                        
                        if not stock_rec.get("stop_loss") or stock_rec.get("stop_loss") == 0:
                            if stock_rec["action"] == "BUY":
                                stock_rec["stop_loss"] = round(current_price * 0.985, 2)  # -1.5% stop loss
                            else:
                                stock_rec["stop_loss"] = round(current_price * 1.015, 2)  # +1.5% stop loss
                        
                        if not stock_rec.get("risk_reward"):
                            stock_rec["risk_reward"] = "1:2"
                        
                        if not stock_rec.get("trade_type"):
                            stock_rec["trade_type"] = "Short-Term"
                    else:
                        print(f"Could not fetch price for {stock_rec['symbol']} from any source. Setting to 0.")
                        stock_rec["price"] = stock_rec.get("price", 0)
                    
                    suggested_stocks.append(stock_rec)
            else:
                print("AI response was not a JSON list. Using fallback.")
                fallback_used = True

        except json.JSONDecodeError:
            with open("debug_ai_error.log", "a") as f:
                f.write(f"JSON Decode Error. Response text: {response_text}\n")
            print("AI response was not valid JSON. Using fallback.")
            fallback_used = True
        except ValueError as ve:
            with open("debug_ai_error.log", "a") as f:
                f.write(f"Value Error: {ve}\n")
            print(f"AI response structure invalid: {ve}. Using fallback.")
            fallback_used = True
        except Exception as e:
            with open("debug_ai_error.log", "a") as f:
                f.write(f"General Error: {e}\n")
            print(f"Error processing AI response or fetching LTP: {e}. Using fallback.")
            fallback_used = True

        if fallback_used or not suggested_stocks:
            suggested_stocks = [
                {
                    "symbol": "RELIANCE",
                    "name": "Reliance Industries Ltd",
                    "action": "BUY",
                    "trade_type": "Short-Term",
                    "price": 1556.50,
                    "entry_price": 1550.00,
                    "target_price": 1610.00,
                    "stop_loss": 1520.00,
                    "risk_reward": "1:2",
                    "confidence": 75,
                    "reason": "AI response parsing failed. This is sample data. Please try again with a different query."
                }
            ]
        
        return {
            "response": response_text,
            "suggested_stocks": suggested_stocks,
            "strategy": {"type": "ai_generated", "confidence": "high"}
        }
    except Exception as e:
        logger.error(f"AI processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"AI service temporarily unavailable: {str(e)}")

@router.get("/market-analysis", response_model=MarketAnalysisResponse)
async def get_market_analysis(current_user: User = Depends(get_current_user)):
    """AI Market Analysis - Summarizes current market state using technicals + Gemini."""
    import asyncio
    import time
    import hashlib
    
    start_time = time.time()
    
    # 1. Check Cache FIRST (10 min TTL)
    cache_key = "market-analysis-daily"
    cached = get_cached_ai_data(cache_key)
    if cached:
        logger.info(f"market-analysis: Cache hit, returning in {(time.time()-start_time)*1000:.0f}ms")
        return cached
    
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")
    
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
    }
    """
    
    from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
    
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), retry=retry_if_exception_type(Exception))
    def fetch_analysis():
        generative_response = model.generate_content(prompt)
        text = generative_response.text
        # Extract JSON if Gemini wraps it in markdown backticks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    
    try:
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_analysis),
                timeout=12.0  # Increased timeout for complex prompt
            )
        except asyncio.TimeoutError:
            logger.warning(f"market-analysis: Gemini API timeout after 12s")
            return {
                "status": "timeout",
                "analysis": "Market analysis is taking longer than expected due to AI service load.",
                "sentiment": "NEUTRAL",
                "trend": "SIDEWAYS",
                "top_sectors": [],
                "stocks_to_watch": [],
                "timestamp": datetime.now().strftime("%Y-%m-%d"),
                "retry_after_seconds": 30
            }
        
        # Ensure timestamp is set if missing
        if "timestamp" not in result:
            result["timestamp"] = datetime.now().strftime("%Y-%m-%d")
        
        # Cache for 10 minutes (600s)
        cache = get_cache()
        if cache.is_available():
            try:
                cache.set(f"qai:ai:strategy:{cache_key}", result, ttl=600)
            except Exception:
                pass
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"market-analysis: Completed in {elapsed:.0f}ms")
        return result
        
    except Exception as e:
        logger.error(f"AI Market Analysis failed after retries: {e}")
        return {
            "status": "error",
            "analysis": "Market analysis temporarily unavailable due to high demand. Please consult the 'Trend Finder' or 'Momentum Scanner' for automated signals.",
            "sentiment": "NEUTRAL",
            "trend": "SIDEWAYS",
            "top_sectors": [],
            "stocks_to_watch": [],
            "timestamp": datetime.now().strftime("%Y-%m-%d")
        }

# Sentiment analysis consolidated below at /sentiment

@router.get("/trend-finder")
async def get_trend_finder_stocks(current_user: User = Depends(get_current_user)):
    """Identify stocks with strong trend continuation setups using technical analysis."""
    import asyncio
    import time
    from fastapi.responses import JSONResponse
    
    start_time = time.time()
    
    # 1. Check Cache
    cached = get_cached_ai_data("trend-finder")
    if cached:
        logger.info(f"trend-finder: Cache hit, returning in {(time.time()-start_time)*1000:.0f}ms")
        # Enrich cached stocks with live prices
        try:
            from services.live_price_enricher import enrich_scanner_results
            if isinstance(cached, dict) and "stocks" in cached and cached["stocks"]:
                access_token = settings.UPSTOX_ACCESS_TOKEN
                cached["stocks"] = await enrich_scanner_results(cached["stocks"], access_token)
        except Exception as e:
            logger.error(f"trend-finder: Failed to enrich cached results: {e}")
        return cached

    try:
        from services.trend_analyzer import TrendAnalyzer
        from services.live_price_enricher import enrich_scanner_results
        
        # Run in thread pool
        def run_scan():
            analyzer = TrendAnalyzer()
            return analyzer.scan_all(limit=10)
        
        loop = asyncio.get_event_loop()
        try:
            stocks = await asyncio.wait_for(
                loop.run_in_executor(None, run_scan),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            logger.warning("trend-finder: Timeout after 10s")
            return {
                "status": "timeout",
                "count": 0, "stocks": [], "scan_type": "trend_technical",
                "description": "Trend scan is taking too long. Please try again."
            }
        
        if stocks:
            access_token = settings.UPSTOX_ACCESS_TOKEN
            enriched_stocks = await enrich_scanner_results(stocks, access_token)
            
            response = {
                "status": "success",
                "count": len(enriched_stocks),
                "stocks": enriched_stocks,
                "scan_type": "trend_technical",
                "description": "Stocks identified using technical analysis with LIVE prices (EMA, RSI, ADX, Volume, Pullback)"
            }
            # 2. Update Cache
            set_cached_ai_data("trend-finder", response)
            return response
        else:
            # No stocks met criteria - return message
            return {
                "status": "success",
                "count": 0,
                "stocks": [],
                "scan_type": "trend_technical",
                "description": "No stocks currently meet the trend criteria (score >= 60). Market may be in consolidation."
            }
            
    except Exception as e:
        logger.error(f"Trend finder error: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "count": 0,
            "stocks": [],
            "scan_type": "trend_technical",
            "description": f"Trend finder temporarily unavailable: {str(e)[:100]}"
        }

@router.get("/breakout-detector", response_model=ScannerResponse)
async def get_breakout_stocks(current_user: User = Depends(get_current_user)):
    """Detect stocks with volume-backed breakouts using technical analysis."""
    import asyncio
    import time
    from fastapi.responses import JSONResponse
    
    start_time = time.time()
    
    # 1. Check Cache FIRST
    cached = get_cached_ai_data("breakout-detector")
    if cached:
        logger.info(f"breakout-detector: Cache hit, returning in {(time.time()-start_time)*1000:.0f}ms")
        # Enrich cached stocks with live prices
        try:
            from services.live_price_enricher import enrich_scanner_results
            if isinstance(cached, dict) and "stocks" in cached and cached["stocks"]:
                access_token = settings.UPSTOX_ACCESS_TOKEN
                cached["stocks"] = await enrich_scanner_results(cached["stocks"], access_token)
        except Exception as e:
            logger.error(f"breakout-detector: Failed to enrich cached results: {e}")
        return cached

    try:
        from services.breakout_detector import BreakoutDetector
        from services.live_price_enricher import enrich_scanner_results
        
        # Run blocking scan in thread pool with HARD TIMEOUT
        def run_scan():
            detector = BreakoutDetector()
            return detector.scan_all(limit=10)
        
        # Execute with 8 second timeout
        loop = asyncio.get_event_loop()
        try:
            stocks = await asyncio.wait_for(
                loop.run_in_executor(None, run_scan),
                timeout=8.0  # Hard timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"breakout-detector: Timeout after 8s")
            return JSONResponse(
                status_code=200,
                content={
                    "status": "timeout",
                    "count": 0,
                    "stocks": [],
                    "scan_type": "breakout_technical",
                    "description": "Breakout scan is taking too long. Please try again."
                }
            )
        
        if stocks:
            # Enrich with live prices from Upstox (Now BATCH optimized)
            access_token = settings.UPSTOX_ACCESS_TOKEN
            enriched_stocks = await enrich_scanner_results(stocks, access_token)
            
            response = {
                "status": "success",
                "count": len(enriched_stocks),
                "stocks": enriched_stocks,
                "scan_type": "breakout_technical",
                "description": "Breakout stocks with LIVE prices (52W High, Resistance, Volume)"
            }
            # 2. Update Cache
            set_cached_ai_data("breakout-detector", response)
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"breakout-detector: Completed in {elapsed:.0f}ms with {len(enriched_stocks)} stocks")
            return response
        else:
            return {
                "status": "success",
                "count": 0,
                "stocks": [],
                "scan_type": "breakout_technical",
                "description": "No breakout stocks currently meet the criteria (score >= 60)"
            }
            
    except Exception as e:
        logger.error(f"Breakout detector error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "count": 0,
                "stocks": [],
                "scan_type": "breakout_technical",
                "description": f"Breakout detector temporarily unavailable: {str(e)[:100]}"
            }
        )

# Route alias for backward compatibility (some clients use /breakout-stocks)
@router.get("/breakout-stocks")
async def get_breakout_stocks_alias(current_user: User = Depends(get_current_user)):
    """Alias for /breakout-detector - backward compatibility."""
    return await get_breakout_stocks(current_user)

@router.get("/top5-picks", response_model=ScannerResponse)
async def get_top5_picks(current_user: User = Depends(get_current_user)):
    """Get Top 10 Buy/Sell signals (5 BUY + 5 SELL) using technical analysis."""
    import asyncio
    import time
    
    start_time = time.time()
    
    # 1. Check Cache FIRST (fast path)
    # 1. Check Cache FIRST (fast path)
    cached = get_cached_ai_data("top5-picks")
    if cached:
        logger.info(f"top5-picks: Cache hit, returning in {(time.time()-start_time)*1000:.0f}ms")
        # Enrich cached stocks with live prices
        try:
            from services.live_price_enricher import enrich_scanner_results
            access_token = settings.UPSTOX_ACCESS_TOKEN
            
            enrich_coroutines = []
            if isinstance(cached, dict):
                # Enrich 'stocks' list if present
                if "stocks" in cached and cached["stocks"]:
                    enrich_coroutines.append(enrich_scanner_results(cached["stocks"], access_token))
                
                # Enrich buy/sell signal lists
                if "buy_signals" in cached and cached["buy_signals"]:
                    enrich_coroutines.append(enrich_scanner_results(cached["buy_signals"], access_token))
                
                if "sell_signals" in cached and cached["sell_signals"]:
                    enrich_coroutines.append(enrich_scanner_results(cached["sell_signals"], access_token))
                
                if enrich_coroutines:
                    results = await asyncio.gather(*enrich_coroutines)
                    # Results assignment logic
                    res_idx = 0
                    if "stocks" in cached and cached["stocks"]:
                        cached["stocks"] = results[res_idx]
                        res_idx += 1
                    if "buy_signals" in cached and cached["buy_signals"]:
                        cached["buy_signals"] = results[res_idx]
                        res_idx += 1
                    if "sell_signals" in cached and cached["sell_signals"]:
                        cached["sell_signals"] = results[res_idx]
        except Exception as e:
            logger.error(f"top5-picks: Failed to enrich cached results: {e}")
        return cached

    try:
        from services.top5_buysell import Top5BuySellEngine
        from services.live_price_enricher import enrich_scanner_results
        
        # Run blocking scan in thread pool with HARD TIMEOUT
        def run_scan():
            engine = Top5BuySellEngine()
            return engine.scan_all(limit=5)
        
        # Execute with 8 second timeout
        loop = asyncio.get_event_loop()
        try:
            signals = await asyncio.wait_for(
                loop.run_in_executor(None, run_scan),
                timeout=8.0  # Hard timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"top5-picks: Scan timeout after 8s")
            return {
                "status": "error",
                "error_code": "TIMEOUT",
                "message": "Scan took too long, please try again",
                "count": 0, "stocks": [], "buy_signals": [], "sell_signals": [],
                "scan_type": "top10_technical"
            }
        
        # Parallel price enrichment for buy and sell signals
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_buy, enriched_sell = await asyncio.gather(
            enrich_scanner_results(signals.get("buy", []), access_token),
            enrich_scanner_results(signals.get("sell", []), access_token)
        )
        all_stocks = enriched_buy + enriched_sell
        
        response = {
            "status": "success",
            "count": len(all_stocks),
            "stocks": all_stocks,
            "buy_signals": enriched_buy,
            "sell_signals": enriched_sell,
            "scan_type": "top10_technical",
            "description": "Top 10 Buy/Sell signals with LIVE prices (EMA, RSI, MACD, Volume)"
        }
        
        # Cache for 5 minutes
        set_cached_ai_data("top5-picks", response)
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"top5-picks: Completed in {elapsed:.0f}ms")
        if elapsed > 3000:
            logger.warning(f"top5-picks: SLOW - took {elapsed:.0f}ms")
        
        return response
            
    except Exception as e:
        logger.error(f"Top 5 picks error: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "count": 0,
            "stocks": [],
            "buy_signals": [],
            "sell_signals": [],
            "scan_type": "top10_technical",
            "description": "Top picks engine temporarily unavailable. Please try again."
        }

# Keep legacy endpoint for backwards compatibility
@router.get("/top3-picks")
async def get_top3_picks(current_user: User = Depends(get_current_user)):
    """Legacy endpoint - redirects to top5-picks"""
    return await get_top5_picks(current_user)

@router.get("/momentum-scanner", response_model=ScannerResponse)
async def get_momentum_stocks(current_user: User = Depends(get_current_user)):
    """Momentum Scanner - ROC and MFI based with LIVE prices."""
    import asyncio
    import time
    
    start_time = time.time()
    
    # 1. Check Cache
    # 1. Check Cache
    cached = get_cached_ai_data("momentum-scanner")
    if cached:
        logger.info(f"momentum-scanner: Cache hit, returning in {(time.time()-start_time)*1000:.0f}ms")
        # Enrich cached stocks with live prices
        try:
            from services.live_price_enricher import enrich_scanner_results
            if isinstance(cached, dict) and "stocks" in cached and cached["stocks"]:
                access_token = settings.UPSTOX_ACCESS_TOKEN
                cached["stocks"] = await enrich_scanner_results(cached["stocks"], access_token)
        except Exception as e:
            logger.error(f"momentum-scanner: Failed to enrich cached results: {e}")
        return cached

    try:
        from services.momentum_scanner import MomentumScanner
        from services.live_price_enricher import enrich_scanner_results
        
        def run_scan():
            scanner = MomentumScanner()
            return scanner.scan_all(limit=10)
            
        loop = asyncio.get_event_loop()
        try:
            stocks = await asyncio.wait_for(
                loop.run_in_executor(None, run_scan),
                timeout=12.0
            )
        except asyncio.TimeoutError:
            logger.warning("momentum-scanner: Timeout after 12s")
            return {
                "status": "timeout",
                "count": 0, "stocks": [], "scan_type": "momentum",
                "description": "Momentum scan is taking too long. Please try again."
            }
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = await enrich_scanner_results(stocks, access_token)
        
        response = {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "momentum", "description": "Stocks with strong price momentum (LIVE prices)"}
        # 2. Update Cache
        set_cached_ai_data("momentum-scanner", response)
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"momentum-scanner: Completed in {elapsed:.0f}ms")
        return response
    except Exception as e:
        logger.error(f"Momentum scanner error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "momentum", "description": str(e)}

@router.get("/mean-reversion", response_model=ScannerResponse)
async def get_mean_reversion_stocks(current_user: User = Depends(get_current_user)):
    """Mean Reversion Scanner with LIVE prices."""
    import asyncio
    import time
    
    start_time = time.time()
    
    # 1. Check Cache
    # 1. Check Cache
    cached = get_cached_ai_data("mean-reversion")
    if cached:
        logger.info(f"mean-reversion: Cache hit, returning in {(time.time()-start_time)*1000:.0f}ms")
        # Enrich cached stocks with live prices
        try:
            from services.live_price_enricher import enrich_scanner_results
            if isinstance(cached, dict) and "stocks" in cached and cached["stocks"]:
                access_token = settings.UPSTOX_ACCESS_TOKEN
                cached["stocks"] = await enrich_scanner_results(cached["stocks"], access_token)
        except Exception as e:
            logger.error(f"mean-reversion: Failed to enrich cached results: {e}")
        return cached

    try:
        from services.mean_reversion_scanner import MeanReversionScanner
        from services.live_price_enricher import enrich_scanner_results
        
        def run_scan():
            scanner = MeanReversionScanner()
            return scanner.scan_all(limit=10)
            
        loop = asyncio.get_event_loop()
        try:
            stocks = await asyncio.wait_for(
                loop.run_in_executor(None, run_scan),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "count": 0, "stocks": [], "scan_type": "mean_reversion",
                "description": "Scan timed out. Please try again."
            }
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = await enrich_scanner_results(stocks, access_token)
        
        response = {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "mean_reversion", "description": "Oversold/overbought stocks with LIVE prices"}
        # 2. Update Cache
        set_cached_ai_data("mean-reversion", response)
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"mean-reversion: Completed in {elapsed:.0f}ms")
        return response
    except Exception as e:
        logger.error(f"Mean reversion error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "mean_reversion", "description": str(e)}

@router.get("/gap-scanner", response_model=ScannerResponse)
async def get_gap_stocks(current_user: User = Depends(get_current_user)):
    """Gap Scanner - Overnight gap detection with LIVE prices."""
    import asyncio
    import time
    start_time = time.time()
    
    try:
        from services.gap_scanner import GapScanner
        from services.live_price_enricher import enrich_scanner_results
        
        def run_scan():
            scanner = GapScanner()
            return scanner.scan_all(limit=10)
        
        loop = asyncio.get_event_loop()
        try:
            stocks = await asyncio.wait_for(
                loop.run_in_executor(None, run_scan),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            return {
                "status": "timeout", "count": 0, "stocks": [], 
                "scan_type": "gap", "description": "Gap scan timed out."
            }
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = await enrich_scanner_results(stocks, access_token)
        
        return {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "gap", "description": "Gap stocks with LIVE prices"}
    except Exception as e:
        logger.error(f"Gap scanner error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "gap", "description": str(e)}

@router.get("/relative-strength", response_model=ScannerResponse)
async def get_relative_strength_stocks(current_user: User = Depends(get_current_user)):
    """Relative Strength Scanner - Market outperformers with LIVE prices."""
    import asyncio
    import time
    start_time = time.time()
    
    try:
        from services.relative_strength_scanner import RelativeStrengthScanner
        from services.live_price_enricher import enrich_scanner_results
        
        def run_scan():
            scanner = RelativeStrengthScanner()
            return scanner.scan_all(limit=10)
        
        loop = asyncio.get_event_loop()
        try:
            stocks = await asyncio.wait_for(
                loop.run_in_executor(None, run_scan),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            return {
                "status": "timeout", "count": 0, "stocks": [], 
                "scan_type": "relative_strength", "description": "Scan timed out."
            }
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = await enrich_scanner_results(stocks, access_token)
        
        return {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "relative_strength", "description": "Market outperformers with LIVE prices"}
    except Exception as e:
        logger.error(f"Relative strength error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "relative_strength", "description": str(e)}

@router.get("/vwap-scanner", response_model=ScannerResponse)
async def get_vwap_stocks(current_user: User = Depends(get_current_user)):
    """VWAP Scanner - Volume weighted average price trading with LIVE prices."""
    import asyncio
    import time
    start_time = time.time()
    
    try:
        from services.vwap_scanner import VWAPScanner
        from services.live_price_enricher import enrich_scanner_results
        
        def run_scan():
            scanner = VWAPScanner()
            return scanner.scan_all(limit=10)
            
        loop = asyncio.get_event_loop()
        try:
            stocks = await asyncio.wait_for(
                loop.run_in_executor(None, run_scan),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            return {
                "status": "timeout", "count": 0, "stocks": [], 
                "scan_type": "vwap", "description": "Scan timed out."
            }
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = await enrich_scanner_results(stocks, access_token)
        
        return {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "vwap", "description": "VWAP trading signals with LIVE prices"}
    except Exception as e:
        logger.error(f"VWAP scanner error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "vwap", "description": str(e)}

@router.get("/sr-bounce", response_model=ScannerResponse)
async def get_sr_bounce_stocks(current_user: User = Depends(get_current_user)):
    """Support/Resistance Bounce Scanner with LIVE prices."""
    import asyncio
    import time
    start_time = time.time()
    
    try:
        from services.sr_bounce_scanner import SRBounceScanner
        from services.live_price_enricher import enrich_scanner_results
        
        def run_scan():
            scanner = SRBounceScanner()
            return scanner.scan_all(limit=10)
            
        loop = asyncio.get_event_loop()
        try:
            stocks = await asyncio.wait_for(
                loop.run_in_executor(None, run_scan),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            return {
                "status": "timeout", "count": 0, "stocks": [], 
                "scan_type": "sr_bounce", "description": "Scan timed out."
            }
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = await enrich_scanner_results(stocks, access_token)
        
        return {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "sr_bounce", "description": "Stocks bouncing off support/resistance levels with LIVE prices"}
    except Exception as e:
        logger.error(f"S/R bounce error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "sr_bounce", "description": str(e)}

@router.post("/command", response_model=AICommandResponse)
async def process_command(request: AICommandRequest, current_user: User = Depends(get_current_user)):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        prompt = f"""
        Convert the following natural language command into a JSON action object.
        User Command: "{request.command}"
        
        Supported Actions:
        - start_intraday_bot (params: capital, max_positions, strategy)
        - stop_bot
        - scan_market (params: index e.g. "Nifty 200")
        - backtest (params: strategy, period, capital)
        - update_risk_settings (params: max_loss, max_position_size)
        - fetch_trending_stocks
        
        Output JSON ONLY. Example: {{"action": "start_intraday_bot", "capital": 100000, "strategy": "trend"}}
        """
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean JSON
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        action_data = json.loads(response_text)
        action = action_data.get("action", "unknown")
        
        return {
            "action": action,
            "params": action_data,
            "message": f"Command parsed: {action}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Command processing failed: {str(e)}")


@router.get("/sentiment")
async def get_ai_sentiment(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """
    Secure AI sentiment proxy endpoint.
    
    This keeps the Gemini API key server-side and prevents frontend exposure.
    The frontend should call this endpoint instead of directly using
    the Google AI SDK.
    
    Returns:
        JSON with sentiment (BULLISH/BEARISH/NEUTRAL), ltp, and summary
    """
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="AI service not configured")
    
    try:
        prompt = f"""
        Task: Analyze current market sentiment for {symbol} (Indian Stock Market, NSE).
        
        Based on recent market trends, news, and technical indicators:
        1. Determine the overall sentiment
        2. Provide a brief market outlook
        
        Respond ONLY with a valid JSON object:
        {{
            "sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
            "ltp": estimated_current_price_number,
            "summary": "Brief 1-2 sentence market outlook for this stock"
        }}
        """
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean JSON
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback parsing
            result = {
                "sentiment": "NEUTRAL",
                "ltp": None,
                "summary": "Unable to parse AI response. Please try again."
            }
        
        # Try to get real price if AI didn't provide one
        if not result.get("ltp"):
            price_data = await get_live_ltp(symbol, settings.UPSTOX_ACCESS_TOKEN)
            price = price_data.get("ltp")
            if price:
                result["ltp"] = round(price, 2)
        
        return {
            "symbol": symbol,
            "sentiment": result.get("sentiment", "NEUTRAL"),
            "ltp": result.get("ltp"),
            "summary": result.get("summary", "Market data retrieved."),
            "source": "gemini-ai"
        }
        
    except Exception as e:
        logger.error(f"AI sentiment error for {symbol}: {e}")
        
        # Fallback with real price
        price_data = await get_live_ltp(symbol, settings.UPSTOX_ACCESS_TOKEN)
        price = price_data.get("ltp")
        
        return {
            "symbol": symbol,
            "sentiment": "NEUTRAL",
            "ltp": round(price, 2) if price else None,
            "summary": "AI service temporarily unavailable. Showing current market price.",
            "source": "fallback"
        }

# ============================================
# Alias Routes for API Consistency
# ============================================

@router.get("/momentum", response_model=ScannerResponse)
async def get_momentum_alias(current_user: User = Depends(get_current_user)):
    """Alias for /momentum-scanner for API consistency."""
    return await get_momentum_stocks(current_user)

@router.get("/vwap", response_model=ScannerResponse)
async def get_vwap_alias(current_user: User = Depends(get_current_user)):
    """Alias for /vwap-scanner for API consistency."""
    return await get_vwap_stocks(current_user)


