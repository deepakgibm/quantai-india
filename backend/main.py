from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import traceback
import logging
from datetime import datetime

# Configure structured logging (replaces basic logging)
try:
    from core.observability.logging import configure_logging, get_logger
    from core.observability.middleware import setup_observability_middleware
    from core.observability.metrics import get_metrics
    from core.observability.correlation import get_correlation_id
    configure_logging()
    logger = get_logger(__name__)
    _observability_available = True
except ImportError as e:
    # Fallback to basic logging if observability module not available
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    _observability_available = False
    print(f"Observability module not available: {e}")

from routers import auth, upstox, trading, ai, orders, risk, settings, algorithms, agentic_bot, engine_performance, quant_bot, scanner, market, metrics
from api.v1.endpoints import walk_forward_backtest  # Walk-Forward Backtest
# from api.v1.endpoints import experiment_lab  # MOVED TO /review - Strategy Experiment Lab (Beta)
from api.v1.endpoints import backtest_strategies  # Enhanced Strategy API with Tiers
from routers import heatmap  # Sector Heatmap
from workers.heatmap_workers import PriceIngestionWorker, SectorAggregationWorker
from workers.yearly_breakout_worker import YearlyBreakoutWorker
from database import init_db
from services.upstox_ws_manager import get_upstox_ws_manager

# NIFTY 100 Real-Time Ranking Service
try:
    from services.nifty100_ranking_service import start_nifty100_ranking_service, stop_nifty100_ranking_service
    _nifty100_service_available = True
except ImportError as e:
    logger.warning(f"NIFTY 100 Ranking Service not available: {e}")
    start_nifty100_ranking_service = None
    stop_nifty100_ranking_service = None
    _nifty100_service_available = False

# High-Performance Scanner v2 (Phase 2-6 Refactor)
try:
    from engine.scanner_api import router as scanner_v2_router
    from engine.scanner_service import start_scanner_service
    _hp_scanner_available = True
except ImportError as e:
    logger.warning(f"High-performance scanner not available: {e}")
    scanner_v2_router = None
    start_scanner_service = None
    _hp_scanner_available = False

# High-Performance Scanner v3 (Memcached-backed, <50ms)
try:
    from routers.hp_scanner_api import router as scanner_v3_router
    from services.hp_scanner_service import start_hp_scanner
    _hp_scanner_v3_available = True
except ImportError as e:
    logger.warning(f"HP Scanner v3 not available: {e}")
    scanner_v3_router = None
    start_hp_scanner = None
    _hp_scanner_v3_available = False

# Optional: Real-time scanner engine (may fail due to optional dependencies)
try:
    from core.scanner.realtime_scanner_engine import get_realtime_scanner_engine
    _realtime_scanner_available = True
except ImportError as e:
    logger.warning(f"Real-time scanner not available: {e}")
    get_realtime_scanner_engine = None
    _realtime_scanner_available = False

app = FastAPI(
    title="QuantAI India Trading Bot API",
    description="AI-Powered Trading Bot with Upstox Integration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add observability middleware (correlation IDs, structured logging, metrics)
if _observability_available:
    setup_observability_middleware(app)
    logger.info("Observability middleware configured")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from utils.error_responses import generic_exception_handler
    return await generic_exception_handler(request, exc)

# Register standardized validation error handler
from fastapi.exceptions import RequestValidationError
from utils.error_responses import validation_exception_handler, http_exception_handler, api_error_handler, APIError

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    return await validation_exception_handler(request, exc)

@app.exception_handler(APIError)
async def custom_api_error_handler(request: Request, exc: APIError):
    return await api_error_handler(request, exc)

@app.on_event("startup")
async def startup_event():
    import asyncio
    
    # Initialize database with timeout
    # try:
    #     await asyncio.wait_for(init_db(), timeout=10.0)
    #     print("Database initialized")
    # except asyncio.TimeoutError:
    #     print("Database init timed out - will retry on first request")
    # except Exception as e:
    #     print(f"Database init error: {e}")
    
    # Initialize Real-time services in background (don't block startup)
    async def init_realtime():
        try:
            get_upstox_ws_manager()
            if _realtime_scanner_available and get_realtime_scanner_engine:
                engine = get_realtime_scanner_engine()
                await asyncio.wait_for(engine.initialize(), timeout=30.0)
                logger.info("Real-time Scanner Engine initialized")
            else:
                logger.warning("Real-time Scanner Engine not available - skipping")
        except asyncio.TimeoutError:
            logger.error("Real-time services initialization timed out")
        except Exception as e:
            logger.error(f"Real-time services initialization skipped: {e}")
    
    asyncio.create_task(init_realtime())
    
    # Initialize NIFTY 100 Ranking Service (WebSocket/REST with smart caching)
    if _nifty100_service_available and start_nifty100_ranking_service:
        async def init_nifty100():
            try:
                await start_nifty100_ranking_service()
                logger.info("NIFTY 100 Ranking Service started (mode: auto-detected)")
            except Exception as e:
                logger.error(f"NIFTY 100 Ranking Service start failed: {e}")
        asyncio.create_task(init_nifty100())

    
    # NOTE: HP Scanner v2/v3 services are now run as SEPARATE PROCESS
    # Run: python hp_scanner_worker.py
    # This prevents GIL contention and achieves <50ms API latency
    
    # Disabled: HP Scanner v2 in-process (causes blocking)
    # if _hp_scanner_available and start_scanner_service:
    #     async def init_hp_scanner():
    #         try:
    #             await start_scanner_service()
    #             print("High-Performance Scanner v2 Service started")
    #         except Exception as e:
    #             print(f"HP Scanner v2 service start failed: {e}")
    #     asyncio.create_task(init_hp_scanner())
    
    # Enabled: HP Scanner v3 in-process (fallback for no Redis)
    if _hp_scanner_v3_available and start_hp_scanner:
        async def init_hp_scanner_v3():
            try:
                await start_hp_scanner()
                logger.info("High-Performance Scanner v3 Service started (Memcached/In-Memory)")
            except Exception as e:
                logger.error(f"HP Scanner v3 service start failed: {e}")
        asyncio.create_task(init_hp_scanner_v3())
    
    # Heatmap Workers (Sector + Price)
    try:
        price_worker = PriceIngestionWorker()
        sector_worker = SectorAggregationWorker()
        
        asyncio.create_task(price_worker.start())
        asyncio.create_task(sector_worker.start())
        
        # Yearly Breakout Worker
        breakout_worker = YearlyBreakoutWorker(interval_seconds=3600)  # Hourly
        asyncio.create_task(breakout_worker.start())
        
        logger.info("Heatmap Workers (Price + Aggregation) and Breakout Worker started")
        
        # PRODUCTION MODE: No demo data seeding. Workers must populate cache from real sources.
        # If cache is empty, UI will show "Data unavailable" - never fake numbers.
            
    except Exception as e:
        logger.error(f"Heatmap workers failed to start: {e}")

    # AI Signal Warmup - Pre-compute signals on startup to eliminate cold-start
    async def warmup_ai_signals():
        """Pre-compute AI signals and cache them on startup."""
        import time
        try:
            await asyncio.sleep(10)  # Wait for DB connections to stabilize
            
            logger.info("?? AI Signal Warmup: Starting pre-computation...")
            start = time.time()
            
            # Pre-compute top5-picks
            from services.top5_buysell import Top5BuySellEngine
            from services.dragonfly_client import get_cache
            
            engine = Top5BuySellEngine()
            signals = engine.scan_all(limit=5)
            
            # Cache the results for 5 minutes
            cache = get_cache()
            if cache.is_available():
                response = {
                    "status": "success",
                    "count": len(signals.get("buy", [])) + len(signals.get("sell", [])),
                    "stocks": signals.get("buy", []) + signals.get("sell", []),
                    "buy_signals": signals.get("buy", []),
                    "sell_signals": signals.get("sell", []),
                    "scan_type": "top10_technical",
                    "description": "Top 10 Buy/Sell signals with LIVE prices (EMA, RSI, MACD, Volume)"
                }
                cache.set("qai:ai:strategy:top5-picks", response, ttl=300)
                logger.info(f"? AI Signal Warmup: Cached {len(response['stocks'])} signals")
            
            elapsed = time.time() - start
            logger.info(f"?? AI Signal Warmup: Completed in {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"AI Signal Warmup failed (non-blocking): {e}")
    
    asyncio.create_task(warmup_ai_signals())

    # Metadata Cache Warmup - Pre-populate symbol and strategy data
    async def warmup_metadata_cache():
        """Pre-populate symbol and strategy metadata cache."""
        try:
            await asyncio.sleep(5)  # Wait for cache connection
            from services.metadata_cache_service import get_metadata_cache_service
            service = get_metadata_cache_service()
            result = service.warm_cache()
            logger.info(f"?? Metadata Cache Warmup: {result}")
        except Exception as e:
            logger.error(f"Metadata Cache Warmup failed (non-blocking): {e}")
    
    asyncio.create_task(warmup_metadata_cache())

    logger.info("Server startup complete - API reads from cache only")
    logger.info("NOTE: Run 'python hp_scanner_worker.py' separately for cache population")


app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
print("DEBUG: Mounting Heatmap Router in MAIN")
app.include_router(heatmap.router, prefix="/api/heatmap", tags=["Heatmap"])
app.include_router(upstox.router, prefix="/api/upstox", tags=["Upstox"])
app.include_router(trading.router, prefix="/api/trading", tags=["Trading"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(algorithms.router, prefix="/api/algorithms", tags=["Algorithms"])
app.include_router(agentic_bot.router, prefix="/api/agentic-bot", tags=["Agentic Bot"])
app.include_router(engine_performance.router, prefix="/api/engines", tags=["Engine Performance"])
app.include_router(quant_bot.router, prefix="/api/quant", tags=["Quant Bot"])
app.include_router(scanner.router)  # Scanner router (already has full prefix)
app.include_router(market.router, prefix="/api/market", tags=["Market"])
app.include_router(metrics.router)  # Metrics & Metadata API (already has prefix)
app.include_router(walk_forward_backtest.router)  # Walk-Forward Backtest (already has full prefix)

# Experiment Lab (Beta) - Re-enabled for testing
try:
    from api.v1.endpoints import experiment_lab
    app.include_router(experiment_lab.router)  # Already has prefix /api/v1/experiment-lab
    logger.info("Registered Experiment Lab API at /api/v1/experiment-lab")
except ImportError as e:
    logger.warning(f"Experiment Lab router not loaded: {e}")

# ETL Status API
try:
    from api.v1.endpoints import etl_status
    app.include_router(etl_status.router, prefix="/api/v1", tags=["ETL"])
    logger.info("Registered ETL Status API at /api/v1/etl")
except ImportError as e:
    logger.warning(f"ETL Status router not loaded: {e}")

app.include_router(backtest_strategies.router, prefix="/api/v1/backtest", tags=["Backtest Strategies"])  # Enhanced Strategy API

# ML Forecast API (Adaptive Price Forecast)
try:
    from api.v1.endpoints import ml_forecast
    app.include_router(ml_forecast.router)  # Already has prefix /api/v1/ml
    logger.info("Registered ML Forecast API at /api/v1/ml")
except ImportError as e:
    logger.warning(f"ML Forecast router not loaded: {e}")

# High-Performance Scanner v2 API (Phase 8: snapshot-driven, <50ms response)
if _hp_scanner_available and scanner_v2_router:
    app.include_router(scanner_v2_router)
    logger.info("Registered High-Performance Scanner v2 API at /api/v2/scanner")

# High-Performance Scanner v3 API (Memcached-backed, <50ms P95)
if _hp_scanner_v3_available and scanner_v3_router:
    app.include_router(scanner_v3_router)
    logger.info("Registered High-Performance Scanner v3 API at /api/v3/scanner")

# Phase 3: Analytics and Archive endpoints
try:
    from routers import analytics
    app.include_router(analytics.router)  # Analytics router (already has full prefix)
except ImportError as e:
    logger.warning(f"Analytics router not loaded: {e}")

@app.get("/")
async def root():
    return {"message": "QuantAI India Trading Bot API", "status": "running"}

@app.get("/health")
async def health_check():
    """
    Comprehensive health check - checks all dependencies.
    Returns 200 if all dependencies are healthy, 503 otherwise.
    """
    import time
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check DragonflyDB/Redis with latency
    try:
        from services.dragonfly_client import get_cache
        start = time.perf_counter()
        cache = get_cache()
        if cache.is_available():
            # Test ping
            cache.get("health_ping")
            latency = (time.perf_counter() - start) * 1000
            health["checks"]["dragonfly"] = {
                "status": "healthy", 
                "backend": "dragonfly",
                "latency_ms": round(latency, 2)
            }
        else:
            health["checks"]["dragonfly"] = {"status": "unhealthy", "error": "Not connected"}
            health["status"] = "degraded"
    except Exception as e:
        health["checks"]["dragonfly"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Check Database (PostgreSQL) with latency
    try:
        from database import AsyncSessionLocal
        start = time.perf_counter()
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            latency = (time.perf_counter() - start) * 1000
            health["checks"]["database"] = {
                "status": "healthy", 
                "backend": "postgresql",
                "latency_ms": round(latency, 2)
            }
    except Exception as e:
        health["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check Upstox API (via Circuit Breaker)
    try:
        from utils.circuit_breaker import UPSTOX_CIRCUIT_BREAKER
        health["checks"]["upstox_api"] = {
            "status": "healthy" if UPSTOX_CIRCUIT_BREAKER.state == "closed" else "degraded",
            "circuit": UPSTOX_CIRCUIT_BREAKER.state,
            "failures": UPSTOX_CIRCUIT_BREAKER.get_stats().get("failed_calls", 0)
        }
    except Exception:
        health["checks"]["upstox_api"] = {"status": "unknown"}

    # Check Gemini AI (via Circuit Breaker)
    try:
        from utils.circuit_breaker import GEMINI_CIRCUIT_BREAKER
        health["checks"]["gemini_api"] = {
            "status": "healthy" if GEMINI_CIRCUIT_BREAKER.state == "closed" else "degraded",
            "circuit": GEMINI_CIRCUIT_BREAKER.state
        }
    except Exception:
        health["checks"]["gemini_api"] = {"status": "unknown"}
    
    # Return 503 if any critical dependency is down
    from fastapi.responses import JSONResponse
    if health["status"] != "healthy":
        return JSONResponse(status_code=503, content=health)
    
    return health

@app.get("/ready")
async def readiness_check():
    """
    Readiness check for load balancers.
    Returns 200 only if backend is ready to accept traffic.
    """
    try:
        from services.dragonfly_client import get_cache
        cache = get_cache()
        if not cache.is_available():
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503, 
                content={"status": "not_ready", "detail": "Cache unavailable", "timestamp": datetime.now().isoformat()}
            )
    except Exception:
        pass
        
    return {"status": "ready", "timestamp": datetime.now().isoformat()}


@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.
    Exposes application metrics for scraping.
    """
    if _observability_available:
        metrics = get_metrics()
        return Response(
            content=metrics.get_metrics_output(),
            media_type=metrics.get_content_type()
        )
    return Response(content=b"# observability not available\n", media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


