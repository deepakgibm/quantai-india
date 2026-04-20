"""
Market Data Microservice — main.py
FastAPI standalone service for real-time market data orchestration and broadcasting.
"""

import asyncio
from fastapi import FastAPI
from services.market_data_service.orchestrator import MarketDataOrchestratorMS

app = FastAPI(title="QuantAI Market Data Service")
orchestrator = MarketDataOrchestratorMS()

@app.on_event("startup")
async def startup_event():
    """Start the orchestrator on service startup."""
    asyncio.create_task(orchestrator.start())

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the orchestrator on service shutdown."""
    await orchestrator.stop()

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes/Docker."""
    return {
        "status": "online",
        "source": orchestrator.current_source,
        "is_running": orchestrator.is_running
    }

@app.get("/status")
async def get_status():
    """Get detailed orchestrator status."""
    return {
        "source": orchestrator.current_source,
        "last_tick": orchestrator.last_tick_time.isoformat() if orchestrator.last_tick_time else None,
        "symbols_count": len(orchestrator._symbols)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
