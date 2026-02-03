import asyncio
import os
import sys

# Mock metrics to avoid prometheus dependency in basic test
sys.path.append(os.getcwd())

from core.resilience.circuit_breaker import CircuitBreaker

async def test_metrics_integration():
    cb = CircuitBreaker("MetricsTest", failure_threshold=1)
    
    print("Testing transition to OPEN...")
    try:
        await cb.call(lambda: asyncio.sleep(0.1) or exec('raise ValueError("fail")'))
    except:
        pass
    
    print(f"Current State: {cb.state.value}")
    
    print("Testing rejection metric...")
    try:
        await cb.call(lambda: None)
    except Exception as e:
        print(f"Caught expected rejection: {e}")

if __name__ == "__main__":
    asyncio.run(test_metrics_integration())
