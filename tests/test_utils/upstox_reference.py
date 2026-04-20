"""
Upstox Reference API Client
Fetches reference prices from Upstox API for comparison.
"""

import os
import time
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Simple in-memory cache for rate limiting
_price_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl: int = 60  # seconds


class UpstoxReferenceClient:
    """
    Client for fetching reference prices from Upstox API.
    Used to validate backend API prices.
    """
    
    BASE_URL = "https://api.upstox.com/v2"
    HISTORICAL_URL = "https://api.upstox.com/v3/historical-candle"
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("UPSTOX_ACCESS_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        self._request_count = 0
        self._last_request_time = 0
        self._rate_limit_delay = 0.5  # seconds between requests
    
    def _rate_limit(self):
        """Apply rate limiting to avoid 429 errors."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()
        self._request_count += 1
    
    def _get_cached(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from cache if not expired."""
        if cache_key in _price_cache:
            cached = _price_cache[cache_key]
            if time.time() - cached["timestamp"] < _cache_ttl:
                return cached["data"]
        return None
    
    def _set_cached(self, cache_key: str, data: Dict[str, Any]):
        """Set cache with timestamp."""
        _price_cache[cache_key] = {
            "data": data,
            "timestamp": time.time()
        }
    
    def get_ltp(self, instrument_key: str) -> Optional[Dict[str, Any]]:
        """
        Get last traded price for an instrument.
        
        Args:
            instrument_key: Upstox instrument key (e.g., NSE_EQ|INE002A01018)
            
        Returns:
            Dict with ltp, open, high, low, close, volume, etc.
        """
        cache_key = f"ltp:{instrument_key}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/market-quote/ltp"
            params = {"instrument_key": instrument_key}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("data"):
                    quote_data = data["data"].get(instrument_key, {})
                    self._set_cached(cache_key, quote_data)
                    return quote_data
            elif response.status_code == 429:
                time.sleep(2)  # Rate limited, wait and retry
                return self.get_ltp(instrument_key)
            
            return None
        except Exception as e:
            print(f"Error fetching LTP for {instrument_key}: {e}")
            return None
    
    def get_full_quote(self, instrument_key: str) -> Optional[Dict[str, Any]]:
        """
        Get full market quote including OHLC.
        
        Args:
            instrument_key: Upstox instrument key
            
        Returns:
            Dict with full quote data including ohlc
        """
        cache_key = f"quote:{instrument_key}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/market-quote/quotes"
            params = {"instrument_key": instrument_key}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("data"):
                    quote_data = data["data"].get(instrument_key, {})
                    self._set_cached(cache_key, quote_data)
                    return quote_data
            
            return None
        except Exception as e:
            print(f"Error fetching quote for {instrument_key}: {e}")
            return None
    
    def get_historical_candles(
        self,
        instrument_key: str,
        interval: str = "day",
        to_date: Optional[str] = None,
        from_date: Optional[str] = None
    ) -> Optional[List[List[Any]]]:
        """
        Get historical candles from Upstox v3 API.
        
        Args:
            instrument_key: Upstox instrument key
            interval: Candle interval (1minute, 5minute, 15minute, 30minute, 1hour, day)
            to_date: End date (YYYY-MM-DD)
            from_date: Start date (YYYY-MM-DD)
            
        Returns:
            List of candles [timestamp, open, high, low, close, volume, oi]
        """
        if to_date is None:
            to_date = datetime.now().strftime("%Y-%m-%d")
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        cache_key = f"candles:{instrument_key}:{interval}:{from_date}:{to_date}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        self._rate_limit()
        
        # Map interval to Upstox API format
        interval_map = {
            "1m": ("minutes", "1"),
            "5m": ("minutes", "5"),
            "15m": ("minutes", "15"),
            "30m": ("minutes", "30"),
            "1h": ("hours", "1"),
            "1d": ("days", "1"),
            "day": ("days", "1"),
        }
        
        unit, value = interval_map.get(interval, ("days", "1"))
        
        try:
            url = f"{self.HISTORICAL_URL}/{instrument_key}/{unit}/{value}/{to_date}/{from_date}"
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    candles = data.get("data", {}).get("candles", [])
                    self._set_cached(cache_key, candles)
                    return candles
            
            return None
        except Exception as e:
            print(f"Error fetching candles for {instrument_key}: {e}")
            return None
    
    def get_batch_ltp(self, instrument_keys: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get LTP for multiple instruments in one call.
        
        Args:
            instrument_keys: List of instrument keys
            
        Returns:
            Dict mapping instrument_key to quote data
        """
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/market-quote/ltp"
            # Upstox allows comma-separated instrument keys
            params = {"instrument_key": ",".join(instrument_keys[:50])}  # Max 50
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return data.get("data", {})
            
            return {}
        except Exception as e:
            print(f"Error fetching batch LTP: {e}")
            return {}


# Singleton instance
_client: Optional[UpstoxReferenceClient] = None


def get_upstox_client() -> UpstoxReferenceClient:
    """Get singleton Upstox reference client."""
    global _client
    if _client is None:
        _client = UpstoxReferenceClient()
    return _client


def get_reference_ltp(symbol: str, instrument_key: Optional[str] = None) -> Optional[float]:
    """
    Convenience function to get reference LTP for a symbol.
    
    Args:
        symbol: Stock symbol (e.g., RELIANCE)
        instrument_key: Optional instrument key (will be looked up if not provided)
        
    Returns:
        LTP as float or None
    """
    from tests.test_utils.test_data import SYMBOL_TO_INSTRUMENT_KEY
    
    if instrument_key is None:
        instrument_key = SYMBOL_TO_INSTRUMENT_KEY.get(symbol)
    
    if instrument_key is None:
        return None
    
    client = get_upstox_client()
    quote = client.get_ltp(instrument_key)
    
    if quote:
        return quote.get("last_price") or quote.get("ltp")
    
    return None


def get_reference_ohlc(symbol: str, instrument_key: Optional[str] = None) -> Optional[Dict[str, float]]:
    """
    Get reference OHLC for a symbol.
    
    Returns:
        Dict with open, high, low, close, volume
    """
    from tests.test_utils.test_data import SYMBOL_TO_INSTRUMENT_KEY
    
    if instrument_key is None:
        instrument_key = SYMBOL_TO_INSTRUMENT_KEY.get(symbol)
    
    if instrument_key is None:
        return None
    
    client = get_upstox_client()
    quote = client.get_full_quote(instrument_key)
    
    if quote and "ohlc" in quote:
        ohlc = quote["ohlc"]
        return {
            "open": ohlc.get("open"),
            "high": ohlc.get("high"),
            "low": ohlc.get("low"),
            "close": ohlc.get("close"),
            "volume": quote.get("volume"),
        }
    
    return None
