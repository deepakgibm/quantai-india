from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from datetime import datetime

# 1. Logging Configuration
# 1. Observability Configuration
from core.observability.logging import configure_logging, get_logger
from core.observability.middleware import setup_observability_middleware

configure_logging()
logger = get_logger(__name__)
_observability_available = True

# 2. Main Application Instance
app = FastAPI(
    title="QuantAI India",
    description="AI-Powered Professional Trading & Analytics Platform",
    version="2.0.0"
)

# 2.5 Ensure Models are Registered


# 3. CORS Configuration (env-driven, not hardcoded wildcard)
from config import settings as app_settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3.5 Secure Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' ws: wss:;"
    )
    return response

if _observability_available:
    setup_observability_middleware(app)

# 4. Exception Handlers
from utils.error_responses import (
    generic_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    api_error_handler,
    APIError
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return await generic_exception_handler(request, exc)

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request, exc):
    return await validation_exception_handler(request, exc)

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    return await http_exception_handler(request, exc)

@app.exception_handler(APIError)
async def custom_api_error_handler(request, exc):
    return await api_error_handler(request, exc)

# 5. Router Imports (Unified Layer)
from api.auth import router as auth_router
from api.ai import router as ai_router
from api.scanners import router as scanner_router
from api.market_data import router as market_router
from api.indicators import router as indicator_router
from api.health import router as health_router
from api.trading import router as trading_router
from api.analytics import router as analytics_router
from api.upstox import router as upstox_router
from api.engines import router as engine_router
from api.bot import router as bot_router
from engine.scanner_api import router as scanner_v3_router
from screener.api.screener_router import router as screener_router
from api.websockets import market_ws_router
from api.search import router as search_router
from api.volatility import router as volatility_router
from api.option_flow import router as option_flow_router
from api.heatmap import router as heatmap_router
from api.sector_analysis import router as sector_analysis_router
from api.volume_profile import router as volume_profile_router
from api.saas_router import router as saas_router
from api.watchlist import router as watchlist_router
from api.metrics import router as metrics_router
from api.system import router as system_router
from api.v1.quant_workspace import router as quant_workspace_router
from api.algorithms import router as algorithms_router
from api.orders import router as orders_router
from api.risk import router as risk_router
from api.settings import router as settings_router


# 6. Unified API Registration (Flattened for Reliability)
app.include_router(health_router, prefix="/api/health", tags=["Health"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(market_router, prefix="/api/market", tags=["Market Data"])
app.include_router(indicator_router, prefix="/api/indicators", tags=["Technical Indicators"])
app.include_router(scanner_router, prefix="/api/scanner", tags=["Standard Scanners"])
app.include_router(trading_router, prefix="/api/trading", tags=["Trading Operations"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Performance Analytics"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI Engine"])
app.include_router(quant_workspace_router, prefix="/api/quant", tags=["Quant Workspace"])
app.include_router(upstox_router, prefix="/api/upstox", tags=["Upstox Broker"])
app.include_router(engine_router, prefix="/api/engines", tags=["Engine Management"])
app.include_router(bot_router, prefix="/api/bot", tags=["Signal Bot"])
app.include_router(screener_router, prefix="/api/screener", tags=["Trade Screener"])
app.include_router(scanner_v3_router, prefix="/api/scanners/v3", tags=["HP Scanner V3 (Phase 1)"])
app.include_router(market_ws_router, prefix="/api/ws", tags=["Market WebSockets"])
app.include_router(search_router, prefix="/api/search", tags=["Search"])
app.include_router(volatility_router, prefix="/api/volatility", tags=["Volatility"])
app.include_router(option_flow_router, prefix="/api/option-flow", tags=["Option Flow"])
app.include_router(heatmap_router, prefix="/api/heatmap", tags=["Heatmap"])
app.include_router(sector_analysis_router, prefix="/api/sector-analysis", tags=["Sector Analysis"])
app.include_router(volume_profile_router, prefix="/api/volume-profile", tags=["Volume Profile"])
app.include_router(saas_router, prefix="/api/saas", tags=["SaaS Enterprise"])
app.include_router(watchlist_router, prefix="/api/watchlist", tags=["Watchlist"])
app.include_router(metrics_router, prefix="/api/metrics", tags=["Metrics & Metadata"])
app.include_router(system_router, prefix="/api/system", tags=["System Diagnostics"])
app.include_router(algorithms_router, prefix="/api/algorithms", tags=["Algorithms"])
app.include_router(orders_router, prefix="/api/orders", tags=["Orders"])
app.include_router(risk_router, prefix="/api/risk", tags=["Risk Settings"])
app.include_router(settings_router, prefix="/api/settings", tags=["User Settings"])


from api.v1 import router as v1_router
app.include_router(v1_router, prefix="/api/v1")


logger.info("?? QuantAI Production API v2.0 Registered at Root.")

# 7. Lifecycle Events
@app.on_event("startup")
async def startup_event():
    logger.info("?? QuantAI Backend Starting Up...")
    
    # 1. Enforce critical database health audit (Ping, Read, Write, Transaction) on startup.
    try:
        from database import init_db, verify_database_health
        await verify_database_health()
        await init_db()
        logger.info("?? Database schema verified/created.")
        
        # Warm instrument resolver cache in a background executor
        from services.instrument_resolver import warm_cache
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, warm_cache, 2000)
        logger.info("⚡ Instrument resolver cache pre-warmed.")
    except Exception as e:
        logger.critical(f"FATAL DATABASE ERROR DURING STARTUP: {e}", exc_info=True)
        import sys
        sys.exit(1)
        
    try:
        from config import settings
        
        # Initialize Core Services
        from services.market_data_orchestrator import get_market_data_orchestrator
        orchestrator = get_market_data_orchestrator()
        asyncio.create_task(orchestrator.start())
        
        # Non-critical engines in background tasks
        from services.nifty100_ranking_service import start_nifty100_ranking_service
        asyncio.create_task(start_nifty100_ranking_service())

        from services.sector_service import start_sector_service
        asyncio.create_task(start_sector_service())
        
        from services.realtime_yearly_breakout_engine import start_realtime_breakout_service
        asyncio.create_task(start_realtime_breakout_service())

        # Initialize Real-Time Scanner Engine (Hydrate from DB/WS)
        if not settings.SAFE_MODE:
            from core.scanner.realtime_scanner_engine import get_realtime_scanner_engine
            # Run initialization in a task to avoid blocking the main server boot
            asyncio.create_task(get_realtime_scanner_engine().initialize())
        else:
            logger.info("Project Aegis: Skipping blocking Real-time Scanner initialization in Safe Mode.")
        
        logger.info("?? Real-time data engines initiated.")
    except Exception as e:
        logger.error(f"Startup warning for non-critical services: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("?? QuantAI Backend Shutting Down...")

# 8. Root Endpoints
from api.health import health_check, readiness_check

@app.get("/health", tags=["Health"])
async def root_health_check():
    return await health_check()

@app.get("/ready", tags=["Health"])
async def root_readiness_check():
    return await readiness_check()

@app.get("/metrics", tags=["Observability"])
async def prometheus_metrics():
    from core.observability.metrics import get_metrics
    metrics = get_metrics()
    return Response(content=metrics.get_metrics_output(), media_type=metrics.get_content_type())

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "QuantAI Professional",
        "version": "2.0.0",
        "api_root": "/api",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
