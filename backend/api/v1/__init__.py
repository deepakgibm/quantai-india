from fastapi import APIRouter
from .quant_workspace import router as quant_workspace_router
from .walk_forward import router as walk_forward_router
from .institutional_scanner import router as institutional_scanner_router

# Standard Routers
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
from api.search import router as search_router
from api.volatility import router as volatility_router
from api.option_flow import router as option_flow_router
from api.heatmap import router as heatmap_router
from api.sector_analysis import router as sector_analysis_router
from api.volume_profile import router as volume_profile_router
from api.saas_router import router as saas_router
from api.watchlist import router as watchlist_router
from api.metrics import router as metrics_router

router = APIRouter()

# v1 Specific Routers
router.include_router(quant_workspace_router, prefix="/quant")
router.include_router(walk_forward_router, prefix="/walk-forward")
router.include_router(institutional_scanner_router, prefix="/institutional-scanner")

# Mounted standard routers under /api/v1
router.include_router(health_router, prefix="/health", tags=["Health"])
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(market_router, prefix="/market", tags=["Market Data"])
router.include_router(indicator_router, prefix="/indicators", tags=["Technical Indicators"])
router.include_router(scanner_router, prefix="/scanner", tags=["Standard Scanners"])
router.include_router(trading_router, prefix="/trading", tags=["Trading Operations"])
router.include_router(analytics_router, prefix="/analytics", tags=["Performance Analytics"])
router.include_router(ai_router, prefix="/ai", tags=["AI Engine"])
router.include_router(upstox_router, prefix="/upstox", tags=["Upstox Broker"])
router.include_router(engine_router, prefix="/engines", tags=["Engine Management"])
router.include_router(bot_router, prefix="/bot", tags=["Signal Bot"])
router.include_router(screener_router, prefix="/screener", tags=["Trade Screener"])
router.include_router(scanner_v3_router, prefix="/scanners/v3", tags=["HP Scanner V3 (Phase 1)"])
router.include_router(search_router, prefix="/search", tags=["Search"])
router.include_router(volatility_router, prefix="/volatility", tags=["Volatility"])
router.include_router(option_flow_router, prefix="/option-flow", tags=["Option Flow"])
router.include_router(heatmap_router, prefix="/heatmap", tags=["Heatmap"])
router.include_router(sector_analysis_router, prefix="/sector-analysis", tags=["Sector Analysis"])
router.include_router(volume_profile_router, prefix="/volume-profile", tags=["Volume Profile"])
router.include_router(saas_router, prefix="/saas", tags=["SaaS Enterprise"])
router.include_router(watchlist_router, prefix="/watchlist", tags=["Watchlist"])
router.include_router(metrics_router, prefix="/metrics", tags=["Metrics"])




