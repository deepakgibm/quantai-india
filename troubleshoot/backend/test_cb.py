import asyncio
import sys
from services.ai.provider import get_ai_provider, AIProvider
from core.resilience.circuit_breaker import CircuitBreakerOpenException

# Mock the model to fail
class MockFailedModel:
    model_name = "mock-model"
    async def generate_content_async(self, prompt):
        raise Exception("Simulated 500 Error")

async def test_circuit_breaker():
    print("Testing Circuit Breaker...", flush=True)
    provider = get_ai_provider()
    
    # Inject failure model
    provider._model = MockFailedModel()
    
    # Force new CB with low threshold for testing
    from core.resilience.circuit_breaker import CircuitBreaker
    provider._cb = CircuitBreaker("TestGemini", failure_threshold=2, recovery_timeout=5.0)
    
    print("\n[1] Sending request 1 (Expected: Failure)", flush=True)
    try:
        await provider.generate_content("test")
    except Exception as e:
        print(f"Caught expected error: {e}", flush=True)

    print("\n[2] Sending request 2 (Expected: Failure)", flush=True)
    try:
        await provider.generate_content("test")
    except Exception as e:
        print(f"Caught expected error: {e}", flush=True)
        
    print("\n[3] Sending request 3 (Expected: Circuit Breaker Open)", flush=True)
    try:
        await provider.generate_content("test")
    except Exception as e:
        print(f"Caught: {e}", flush=True)
        # Need to check exception details for specific message
        if hasattr(e, 'detail') and "Circuit Open" in e.detail:
             print("SUCCESS: Circuit Breaker triggered correctly.", flush=True)
        else:
             print("FAILURE: Circuit exceeded threshold but did not throw CB exception.", flush=True)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_circuit_breaker())
