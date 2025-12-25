from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routers import auth, upstox, trading, ai, orders, risk, settings, algorithms, agentic_bot, engine_performance, quant_bot, alerts, scanner, market
from api.v1.endpoints import alpha # Added AlphaPrime import
from api.v1.endpoints import walk_forward_backtest  # Walk-Forward Backtest
from database import init_db
from services.upstox_ws_manager import get_upstox_ws_manager

# Optional: Real-time scanner engine (may fail due to optional dependencies)
try:
    from core.scanner.realtime_scanner_engine import get_realtime_scanner_engine
    _realtime_scanner_available = True
except ImportError as e:
    print(f"Real-time scanner not available: {e}")
    get_realtime_scanner_engine = None
    _realtime_scanner_available = False

app = FastAPI(
    title="QuantAI India Trading Bot API",
    description="AI-Powered Trading Bot with Upstox Integration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    import asyncio
    
    # Initialize database with timeout
    try:
        await asyncio.wait_for(init_db(), timeout=10.0)
        print("Database initialized")
    except asyncio.TimeoutError:
        print("Database init timed out - will retry on first request")
    except Exception as e:
        print(f"Database init error: {e}")
    
    # Initialize Real-time services in background (don't block startup)
    async def init_realtime():
        try:
            get_upstox_ws_manager()
            if _realtime_scanner_available and get_realtime_scanner_engine:
                engine = get_realtime_scanner_engine()
                await asyncio.wait_for(engine.initialize(), timeout=30.0)
                print("Real-time Scanner Engine initialized")
            else:
                print("Real-time Scanner Engine not available - skipping")
        except asyncio.TimeoutError:
            print("Real-time services initialization timed out")
        except Exception as e:
            print(f"Real-time services initialization skipped: {e}")
    
    asyncio.create_task(init_realtime())
    print("Server startup complete - ready to accept requests")

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
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
app.include_router(alerts.router)  # Alerts router (already has full prefix)
app.include_router(alpha.router)  # AlphaPrime router (already has full prefix in router definition)
app.include_router(scanner.router)  # Scanner router (already has full prefix)
app.include_router(market.router, prefix="/api/market", tags=["Market"])
app.include_router(walk_forward_backtest.router)  # Walk-Forward Backtest (already has full prefix)

# Phase 3: Analytics and Archive endpoints
try:
    from routers import analytics
    app.include_router(analytics.router)  # Analytics router (already has full prefix)
except ImportError as e:
    print(f"Analytics router not loaded: {e}")

@app.get("/")
async def root():
    return {"message": "QuantAI India Trading Bot API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
