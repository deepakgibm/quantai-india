"""
End-to-End API Testing for AlphaPrime
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test 1: Health check"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        print("✅ PASS - Backend is healthy")
        print(f"   Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ FAIL - {e}")
        return False


def test_login():
    """Test 2: User login"""
    print("\n" + "="*60)
    print("TEST 2: User Login")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "demo@example.com",
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        assert "access_token" in data
        
        print("✅ PASS - Login successful")
        print(f"   Email: demo@example.com")
        print(f"   Token: {data['access_token'][:30]}...")
        
        return data['access_token']
    except Exception as e:
        print(f"❌ FAIL - {e}")
        if response:
            print(f"   Response: {response.text}")
        return None


def test_alphaprime_signals(token):
    """Test 3: AlphaPrime signals endpoint"""
    print("\n" + "="*60)
    print("TEST 3: AlphaPrime Signals API")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/alpha-prime/signals?limit=5",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Status: {response.status_code}"
        signals = response.json()
        assert isinstance(signals, list)
        assert len(signals) > 0, "No signals returned"
        
        print(f"✅ PASS - Retrieved {len(signals)} signals")
        print("\n   Top 3 Signals:")
        for i, sig in enumerate(signals[:3], 1):
            print(f"   #{i}: {sig['symbol']:12s} - Score: {sig['alpha_score']:.4f} - RSI: {sig.get('rsi', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ FAIL - {e}")
        if response:
            print(f"   Response: {response.text[:200]}")
        return False


def test_alphaprime_config(token):
    """Test 4: AlphaPrime configuration"""
    print("\n" + "="*60)
    print("TEST 4: AlphaPrime Config API")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/alpha-prime/config",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        config = response.json()
        assert config["status"] == "success"
        
        print("✅ PASS - Configuration retrieved")
        print(f"   ML Enabled: {config['config']['ml_enabled']}")
        print(f"   Paper Trade: {config['config']['paper_trade_mode']}")
        print(f"   Min Confidence: {config['config']['min_confidence']}")
        
        return True
    except Exception as e:
        print(f"❌ FAIL - {e}")
        return False


def test_frontend():
    """Test 5: Frontend availability"""
    print("\n" + "="*60)
    print("TEST 5: Frontend Availability")
    print("="*60)
    
    try:
        response = requests.get("http://localhost:3000")
        assert response.status_code == 200
        print("✅ PASS - Frontend is accessible")
        print("   URL: http://localhost:3000")
        return True
    except Exception as e:
        print(f"❌ FAIL - {e}")
        return False


def main():
    print("\n" + "="*60)
    print("ALPHAPRIME END-TO-END API TESTING")
    print("="*60)
    
    results = {}
    
    # Test 1: Health
    results['health'] = test_health()
    
    # Test 2: Login
    token = test_login()
    results['login'] = token is not None
    
    if token:
        # Test 3: Signals
        results['signals'] = test_alphaprime_signals(token)
        
        # Test 4: Config
        results['config'] = test_alphaprime_config(token)
    else:
        results['signals'] = False
        results['config'] = False
    
    # Test 5: Frontend
    results['frontend'] = test_frontend()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test.upper()}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! AlphaPrime is fully functional!")
        print("\nNext steps:")
        print("1. Open http://localhost:3000")
        print("2. Login: demo@example.com / testpass123")
        print("3. Click 'AlphaPrime' in sidebar")
        print("4. View signals and test features!")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
    
    print()


if __name__ == "__main__":
    main()
