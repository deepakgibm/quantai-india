import pytest
import httpx
import time
import asyncio
import numpy as np
from main import app
from unittest.mock import patch, MagicMock
from services.price_manager.price_cache import get_price_cache
from utils.auth import get_current_user

@pytest.fixture
def client():
    try:
        transport = httpx.ASGITransport(app=app)
        return httpx.AsyncClient(transport=transport, base_url="http://test")
    except (AttributeError, TypeError):
        return httpx.AsyncClient(app=app, base_url="http://test")

@pytest.mark.asyncio
async def test_price_api_concurrency_and_performance(client):
    cache = get_price_cache()
    price_data = {
        "symbol": "RELIANCE",
        "ltp": 2500.0,
        "prev_close": 2480.0,
        "timestamp": "2026-07-24T15:30:00+05:30",
        "price_source": "UPSTOX_WS"
    }
    cache.set("RELIANCE", price_data)

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@quantai.com"

    # Set dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user

    async with client as ac:
        
        async def run_concurrent_requests(count):
            tasks = []
            start_time = time.perf_counter()
            
            for _ in range(count):
                tasks.append(ac.get("/api/upstox/market-quote/RELIANCE"))
            
            responses = await asyncio.gather(*tasks)
            total_duration = (time.perf_counter() - start_time) * 1000  # ms
            
            latencies = []
            cache_hits = 0
            failures = 0
            
            for r in responses:
                if r.status_code == 200:
                    latencies.append(total_duration / count)
                    data = r.json()
                    if data.get("status") == "success":
                        symbol_data = data.get("data", {}).get("NSE_EQ:RELIANCE", {})
                        if symbol_data.get("price_source") == "UPSTOX_WS":
                            cache_hits += 1
                    else:
                        failures += 1
                else:
                    failures += 1
            
            p95 = np.percentile(latencies, 95) if latencies else 0
            p99 = np.percentile(latencies, 99) if latencies else 0
            avg = np.mean(latencies) if latencies else 0
            
            return {
                "concurrency": count,
                "avg_latency_ms": round(avg, 2),
                "p95_latency_ms": round(p95, 2),
                "p99_latency_ms": round(p99, 2),
                "cache_hit_ratio": round(cache_hits / count, 2) if count > 0 else 0,
                "failure_rate": round(failures / count, 2) if count > 0 else 0,
                "total_time_ms": round(total_duration, 2)
            }

        scales = [10, 50, 100, 200]
        for scale in scales:
            metrics = await run_concurrent_requests(scale)
            print(f"\nConcurrency {scale} Metrics: {metrics}")
            
            assert metrics["failure_rate"] == 0.0
            assert metrics["avg_latency_ms"] < 100.0

    app.dependency_overrides.clear()
    cache.clear("RELIANCE")
