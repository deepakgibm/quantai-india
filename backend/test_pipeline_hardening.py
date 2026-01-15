"""
Test script for the new Metadata Cache and Metrics API.
"""
import sys
sys.path.insert(0, '.')

def test_metadata_cache_service():
    """Test the MetadataCacheService directly."""
    print("=" * 60)
    print("TESTING: MetadataCacheService")
    print("=" * 60)
    
    try:
        from services.metadata_cache_service import get_metadata_cache_service
        service = get_metadata_cache_service()
        
        # Test 1: Load symbols from DB (bypassing cache)
        print("\n1. Loading symbols from database...")
        symbols = service._load_symbols_from_db()
        print(f"   ✅ Loaded {len(symbols)} symbols")
        
        if symbols:
            print(f"   Sample: {symbols[0]}")
        
        # Test 2: Get strategies (built-in)
        print("\n2. Getting strategy definitions...")
        strategies = service.get_strategies()
        print(f"   ✅ Found {len(strategies)} strategies")
        for s in strategies[:3]:
            print(f"   - {s['id']}: {s['name']}")
        
        # Test 3: Get stats
        print("\n3. Getting cache stats...")
        stats = service.get_stats()
        print(f"   {stats}")
        
        print("\n" + "=" * 60)
        print("MetadataCacheService: All tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_circuit_breaker():
    """Test the CircuitBreaker utility."""
    print("\n" + "=" * 60)
    print("TESTING: CircuitBreaker")
    print("=" * 60)
    
    try:
        from utils.circuit_breaker import CircuitBreaker, CircuitState
        
        # Create a test circuit breaker
        cb = CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=5
        )
        
        print("\n1. Initial state (should be CLOSED)...")
        print(f"   State: {cb.state.value}")
        assert cb.state == CircuitState.CLOSED
        print("   ✅ PASSED")
        
        print("\n2. Recording failures until circuit opens...")
        for i in range(3):
            cb.record_failure()
            print(f"   Failure {i+1}: state={cb.state.value}")
        
        assert cb.state == CircuitState.OPEN
        print("   ✅ Circuit opened after threshold failures")
        
        print("\n3. Requests should be rejected when OPEN...")
        allowed = cb.allow_request()
        print(f"   allow_request() = {allowed}")
        assert not allowed
        print("   ✅ PASSED")
        
        print("\n4. Getting stats...")
        stats = cb.get_stats()
        print(f"   {stats}")
        
        print("\n5. Manual reset...")
        cb.reset()
        print(f"   State after reset: {cb.state.value}")
        assert cb.state == CircuitState.CLOSED
        print("   ✅ PASSED")
        
        print("\n" + "=" * 60)
        print("CircuitBreaker: All tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PRODUCTION DATA PIPELINE HARDENING - UNIT TESTS")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("MetadataCacheService", test_metadata_cache_service()))
    results.append(("CircuitBreaker", test_circuit_breaker()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    sys.exit(0 if passed == len(results) else 1)
