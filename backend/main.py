from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import asyncio
from datetime import datetime

# 1. Logging Configuration
# 1. Observability Configuration
from core.observability.logging import configure_logging, get_logger
from core.observability.middleware import setup_observability_middleware
from core.observability.metrics import get_metrics

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
import models
import models_ml
import models_alpha
import models_indicators
import models_risk
import models_bot
import screener.models

# 3. CORS Configuration (env-driven, not hardcoded wildcard)
from config import settings as app_settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# if _observability_available:
#     setup_observability_middleware(app)

# 4. Exception Handlers
from utils.error_responses import generic_exception_handler, validation_exception_handler
from fastapi.exceptions import RequestValidationError

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return await generic_exception_handler(request, exc)

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request, exc):
    return await validation_exception_handler(request, exc)

# 5. Router Imports (Unified Layer)
from api.auth import router as auth_router
from api.ai import router as ai_router
from api.forecast import router as forecast_router
from api.scanners import router as scanner_router
from api.market_data import router as market_router
from api.indicators import router as indicator_router
from api.health import router as health_router
from api.trading import router as trading_router
from api.orders import router as orders_router
from api.analytics import router as analytics_router
from api.risk import router as risk_router
from api.etl_status import router as etl_router
from api.metrics import router as metrics_router
from api.upstox import router as upstox_router
from api.admin import router as admin_router
from api.engines import router as engine_router
from api.bot import router as bot_router
from api.v1.experiment_lab import router as experiment_lab_router
from api.v1.backtest_strategies import router as backtest_strategies_router
from engine.scanner_api import router as scanner_v3_router
from screener.api.screener_router import router as screener_router
from api.websockets import market_ws_router
from api.search import router as search_router
from api.volatility import router as volatility_router
from api.option_flow import router as option_flow_router
from api.heatmap import router as heatmap_router


# 6. Unified API Registration (Flattened for Reliability)
app.include_router(health_router, prefix="/api/health", tags=["Health"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(market_router, prefix="/api/market", tags=["Market Data"])
app.include_router(indicator_router, prefix="/api/indicators", tags=["Technical Indicators"])
app.include_router(scanner_router, prefix="/api/scanner", tags=["Standard Scanners"])
app.include_router(forecast_router, prefix="/api/forecast", tags=["ML Forecasts"])
app.include_router(trading_router, prefix="/api/trading", tags=["Trading Operations"])
app.include_router(orders_router, prefix="/api/orders", tags=["Order Management"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Performance Analytics"])
app.include_router(risk_router, prefix="/api/risk", tags=["Risk Management"])
app.include_router(etl_router, prefix="/api/etl", tags=["Data Pipelines"])
app.include_router(metrics_router, prefix="/api/metrics", tags=["System Metrics"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI Engine"])
app.include_router(upstox_router, prefix="/api/upstox", tags=["Upstox Broker"])
app.include_router(admin_router, prefix="/api/admin", tags=["Administration"])
app.include_router(engine_router, prefix="/api/engines", tags=["Engine Management"])
app.include_router(bot_router, prefix="/api/bot", tags=["Signal Bot"])
app.include_router(screener_router, prefix="/api/screener", tags=["Trade Screener"])
app.include_router(scanner_v3_router, prefix="/api/scanners/v3", tags=["HP Scanner V3 (Phase 1)"])
app.include_router(market_ws_router, prefix="/api/ws", tags=["Market WebSockets"])
app.include_router(search_router, prefix="/api/search", tags=["Search"])
app.include_router(volatility_router, prefix="/api/volatility", tags=["Volatility"])
app.include_router(option_flow_router, prefix="/api/option-flow", tags=["Option Flow"])
app.include_router(heatmap_router, prefix="/api/heatmap", tags=["Heatmap"])


from api.v1 import router as v1_router
app.include_router(v1_router, prefix="/api/v1")

logger.info("?? QuantAI Production API v2.0 Registered at Root.")

# 7. Lifecycle Events
@app.on_event("startup")
async def startup_event():
    logger.info("?? QuantAI Backend Starting Up...")
    try:
        from database import init_db
        await init_db()
        logger.info("?? Database schema verified/created.")
        
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
        logger.error(f"Startup warning: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("?? QuantAI Backend Shutting Down...")

# 8. Root Endpoints
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
