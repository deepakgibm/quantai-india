"""
Upstox API Client Wrapper for AlphaPrime Module

Production-grade wrapper with:
- Token bucket rate limiting (100 req/min)
- Exponential backoff retry logic
- Historical and live data fetching
- Error handling and logging
"""

import asyncio
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from config import settings
import pandas as pd


class RateLimiter:
    """
    Token bucket rate limiter for Upstox API compliance.
    Limits: 100 requests/minute with burst capacity.
    """
    
    def __init__(self, rate_per_minute: int = 100, burst: int = 10):
        self.rate_per_minute = rate_per_minute
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token, waiting if necessary"""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Refill tokens based on elapsed time
            self.tokens = min(
                self.burst,
                self.tokens + (elapsed * self.rate_per_minute / 60.0)
            )
            self.last_update = now
            
            # Wait if no tokens available
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * 60.0 / self.rate_per_minute
                await asyncio.sleep(wait_time)
                self.tokens = 1
            
            self.tokens -= 1


class UpstoxClient:
    """
    Async wrapper for Upstox API with rate limiting and retry logic.
    """
    
    BASE_URL = "https://api.upstox.com/v2"
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or settings.UPSTOX_ACCESS_TOKEN
        self.rate_limiter = RateLimiter(
            rate_per_minute=settings.UPSTOX_RATE_LIMIT_PER_MINUTE,
            burst=settings.UPSTOX_RATE_LIMIT_BURST
        )
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        })
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout))
    )
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            JSON response as dict
            
        Raises:
            requests.exceptions.HTTPError: On HTTP errors
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"Request error: {e}")
            raise
    
    async def get_historical_data(
        self,
        symbol: str,
        instrument_key: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = "1minute"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from Upstox.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            instrument_key: Upstox instrument key (e.g., "NSE_EQ|INE002A01018")
            from_date: Start date
            to_date: End date
            interval: Candle interval (1minute, 5minute, 1day, etc.)
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        await self.rate_limiter.acquire()
        
        # Upstox API endpoint for historical data
        endpoint = f"/historical-candle/{instrument_key}/{interval}/{to_date.strftime('%Y-%m-%d')}/{from_date.strftime('%Y-%m-%d')}"
        
        try:
            data = self._make_request("GET", endpoint)
            
            if data.get("status") != "success" or not data.get("data", {}).get("candles"):
                print(f"No data for {symbol} from {from_date} to {to_date}")
                return pd.DataFrame()
            
            # Parse candles into DataFrame
            candles = data["data"]["candles"]
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
            
            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["symbol"] = symbol
            df = df.drop(columns=["oi"])  # Drop open interest
            
            return df[["symbol", "timestamp", "open", "high", "low", "close", "volume"]]
            
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_live_quotes(self, instrument_keys: List[str]) -> Dict[str, Dict]:
        """
        Fetch multiple market quotes in a single batch request.
        
        Args:
            instrument_keys: List of Upstox instrument keys
            
        Returns:
            Dict mapping instrument_key to quote data
        """
        if not instrument_keys:
            return {}
            
        import urllib.parse
        await self.rate_limiter.acquire()
        
        # Join keys with comma and encode
        keys_str = ",".join(instrument_keys)
        encoded_keys = urllib.parse.quote(keys_str, safe=',')
        
        endpoint = f"/market-quote/quotes?instrument_key={encoded_keys}"
        
        try:
            data = self._make_request("GET", endpoint)
            
            results = {}
            if data.get("status") == "success" and data.get("data"):
                for key, quote_data in data["data"].items():
                    # Upstox might use different key format in response (e.g. NSE_EQ:RELIANCE instead of NSE_EQ|RELIANCE)
                    # We should map back if possible, or just return the data
                    
                    prev_close = quote_data.get("previous_close") or quote_data.get("ohlc", {}).get("close")
                    ltp = quote_data.get("last_price", 0)
                    
                    net_change = quote_data.get("net_change", 0)
                    change_pct = quote_data.get("percentage_change", 0)
                    
                    if not change_pct and prev_close and prev_close > 0:
                        change_pct = ((ltp - prev_close) / prev_close) * 100
                    
                    results[key] = {
                        "timestamp": datetime.now(),
                        "open": quote_data.get("ohlc", {}).get("open"),
                        "high": quote_data.get("ohlc", {}).get("high"),
                        "low": quote_data.get("ohlc", {}).get("low"),
                        "close": quote_data.get("ohlc", {}).get("close"),
                        "last_price": ltp,
                        "previous_close": prev_close,
                        "net_change": net_change,
                        "change_percent": change_pct,
                        "volume": quote_data.get("volume"),
                    }
            
            return results
            
        except Exception as e:
            print(f"Error fetching batch live quotes: {e}")
            return {}

    async def get_live_quote(self, instrument_key: str, symbol: str) -> Optional[Dict]:
        """
        Fetch live market quote (LTP, OHLC, volume, previous close).
        
        Args:
            instrument_key: Upstox instrument key
            symbol: Stock symbol for logging
            
        Returns:
            Dict with quote data or None on failure
        """
        import urllib.parse
        await self.rate_limiter.acquire()
        
        # URL-encode the instrument key (contains | and spaces)
        encoded_key = urllib.parse.quote(instrument_key, safe='')
        
        # Use full quote endpoint which includes previous close
        endpoint = f"/market-quote/quotes?instrument_key={encoded_key}"
        
        try:
            data = self._make_request("GET", endpoint)
            
            if data.get("status") == "success" and data.get("data"):
                # Extract the quote (key might vary)
                quote_data = next(iter(data["data"].values()))
                
                # Get previous close - Upstox provides this in full quote
                # If not available, try to use close from OHLC
                prev_close = quote_data.get("previous_close") or quote_data.get("ohlc", {}).get("close")
                ltp = quote_data.get("last_price", 0)
                
                # Calculate change if we have previous close
                net_change = quote_data.get("net_change", 0)
                change_pct = quote_data.get("percentage_change", 0)
                
                # If API doesn't provide change, calculate it
                if not change_pct and prev_close and prev_close > 0:
                    change_pct = ((ltp - prev_close) / prev_close) * 100
                
                return {
                    "symbol": symbol,
                    "timestamp": datetime.now(),
                    "open": quote_data.get("ohlc", {}).get("open"),
                    "high": quote_data.get("ohlc", {}).get("high"),
                    "low": quote_data.get("ohlc", {}).get("low"),
                    "close": quote_data.get("ohlc", {}).get("close"),
                    "last_price": ltp,
                    "previous_close": prev_close,
                    "net_change": net_change,
                    "change_percent": change_pct,
                    "volume": quote_data.get("volume"),
                }
            
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Token expired
                pass
            return None
        except Exception as e:
            print(f"Error fetching live quote for {symbol}: {e}")
            return None
    
    async def get_nifty_200_symbols(self) -> List[Tuple[str, str]]:
        """
        Fetch Nifty 200 constituent symbols and their instrument keys.
        Reads from nifty200_instruments.json file.
        
        Returns:
            List of tuples: [(symbol, instrument_key), ...]
        """
        import json
        from pathlib import Path
        
        # Read from JSON file
        json_path = Path(__file__).parent.parent / "nifty200_instruments.json"
        if json_path.exists():
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                # data is list of [symbol, instrument_key] pairs
                return [(item[0], item[1]) for item in data]
            except Exception as e:
                print(f"Error reading nifty200_instruments.json: {e}")
        
        # Fallback to hardcoded subset
        NIFTY_50_MAPPING = {
            "RELIANCE": "NSE_EQ|INE002A01018",
            "TCS": "NSE_EQ|INE467B01029",
            "HDFCBANK": "NSE_EQ|INE040A01034",
            "INFY": "NSE_EQ|INE009A01021",
            "ICICIBANK": "NSE_EQ|INE090A01021",
        }
        
        return list(NIFTY_50_MAPPING.items())
    
    async def batch_fetch_historical(
        self,
        symbols: List[Tuple[str, str]],
        from_date: datetime,
        to_date: datetime,
        interval: str = "1minute"
    ) -> pd.DataFrame:
        """
        Batch fetch historical data for multiple symbols.
        
        Args:
            symbols: List of (symbol, instrument_key) tuples
            from_date: Start date
            to_date: End date
            interval: Candle interval
            
        Returns:
            Combined DataFrame with all symbols
        """
        all_data = []
        
        for symbol, instrument_key in symbols:
            print(f"Fetching {symbol} from {from_date.date()} to {to_date.date()}...")
            
            df = await self.get_historical_data(
                symbol=symbol,
                instrument_key=instrument_key,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
            
            if not df.empty:
                all_data.append(df)
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.1)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        
        return pd.DataFrame()
    
    async def get_profile(self) -> Dict:
        """Fetch user profile"""
        await self.rate_limiter.acquire()
        return self._make_request("GET", "/user/profile")

    async def get_positions(self) -> List[Dict]:
        """Fetch all positions (short-term and long-term)"""
        await self.rate_limiter.acquire()
        # Fetch both and combine
        short_term = self._make_request("GET", "/portfolio/short-term-positions")
        # long_term = self._make_request("GET", "/portfolio/long-term-positions") # Optional depending on API
        
        positions = []
        if short_term.get("status") == "success":
            positions.extend(short_term.get("data", []))
            
        return positions

    async def get_holdings(self) -> List[Dict]:
        """Fetch holdings"""
        await self.rate_limiter.acquire()
        response = self._make_request("GET", "/portfolio/long-term-holdings")
        if response.get("status") == "success":
            return response.get("data", [])
        return []

    async def get_orders(self) -> List[Dict]:
        """Fetch order book"""
        await self.rate_limiter.acquire()
        response = self._make_request("GET", "/order/retrieve-all")
        if response.get("status") == "success":
            return response.get("data", [])
        return []

    async def place_order(
        self,
        instrument_token: str,
        quantity: int,
        product: str,  # I (Intraday) or D (Delivery)
        transaction_type: str,  # BUY or SELL
        order_type: str,  # MARKET, LIMIT, SL, SL-M
        price: float = 0.0,
        trigger_price: float = 0.0,
        tag: str = None
    ) -> Dict:
        """
        Place an order.
        """
        await self.rate_limiter.acquire()
        
        payload = {
            "quantity": quantity,
            "product": product,
            "validity": "DAY",
            "price": price,
            "tag": tag,
            "instrument_token": instrument_token,
            "order_type": order_type,
            "transaction_type": transaction_type,
            "disclosed_quantity": 0,
            "trigger_price": trigger_price,
            "is_amo": False
        }
        
        return self._make_request("POST", "/order/place", json=payload)

    async def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        await self.rate_limiter.acquire()
        return self._make_request("DELETE", f"/order/cancel?order_id={order_id}")

    def close(self):
        """Close the session"""
        self.session.close()


# Singleton instance
_upstox_client = None

def get_upstox_client(access_token: Optional[str] = None) -> UpstoxClient:
    """Get or create a singleton Upstox client instance"""
    global _upstox_client
    
    if _upstox_client is None:
        _upstox_client = UpstoxClient(access_token)
    
    return _upstox_client
