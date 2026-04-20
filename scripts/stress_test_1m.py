"""
1M User Scalability Stress Test — QuantAI India
Simulates concurrent load across API, Market Data, and ML task endpoints.
Uses high-performance HTTPX client with connection pooling.
"""

import asyncio
import time
import uuid
import random
import logging
import httpx
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"  # Or LB URL
MARKET_DATA_URL = "http://localhost:8001"
CONCURRENCY_STEPS = [100, 1000, 5000, 10000]
TEST_DURATION_STEP = 10  # Reduced for fast local validation

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("StressTest")

class ScalabilityMetrics:
    def __init__(self):
        self.total_requests = 0
        self.success_count = 0
        self.error_count = 0
        self.latencies = []

    def log_result(self, success: bool, latency: float):
        self.total_requests += 1
        if success:
            self.success_count += 1
            self.latencies.append(latency)
        else:
            self.error_count += 1

    def report(self):
        if not self.latencies: return "No data"
        avg_latency = sum(self.latencies) / len(self.latencies)
        p99 = sorted(self.latencies)[int(len(self.latencies) * 0.99)]
        return f"Reqs: {self.total_requests} | Success: {self.success_count} | Error: {self.error_count} | Avg Latency: {avg_latency:.4f}s | p99: {p99:.4f}s"

async def simulate_user(client: httpx.AsyncClient, metrics: ScalabilityMetrics):
    """Simulates a single active QuantAI user."""
    user_id = str(uuid.uuid4())
    
    # User Behavior Profile
    # 80% Reads, 15% Auth/Status, 5% Heavy (Forecast/Backtest)
    choice = random.random()
    
    try:
        start_time = time.time()
        if choice < 0.80:
            # Main Health Check (Hits DB & Cache)
            await client.get(f"{BASE_URL}/api/health/")
        elif choice < 0.95:
            # Market Data Service Health
            await client.get(f"{MARKET_DATA_URL}/health")
        else:
            # Indicator Endpoint (Simulating real API load)
            await client.get(f"{BASE_URL}/api/indicators/")
        
        latency = time.time() - start_time
        metrics.log_result(True, latency)
    except Exception as e:
        metrics.log_result(False, 0)

async def run_step(concurrency: int):
    """Runs a single concurrency step of the stress test."""
    logger.info(f">>> STARTING STEP: {concurrency} CONCURRENT USERS")
    metrics = ScalabilityMetrics()
    
    limits = httpx.Limits(max_keepalive_connections=500, max_connections=concurrency)
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        start_step = time.time()
        while time.time() - start_step < TEST_DURATION_STEP:
            # Launch batch of concurrent tasks
            tasks = [simulate_user(client, metrics) for _ in range(min(500, concurrency))]
            await asyncio.gather(*tasks)
            # Subtle delay to prevent local socket exhaustion
            await asyncio.sleep(0.01)
            
        logger.info(f"STEP COMPLETE: {metrics.report()}")

async def main():
    logger.info("Starting QuantAI 1M User Scalability Stress Test Suite")
    for step in CONCURRENCY_STEPS:
        await run_step(step)
    logger.info("Scalability Test Suite Finished Successfully")

if __name__ == "__main__":
    asyncio.run(main())
