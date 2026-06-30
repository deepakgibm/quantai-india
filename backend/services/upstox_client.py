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
import httpx
import urllib.parse
import logging
import pandas as pd

logger = logging.getLogger(__name__)

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings
from database import SessionLocal
from services.auth.token_manager import TokenManagerService


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
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                self.tokens = 1
            
            self.tokens -= 1


class UpstoxClient:
    """
    Async wrapper for Upstox API with rate limiting and retry logic.
    """
    
    BASE_URL = "https://api.upstox.com/v2"
    
    def __init__(self, access_token: Optional[str] = None):
        # 1. Provide an explicit access token override (if not a placeholder).
        # 2. Or fallback to TokenManagerService Analytics Token DB
        # 3. Or lastly to the .env legacy settings
        
        is_placeholder = not access_token or "your-token" in str(access_token).lower()
        
        if access_token and not is_placeholder:
            self.access_token = access_token
        else:
            db = SessionLocal()
            try:
                manager = TokenManagerService(db)
                self.access_token = manager.get_analytics_token() or settings.UPSTOX_ACCESS_TOKEN
            finally:
                db.close()
                
        self.rate_limiter = RateLimiter(
            rate_per_minute=settings.UPSTOX_RATE_LIMIT_PER_MINUTE,
            burst=settings.UPSTOX_RATE_LIMIT_BURST
        )
        self._client = None
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "Api-Key": settings.UPSTOX_API_KEY
        }
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(10.0, connect=5.0)
            )
        return self._client

    class UpstoxSystemFailure(Exception): 
        """Exception that triggers the Circuit Breaker"""
        pass

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=1, max=3),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException))
    )
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict:
        """
        Make HTTP request with retry logic.
        Only retries on network errors, not on HTTP status errors (401, 429, etc.).
        """
        from core.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException

        if not hasattr(self, '_cb'):
            self._cb = CircuitBreaker(
                "UpstoxAPI", 
                failure_threshold=5, 
                recovery_timeout=30.0,  # Reduced from 60s: attempt recovery sooner
                expected_exceptions=(self.UpstoxSystemFailure,)
            )

        url = f"{self.BASE_URL}{endpoint}"
        
        async def _execute():
            logger.info(f"[Upstox Request] {method} {url} | Params: {params} | Token Present: {bool(self.access_token)}")
            start_time = time.time()
            try:
                response = await self.client.request(method, url, params=params, **kwargs)
                latency = round(time.time() - start_time, 3)
                logger.info(f"[Upstox Response] {response.status_code} for {method} {endpoint} | Latency: {latency}s | Size: {len(response.content)} bytes")
                
                # Treat 5xx as system failure
                if response.status_code >= 500:
                    logger.error(f"Upstox 5xx Server Error: {response.status_code} for {endpoint}")
                    raise self.UpstoxSystemFailure(f"Upstox Server Error: {response.status_code}")
                
                # Treat 429 as system failure (rate limit exceeded)
                if response.status_code == 429:
                    logger.warning(f"Upstox 429 Rate Limit: {endpoint}")
                    raise self.UpstoxSystemFailure("Upstox Rate Limit Exceeded")

                response.raise_for_status()
                return response.json()
                
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.error(f"Upstox Network Error: {e}")
                raise self.UpstoxSystemFailure(f"Upstox Network Error: {str(e)}")
            except httpx.HTTPStatusError as e:
                # 4xx errors (except 429) do NOT trigger the circuit breaker
                # but we still want to raise them to the caller
                raise

        try:
             # Circuit Breaker wraps the execution
            return await self._cb.call(_execute)
            
        except CircuitBreakerOpenException:
            # Fallback for when Upstox is down
            logger.error(f"Upstox Circuit Open: Skipping request to {endpoint}")
            return {"status": "error", "message": "Upstox Service Temporarily Unavailable", "data": {}}
            
        except httpx.HTTPStatusError as e:
            # Handle 401 Unauthorized (Session Expired)
            if e.response.status_code == 401:
                logger.warning(f"Upstox 401 Unauthorized: Session may have expired for {endpoint}")
                # Attempt to refresh token if logic is available
                if await self.refresh_access_token():
                    logger.info("Token refreshed successfully, retrying request...")
                    # Update headers
                    self.headers["Authorization"] = f"Bearer {self.access_token}"
                    # Recreate the httpx client so it picks up the new headers
                    if self._client:
                        try:
                            await self._client.aclose()
                        except Exception:
                            pass
                        self._client = None
                    return await _execute()
                else:
                    logger.error("Token refresh failed or not available. Manual re-login required.")
            
            if e.response.status_code != 401:
                 logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise

    async def refresh_access_token(self) -> bool:
        """
        Attempt to refresh the Upstox access token.
        Always resolves to Analytics Token if standard auth token expires.
        """
        db = SessionLocal()
        try:
            manager = TokenManagerService(db)
            db_token = manager.get_analytics_token()
            if db_token and db_token != self.access_token:
                logger.info("Found newer Analytics Token in database.")
                self.access_token = db_token
                return True
        finally:
            db.close()

        logger.error("UpstoxClient: Token refresh failed. Analytics Token may be expired.")
        return False
    
    async def _get_historical_data_single(
        self,
        symbol: str,
        instrument_key: str,
        from_date: datetime,
        to_date: datetime,
        interval: str
    ) -> pd.DataFrame:
        """Fetch historical data for a single date range chunk (<= 30 days)."""
        await self.rate_limiter.acquire()
        
        # Upstox API endpoint for historical data
        # Historical candle uses path parameters, so we must manually encode the key
        encoded_key = urllib.parse.quote(instrument_key, safe='')
        endpoint = f"/historical-candle/{encoded_key}/{interval}/{to_date.strftime('%Y-%m-%d')}/{from_date.strftime('%Y-%m-%d')}"
        
        try:
            data = await self._make_request("GET", endpoint)
            
            if data.get("status") != "success" or not data.get("data", {}).get("candles"):
                logger.info(f"No data for {symbol} from {from_date} to {to_date}")
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
            logger.error(f"Error fetching historical data for {symbol} in chunk: {e}")
            return pd.DataFrame()

    async def get_historical_data(
        self,
        symbol: str,
        instrument_key: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = "1minute"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from Upstox. Supporting automatic chunking/pagination
        for short intervals like 1minute to avoid Upstox 30-day range limits.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            instrument_key: Upstox instrument key (e.g., "NSE_EQ|INE002A01018")
            from_date: Start date
            to_date: End date
            interval: Candle interval (1minute, 30minute, day, etc.)
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        from datetime import timedelta
        
        max_chunk_days = 30
        is_sub_day = interval in ("1minute", "3minute", "5minute", "10minute", "15minute", "30minute", "60minute", "1hour")
        
        if is_sub_day and (to_date - from_date).days > max_chunk_days:
            chunks = []
            current_to = to_date
            while current_to > from_date:
                current_from = max(from_date, current_to - timedelta(days=max_chunk_days))
                chunks.append((current_from, current_to))
                current_to = current_from - timedelta(days=1)
                
            all_dfs = []
            # Fetch in order from oldest to newest chunk to preserve correct alignment/ordering
            for chunk_from, chunk_to in reversed(chunks):
                chunk_df = await self._get_historical_data_single(
                    symbol=symbol,
                    instrument_key=instrument_key,
                    from_date=chunk_from,
                    to_date=chunk_to,
                    interval=interval
                )
                if not chunk_df.empty:
                    all_dfs.append(chunk_df)
                    
            if not all_dfs:
                return pd.DataFrame()
                
            combined_df = pd.concat(all_dfs, ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
            return combined_df
            
        # Standard single request
        return await self._get_historical_data_single(
            symbol=symbol,
            instrument_key=instrument_key,
            from_date=from_date,
            to_date=to_date,
            interval=interval
        )
    
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
            
        await self.rate_limiter.acquire()
        
        params = {"instrument_key": ",".join(instrument_keys)}
        endpoint = "/market-quote/quotes"
        
        try:
            data = await self._make_request("GET", endpoint, params=params)
            
            results = {}
            if data.get("status") == "success" and data.get("data"):
                # Create a mapping for key normalization
                # If we requested NSE_EQ|RELIANCE, but got NSE_EQ:RELIANCE, 
                # we want to map it back to the requested key.
                requested_keys_map = {}
                for rk in instrument_keys:
                    requested_keys_map[rk] = rk
                    # Also map variants
                    if "|" in rk:
                        requested_keys_map[rk.replace("|", ":")] = rk
                    elif ":" in rk:
                        requested_keys_map[rk.replace(":", "|")] = rk

                for key, quote_data in data["data"].items():
                    # Resolve to the requested key if possible
                    final_key = requested_keys_map.get(key, key)
                    
                    ltp = quote_data.get("last_price", 0)
                    net_change = quote_data.get("net_change", 0)
                    change_pct = quote_data.get("percentage_change", 0)
                    
                    # Calculate previous close accurately:
                    # 1. Try "previous_close" from API response
                    # 2. Try to derive from ltp and net_change: prev_close = ltp - net_change
                    # 3. Fallback to ohlc close
                    prev_close = quote_data.get("previous_close")
                    if not prev_close or prev_close == 0:
                        if net_change is not None:
                            try:
                                prev_close = float(ltp) - float(net_change)
                            except Exception:
                                pass
                        if not prev_close or prev_close == 0:
                            prev_close = quote_data.get("ohlc", {}).get("close", 0)
                    
                    if not change_pct and prev_close and prev_close > 0:
                        change_pct = ((ltp - prev_close) / prev_close) * 100
                    
                    # Fallback: Calculate from net_change if percent is missing
                    if (not change_pct or change_pct == 0) and net_change and ltp:
                        try:
                            nc = float(net_change)
                            lp = float(ltp)
                            if nc != 0 and lp != 0:
                                implied_prev = lp - nc
                                if implied_prev > 0:
                                    change_pct = (nc / implied_prev) * 100
                        except Exception:
                            pass
                    
                    results[final_key] = {
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
            logger.error(f"Error fetching batch live quotes: {e}")
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
        await self.rate_limiter.acquire()
        
        params = {"instrument_key": instrument_key}
        endpoint = "/market-quote/quotes"
        
        try:
            data = await self._make_request("GET", endpoint, params=params)
            
            if data.get("status") == "success" and data.get("data"):
                # Extract the quote (key might vary)
                quote_data = next(iter(data["data"].values()))
                
                ltp = quote_data.get("last_price", 0)
                ohlc = quote_data.get("ohlc", {})
                net_change = quote_data.get("net_change", 0)
                change_pct = quote_data.get("percentage_change", 0)
                
                # Get previous close - try multiple sources
                prev_close = quote_data.get("previous_close")
                if not prev_close or prev_close == 0:
                    if net_change is not None:
                        try:
                            prev_close = float(ltp) - float(net_change)
                        except Exception:
                            pass
                    if not prev_close or prev_close == 0:
                        # Fallback to OHLC close (previous day's closing price)
                        prev_close = ohlc.get("close", 0)
                
                # If percentage_change is missing/zero but we have net_change, calculate it
                if (not change_pct or change_pct == 0) and net_change and prev_close and prev_close > 0:
                    # Calculate from net_change: percent = (net_change / (ltp - net_change)) * 100
                    actual_prev = ltp - net_change
                    if actual_prev > 0:
                        change_pct = (net_change / actual_prev) * 100
                
                # Last resort: calculate from ltp and prev_close
                if (not change_pct or change_pct == 0) and prev_close and prev_close > 0:
                    change_pct = ((ltp - prev_close) / prev_close) * 100
                    net_change = ltp - prev_close
                
                return {
                    "symbol": symbol,
                    "timestamp": datetime.now(),
                    "open": ohlc.get("open"),
                    "high": ohlc.get("high"),
                    "low": ohlc.get("low"),
                    "close": ohlc.get("close"),
                    "last_price": ltp,
                    "previous_close": prev_close,
                    "net_change": net_change,
                    "change_percent": change_pct,
                    "volume": quote_data.get("volume"),
                }
            
            return None

            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Token expired
                pass
            return None
        except Exception as e:
            logger.error(f"Error fetching live quote for {symbol}: {e}")
            return None

    async def get_option_chain(self, instrument_key: str, expiry_date: str = "") -> Optional[Dict]:
        """
        Fetch option chain data for F&O stocks from Upstox.
        
        Args:
            instrument_key: Upstox instrument key (e.g., "NSE_EQ|INE002A01018")
            expiry_date: Optional expiry date (YYYY-MM-DD). If empty, uses nearest expiry.
            
        Returns:
            Dict with {total_call_oi, total_put_oi, pcr, num_strikes, expiry} or None on failure.
        """
        await self.rate_limiter.acquire()

        if not expiry_date:
            try:
                contracts_data = await self._make_request("GET", "/option/contract", params={"instrument_key": instrument_key})
                if contracts_data.get("status") == "success" and contracts_data.get("data"):
                    contracts = contracts_data["data"]
                    unique_expiries = sorted(list(set(c.get("expiry") for c in contracts if c.get("expiry"))))
                    if unique_expiries:
                        expiry_date = unique_expiries[0]
                        logger.info(f"[get_option_chain] Resolved nearest expiry for {instrument_key}: {expiry_date}")
            except Exception as e:
                logger.error(f"[get_option_chain] Failed to automatically resolve nearest expiry for {instrument_key}: {e}")

        if not expiry_date:
            logger.warning(f"[get_option_chain] No active expiry found for {instrument_key}, option chain call skipped.")
            return None

        params = {"instrument_key": instrument_key, "expiry_date": expiry_date}
        endpoint = "/option/chain"

        try:
            data = await self._make_request("GET", endpoint, params=params)

            if data.get("status") != "success" or not data.get("data"):
                return None

            chain_data = data["data"]
            total_call_oi = 0
            total_put_oi = 0
            num_strikes = 0
            expiry = ""

            for strike in chain_data:
                call = strike.get("call_options", {})
                put = strike.get("put_options", {})

                call_oi = call.get("market_data", {}).get("oi", 0) or 0
                put_oi = put.get("market_data", {}).get("oi", 0) or 0

                total_call_oi += call_oi
                total_put_oi += put_oi
                num_strikes += 1

                if not expiry and strike.get("expiry"):
                    expiry = strike["expiry"]

            pcr = round(total_put_oi / total_call_oi, 4) if total_call_oi > 0 else None

            return {
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                "pcr": pcr,
                "num_strikes": num_strikes,
                "expiry": expiry,
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.debug(f"Option chain not available for {instrument_key} (403 — no F&O access)")
            else:
                logger.warning(f"Option chain error for {instrument_key}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error fetching option chain for {instrument_key}: {e}")
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
                logger.error(f"Error reading nifty200_instruments.json: {e}")
        
        # Fallback to Database query
        try:
            from sqlalchemy import create_engine, text
            from config import settings
            
            engine = create_engine(settings.SYNC_DATABASE_URL)
            with engine.connect() as conn:
                # Use instrument_master (new schema) instead of stock_master
                result = conn.execute(text("SELECT symbol, instrument_key FROM instrument_master WHERE is_active = TRUE LIMIT 200"))
                db_data = [(row.symbol, row.instrument_key) for row in result]
                
            if db_data:
                return db_data
        except Exception as e:
            logger.error(f"Error fetching symbols from DB fallback: {e}")

        # Final empty fallback - better than hardcoded stale data
        return []
    
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
            logger.info(f"Fetching {symbol} from {from_date.date()} to {to_date.date()}...")
            
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
        return await self._make_request("GET", "/user/profile")

    async def get_positions(self) -> List[Dict]:
        """Fetch all positions (short-term and long-term)"""
        await self.rate_limiter.acquire()
        # Fetch both and combine
        short_term = await self._make_request("GET", "/portfolio/short-term-positions")
        # long_term = await self._make_request("GET", "/portfolio/long-term-positions") # Optional depending on API
        
        positions = []
        if short_term.get("status") == "success":
            positions.extend(short_term.get("data", []))
            
        return positions

    async def get_holdings(self) -> List[Dict]:
        """Fetch holdings"""
        await self.rate_limiter.acquire()
        response = await self._make_request("GET", "/portfolio/long-term-holdings")
        if response.get("status") == "success":
            return response.get("data", [])
        return []

    async def get_orders(self) -> List[Dict]:
        """Fetch order book"""
        await self.rate_limiter.acquire()
        response = await self._make_request("GET", "/order/retrieve-all")
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
        
        return await self._make_request("POST", "/order/place", json=payload)

    async def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        await self.rate_limiter.acquire()
        return await self._make_request("DELETE", f"/order/cancel?order_id={order_id}")

    async def aclose(self):
        """Close the client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton instance
_upstox_client = None

def get_upstox_client(access_token: Optional[str] = None) -> UpstoxClient:
    """Get or create a singleton Upstox client instance"""
    global _upstox_client
    
    if _upstox_client is None:
        _upstox_client = UpstoxClient(access_token)
    
    return _upstox_client


def get_upstox_client_dependency() -> UpstoxClient:
    """FastAPI Dependency injector provider for UpstoxClient singleton."""
    return get_upstox_client()
