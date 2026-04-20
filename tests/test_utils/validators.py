"""
Validation Utilities
Helper functions for price comparison, schema validation, and data checks.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime


def compare_prices(
    actual: float,
    expected: float,
    tolerance: float = 0.001
) -> Tuple[bool, float, float]:
    """
    Compare two prices within a tolerance.
    
    Args:
        actual: Price from backend API
        expected: Reference price from Upstox
        tolerance: Allowed difference as decimal (0.001 = 0.1%)
        
    Returns:
        Tuple of (is_within_tolerance, absolute_diff, percentage_diff)
    """
    if expected == 0:
        return actual == 0, abs(actual), 0
    
    absolute_diff = abs(actual - expected)
    percentage_diff = absolute_diff / expected
    is_within_tolerance = percentage_diff <= tolerance
    
    return is_within_tolerance, absolute_diff, percentage_diff * 100


def validate_ohlc_sanity(ohlc: Dict[str, float]) -> Tuple[bool, List[str]]:
    """
    Validate OHLC data for sanity.
    
    Rules:
    - high >= max(open, close)
    - low <= min(open, close)
    - high >= low
    - All values should be positive
    
    Args:
        ohlc: Dict with open, high, low, close keys
        
    Returns:
        Tuple of (is_valid, list of errors)
    """
    errors = []
    
    o = ohlc.get("open", 0)
    h = ohlc.get("high", 0)
    l = ohlc.get("low", 0)
    c = ohlc.get("close", 0)
    
    # Check for positive values
    if any(v <= 0 for v in [o, h, l, c]):
        errors.append("All OHLC values must be positive")
    
    # High must be >= max(open, close)
    if h < max(o, c):
        errors.append(f"High ({h}) < max(Open, Close) ({max(o, c)})")
    
    # Low must be <= min(open, close)
    if l > min(o, c):
        errors.append(f"Low ({l}) > min(Open, Close) ({min(o, c)})")
    
    # High must be >= Low
    if h < l:
        errors.append(f"High ({h}) < Low ({l})")
    
    return len(errors) == 0, errors


def validate_timestamp_freshness(
    timestamp: str,
    max_age_minutes: int = 5,
    market_hours_only: bool = True
) -> Tuple[bool, float]:
    """
    Check if a timestamp is fresh (not stale).
    
    Args:
        timestamp: ISO format timestamp string
        max_age_minutes: Maximum age in minutes
        market_hours_only: If True, only check during market hours
        
    Returns:
        Tuple of (is_fresh, age_in_minutes)
    """
    try:
        # Parse timestamp (handle various formats)
        if "T" in timestamp:
            if "+" in timestamp:
                ts = datetime.fromisoformat(timestamp)
            else:
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            ts = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        
        # Make timezone-naive for comparison
        if ts.tzinfo:
            ts = ts.replace(tzinfo=None)
        
        now = datetime.now()
        age = now - ts
        age_minutes = age.total_seconds() / 60
        
        # During non-market hours, allow older data
        if market_hours_only:
            hour = now.hour
            if hour < 9 or hour >= 16:  # Outside 9 AM - 4 PM
                return True, age_minutes
        
        is_fresh = age_minutes <= max_age_minutes
        return is_fresh, age_minutes
        
    except Exception as e:
        return False, -1


def validate_response_schema(
    response: Dict[str, Any],
    required_keys: List[str],
    optional_keys: Optional[List[str]] = None
) -> Tuple[bool, List[str]]:
    """
    Validate response contains required keys.
    
    Args:
        response: API response dict
        required_keys: List of keys that must be present
        optional_keys: List of keys that may be present
        
    Returns:
        Tuple of (is_valid, list of missing keys)
    """
    missing = []
    
    for key in required_keys:
        if key not in response:
            missing.append(key)
    
    return len(missing) == 0, missing


def validate_data_types(
    data: Dict[str, Any],
    type_map: Dict[str, type]
) -> Tuple[bool, List[str]]:
    """
    Validate data types of response fields.
    
    Args:
        data: Response data dict
        type_map: Dict mapping field names to expected types
        
    Returns:
        Tuple of (is_valid, list of type errors)
    """
    errors = []
    
    for field, expected_type in type_map.items():
        if field in data:
            value = data[field]
            if value is not None and not isinstance(value, expected_type):
                # Allow int for float
                if expected_type == float and isinstance(value, (int, float)):
                    continue
                errors.append(f"{field}: expected {expected_type.__name__}, got {type(value).__name__}")
    
    return len(errors) == 0, errors


def validate_candle_ordering(candles: List[List[Any]]) -> Tuple[bool, List[str]]:
    """
    Validate candles are in correct time order.
    
    Args:
        candles: List of candles [timestamp, o, h, l, c, v, ...]
        
    Returns:
        Tuple of (is_valid, list of ordering errors)
    """
    errors = []
    
    if len(candles) < 2:
        return True, []
    
    prev_ts = None
    for i, candle in enumerate(candles):
        if len(candle) > 0:
            try:
                ts_str = candle[0]
                if isinstance(ts_str, str):
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                else:
                    ts = ts_str
                
                if prev_ts and ts >= prev_ts:
                    errors.append(f"Candle {i}: timestamp {ts} is not before previous {prev_ts}")
                
                prev_ts = ts
            except Exception as e:
                errors.append(f"Candle {i}: invalid timestamp format - {e}")
    
    return len(errors) == 0, errors


def extract_price_from_response(
    response: Dict[str, Any],
    data_path: str,
    price_field: str = "ltp"
) -> List[Dict[str, Any]]:
    """
    Extract price data from API response.
    
    Args:
        response: API response
        data_path: Path to data (e.g., "stocks", "gainers", "data")
        price_field: Field containing price
        
    Returns:
        List of dicts with symbol and price
    """
    results = []
    
    # Navigate to data path
    data = response
    for key in data_path.split("."):
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return results
    
    if not isinstance(data, list):
        return results
    
    for item in data:
        if isinstance(item, dict):
            symbol = item.get("symbol") or item.get("trading_symbol") or item.get("name")
            
            # Try multiple price field names
            price = None
            for field in [price_field, "ltp", "last_price", "close", "current_price", "price"]:
                if field in item and item[field] is not None:
                    price = item[field]
                    break
            
            if symbol and price is not None:
                results.append({
                    "symbol": symbol,
                    "price": price,
                    "change": item.get("change") or item.get("change_percent") or item.get("pct_change"),
                    "raw": item
                })
    
    return results


class PriceValidationResult:
    """Container for price validation results."""
    
    def __init__(
        self,
        api_endpoint: str,
        symbol: str,
        backend_price: float,
        reference_price: float,
        tolerance: float
    ):
        self.api_endpoint = api_endpoint
        self.symbol = symbol
        self.backend_price = backend_price
        self.reference_price = reference_price
        self.tolerance = tolerance
        
        self.is_valid, self.abs_diff, self.pct_diff = compare_prices(
            backend_price, reference_price, tolerance
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_endpoint": self.api_endpoint,
            "symbol": self.symbol,
            "backend_price": self.backend_price,
            "reference_price": self.reference_price,
            "absolute_difference": round(self.abs_diff, 4),
            "percentage_difference": round(self.pct_diff, 4),
            "tolerance": self.tolerance * 100,
            "passed": self.is_valid,
            "status": "PASS" if self.is_valid else "FAIL"
        }
    
    def __str__(self) -> str:
        status = "✓ PASS" if self.is_valid else "✗ FAIL"
        return (
            f"{status} | {self.symbol} | "
            f"Backend: {self.backend_price:.2f} | "
            f"Reference: {self.reference_price:.2f} | "
            f"Diff: {self.pct_diff:.4f}%"
        )


class TestReport:
    """Aggregate test results for reporting."""
    
    def __init__(self):
        self.results: List[PriceValidationResult] = []
        self.api_results: Dict[str, Dict[str, Any]] = {}
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
    
    def add_result(self, result: PriceValidationResult):
        self.results.append(result)
    
    def add_api_result(self, endpoint: str, status_code: int, passed: bool, error: Optional[str] = None):
        self.api_results[endpoint] = {
            "status_code": status_code,
            "passed": passed,
            "error": error
        }
    
    def finalize(self):
        self.end_time = datetime.now()
    
    def get_summary(self) -> Dict[str, Any]:
        self.finalize()
        
        passed = sum(1 for r in self.results if r.is_valid)
        failed = len(self.results) - passed
        
        api_passed = sum(1 for r in self.api_results.values() if r["passed"])
        api_failed = len(self.api_results) - api_passed
        
        return {
            "execution_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else 0
            },
            "api_health": {
                "total": len(self.api_results),
                "passed": api_passed,
                "failed": api_failed,
                "pass_rate": round(api_passed / len(self.api_results) * 100, 2) if self.api_results else 0
            },
            "price_validation": {
                "total": len(self.results),
                "passed": passed,
                "failed": failed,
                "pass_rate": round(passed / len(self.results) * 100, 2) if self.results else 0
            },
            "failures": [r.to_dict() for r in self.results if not r.is_valid]
        }
