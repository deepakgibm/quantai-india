from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import asyncio
from datetime import datetime

# 1. Logging Configuration
try:
    from core.observability.logging import configure_logging, get_logger
    from core.observability.middleware import setup_observability_middleware
    from core.observability.metrics import get_metrics
    configure_logging()
    logger = get_logger(__name__)
    _observability_available = True
except ImportError:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    _observability_available = False

# 2. Main Application Instance
app = FastAPI(
    title="QuantAI India",
    description="AI-Powered Professional Trading & Analytics Platform",
    version="2.0.0"
)

# 3. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if _observability_available:
    setup_observability_middleware(app)

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

# 6. Unified API Sub-App
api = FastAPI(title="QuantAI API", version="2.0.0")

# Register Routes
api.include_router(health_router, prefix="/health")
api.include_router(auth_router, prefix="/auth")
api.include_router(market_router, prefix="/market")
api.include_router(indicator_router, prefix="/indicators")
api.include_router(scanner_router, prefix="/scanner")
api.include_router(forecast_router, prefix="/forecast")
api.include_router(trading_router, prefix="/trading")
api.include_router(orders_router, prefix="/orders")
api.include_router(analytics_router, prefix="/analytics")
api.include_router(risk_router, prefix="/risk")
api.include_router(etl_router, prefix="/etl")
api.include_router(metrics_router, prefix="/metrics")
api.include_router(ai_router, prefix="/ai")
api.include_router(upstox_router, prefix="/upstox")
api.include_router(admin_router, prefix="/admin")
api.include_router(engine_router, prefix="/engines")

from api.v1 import router as v1_router
api.include_router(v1_router, prefix="/v1")

# Mount API
app.mount("/api", api)

# 7. Lifecycle Events
@app.on_event("startup")
async def startup_event():
    logger.info("?? QuantAI Backend Starting Up...")
    try:
        # Initialize Core Services
        from services.market_data_orchestrator import get_market_data_orchestrator
        orchestrator = get_market_data_orchestrator()
        asyncio.create_task(orchestrator.start())
        
        from services.nifty100_ranking_service import start_nifty100_ranking_service
        asyncio.create_task(start_nifty100_ranking_service())

        from services.sector_service import start_sector_service
        asyncio.create_task(start_sector_service())
        
        from services.realtime_yearly_breakout_engine import start_realtime_breakout_service
        asyncio.create_task(start_realtime_breakout_service())

        # Initialize Real-Time Scanner Engine (Hydrate from DB/WS)
        from core.scanner.realtime_scanner_engine import get_realtime_scanner_engine
        await get_realtime_scanner_engine().initialize()
        
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
