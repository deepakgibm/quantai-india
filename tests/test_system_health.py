import pytest
import requests

BASE_URL = "http://localhost:3000"

def test_system_health():
    """Verify GET /api/system/health returns correct structure."""
    r = requests.get(f"{BASE_URL}/api/system/health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    
    assert "backend" in data
    assert "database" in data
    assert "redis" in data
    assert "upstox" in data
    assert "firebase" in data
    assert "websocket" in data
    assert "version" in data
    
    assert data["backend"] == "healthy"
    assert data["database"] in ("healthy", "unhealthy")
    assert data["redis"] in ("healthy", "unhealthy")

def test_upstox_health():
    """Verify GET /api/system/upstox-health returns correct structure."""
    r = requests.get(f"{BASE_URL}/api/system/upstox-health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    
    assert "status" in data
    assert "token_valid" in data
    assert "api_reachable" in data
    assert "last_checked" in data
    
    assert data["status"] in ("healthy", "unhealthy")
    assert isinstance(data["token_valid"], bool)
    assert isinstance(data["api_reachable"], bool)

def test_structured_error_responses():
    """Verify custom error handler formats unhandled exceptions or 404s correctly."""
    r = requests.get(f"{BASE_URL}/api/some-nonexistent-route", timeout=10)
    assert r.status_code == 404
    data = r.json()
    
    assert "success" in data
    assert "service" in data
    assert "error_code" in data
    assert "message" in data
    assert "details" in data
    
    assert data["success"] is False
    assert data["service"] == "quantai-backend"
    assert "404" in data["error_code"]
