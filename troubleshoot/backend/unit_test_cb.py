import asyncio
from core.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException

async def fail_func():
    raise ValueError("Service Failure")

async def test_cb_logic():
    cb = CircuitBreaker("UnitTester", failure_threshold=2, recovery_timeout=1.0)
    
    print("[1] First Failure")
    try:
        await cb.call(fail_func)
    except ValueError:
        print("Caught expected ValueError")
        
    print(f"State: {cb.state.value}, Failures: {cb.failure_count}")

    print("\n[2] Second Failure (Should trip)")
    try:
        await cb.call(fail_func)
    except ValueError:
        print("Caught expected ValueError (Tripped)")
        
    print(f"State: {cb.state.value}, Failures: {cb.failure_count}")

    print("\n[3] Third Call (Should be OPEN)")
    try:
        await cb.call(fail_func)
    except CircuitBreakerOpenException:
        print("SUCCESS: Caught CircuitBreakerOpenException")
    except Exception as e:
        print(f"FAILURE: Caught unexpected {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_cb_logic())
