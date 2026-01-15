"""
QuantAI Stock Price Validator
Tests backend APIs and validates stock prices against yfinance (Google Finance source).

Features:
- API endpoint testing with status code, schema, and data validation
- Stock price comparison with configurable tolerance
- Company name to NSE ticker symbol mapping
- Rate limit handling with exponential backoff
- Detailed JSON and markdown report generation
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = "http://localhost:8000"
TIMEOUT = 30  # seconds
PRICE_TOLERANCE_PERCENT = 0.5  # ±0.5% tolerance for price comparison
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# =============================================================================
# Company Name to NSE Ticker Symbol Mapping
# This mapping converts company names (as returned by API) to NSE ticker symbols
# =============================================================================

COMPANY_TO_TICKER = {
    # Top 50 companies - most commonly traded
    "Reliance Industries Ltd": "RELIANCE",
    "Tata Consultancy Services Ltd": "TCS",
    "HDFC Bank Ltd": "HDFCBANK",
    "Infosys Ltd": "INFY",
    "ICICI Bank Ltd": "ICICIBANK",
    "Hindustan Unilever Ltd": "HINDUNILVR",
    "State Bank of India": "SBIN",
    "Bharti Airtel Ltd": "BHARTIARTL",
    "ITC Ltd": "ITC",
    "Kotak Mahindra Bank Ltd": "KOTAKBANK",
    "Axis Bank Ltd": "AXISBANK",
    "Larsen & Toubro Ltd": "LT",
    "Bajaj Finance Ltd": "BAJFINANCE",
    "Asian Paints Ltd": "ASIANPAINT",
    "Maruti Suzuki India Ltd": "MARUTI",
    "Titan Company Ltd": "TITAN",
    "Sun Pharmaceutical Industries Ltd": "SUNPHARMA",
    "HCL Technologies Ltd": "HCLTECH",
    "Wipro Ltd": "WIPRO",
    "Tata Steel Ltd": "TATASTEEL",
    "UltraTech Cement Ltd": "ULTRACEMCO",
    "Tech Mahindra Ltd": "TECHM",
    "NTPC Ltd": "NTPC",
    "Power Grid Corporation of India Ltd": "POWERGRID",
    "Mahindra & Mahindra Ltd": "M&M",
    "Bajaj Finserv Ltd": "BAJAJFINSV",
    "Nestle India Ltd": "NESTLEIND",
    "IndusInd Bank Ltd": "INDUSINDBK",
    "Tata Motors Passenger Vehicles Ltd": "TATAMOTORS",
    "Adani Enterprises Ltd": "ADANIENT",
    "Adani Ports and Special Economic Zone Ltd": "ADANIPORTS",
    "Cipla Ltd": "CIPLA",
    "Grasim Industries Ltd": "GRASIM",
    "Dr Reddy's Laboratories Ltd": "DRREDDY",
    "Britannia Industries Ltd": "BRITANNIA",
    "Coal India Ltd": "COALINDIA",
    "Eicher Motors Ltd": "EICHERMOT",
    "Hero MotoCorp Ltd": "HEROMOTOCO",
    "Oil & Natural Gas Corporation Ltd": "ONGC",
    "Bharat Petroleum Corporation Ltd": "BPCL",
    "Tata Consumer Products Ltd": "TATACONSUM",
    "Divi's Laboratories Ltd": "DIVISLAB",
    "Apollo Hospitals Enterprise Ltd": "APOLLOHOSP",
    "Hindalco Industries Ltd": "HINDALCO",
    "JSW Steel Ltd": "JSWSTEEL",
    "Tata Power Co Ltd": "TATAPOWER",
    "SBI Life Insurance Company Ltd": "SBILIFE",
    "HDFC Life Insurance Company Ltd": "HDFCLIFE",
    "Pidilite Industries Ltd": "PIDILITIND",
    
    # Additional companies from the data
    "360 ONE WAM Ltd": "360ONE",
    "3M India Ltd": "3MINDIA",
    "ABB India Ltd": "ABB",
    "ACC Ltd": "ACC",
    "Aadhar Housing Finance Ltd": "AADHARHFC",
    "Aarti Industries Ltd": "AARTIIND",
    "Aavas Financiers Ltd": "AAVAS",
    "Abbott India Ltd": "ABBOTINDIA",
    "Adani Energy Solutions Ltd": "ADANIENSOL",
    "Adani Green Energy Ltd": "ADANIGREEN",
    "Adani Power Ltd": "ADANIPOWER",
    "Adani Total Gas Ltd": "ATGL",
    "Aditya Birla Capital Ltd": "ABCAPITAL",
    "Aditya Birla Fashion and Retail Ltd": "ABFRL",
    "Ambuja Cements Ltd": "AMBUJACEM",
    "Bajaj Auto Ltd": "BAJAJ-AUTO",
    "Bank of Baroda": "BANKBARODA",
    "Bharat Electronics Ltd": "BEL",
    "Canara Bank": "CANBK",
    "Federal Bank Ltd": "FEDERALBNK",
    "GAIL (India) Ltd": "GAIL",
    "Godrej Consumer Products Ltd": "GODREJCP",
    "Havells India Ltd": "HAVELLS",
    "ICICI Lombard General Insurance Company Ltd": "ICICIGI",
    "ICICI Prudential Life Insurance Company Ltd": "ICICIPRULI",
    "Indian Oil Corporation Ltd": "IOC",
    "LTIMindtree Ltd": "LTIM",
    "Lupin Ltd": "LUPIN",
    "MRF Ltd": "MRF",
    "Marico Ltd": "MARICO",
    "Muthoot Finance Ltd": "MUTHOOTFIN",
    "Page Industries Ltd": "PAGEIND",
    "Punjab National Bank": "PNB",
    "REC Ltd": "RECLTD",
    "Shriram Finance Ltd": "SHRIRAMFIN",
    "Siemens Ltd": "SIEMENS",
    "TVS Motor Company Ltd": "TVSMOTOR",
    "Torrent Pharmaceuticals Ltd": "TORNTPHARM",
    "Trent Ltd": "TRENT",
    "UPL Ltd": "UPL",
    "Vedanta Ltd": "VEDL",
    "Voltas Ltd": "VOLTAS",
    "Yes Bank Ltd": "YESBANK",
    "Zee Entertainment Enterprises Ltd": "ZEEL",
    "Zydus Lifesciences Ltd": "ZYDUSLIFE",
}

# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ApiTestResult:
    """Result of an API test."""
    endpoint: str
    method: str
    status: str  # PASS, FAIL, TIMEOUT, ERROR
    status_code: Optional[int]
    response_time_ms: float
    error: Optional[str] = None
    response_data: Optional[Dict] = None


@dataclass
class PriceValidationResult:
    """Result of price comparison."""
    symbol: str
    ticker: str
    backend_price: Optional[float]
    external_price: Optional[float]
    difference_percent: Optional[float]
    status: str  # MATCH, MISMATCH, BACKEND_ERROR, EXTERNAL_ERROR, NO_MAPPING
    tolerance_percent: float
    backend_source: str
    external_source: str = "yfinance"


@dataclass
class TestReport:
    """Complete test report."""
    timestamp: str
    total_api_tests: int
    api_passed: int
    api_failed: int
    total_price_validations: int
    price_matches: int
    price_mismatches: int
    price_errors: int
    api_results: List[Dict]
    price_results: List[Dict]


# =============================================================================
# yFinance Price Fetcher
# =============================================================================

def get_yfinance_prices_batch(tickers: List[str]) -> Dict[str, Tuple[Optional[float], Optional[str]]]:
    """
    Fetch multiple stock prices from yfinance in batch.
    tickers should be NSE ticker symbols (without .NS suffix).
    """
    results = {}
    
    if not tickers:
        return results
    
    try:
        import yfinance as yf
        
        # Build ticker string with .NS suffix for NSE
        nse_tickers = [f"{t}.NS" for t in tickers]
        tickers_str = " ".join(nse_tickers)
        
        # Use session with User-Agent to avoid blocking
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0'
        })
        
        print(f"  Fetching {len(tickers)} tickers: {', '.join(tickers[:5])}...")
        
        # Fetch data
        data = yf.download(
            tickers_str, 
            period="1d", 
            interval="1d", 
            progress=False, 
            group_by='ticker',
            session=session
        )
        
        if data is None or data.empty:
            for ticker in tickers:
                results[ticker] = (None, "No data returned")
            return results
        
        # Extract prices
        for ticker in tickers:
            nse_ticker = f"{ticker}.NS"
            try:
                if len(tickers) > 1:
                    # Multi-ticker response
                    ticker_data = data[nse_ticker] if nse_ticker in data.columns.get_level_values(0) else None
                    if ticker_data is not None and not ticker_data.empty:
                        close_col = ticker_data['Close']
                        if hasattr(close_col, 'iloc'):
                            price = float(close_col.iloc[-1])
                        else:
                            price = float(close_col)
                        if price > 0:
                            results[ticker] = (round(price, 2), None)
                        else:
                            results[ticker] = (None, "Zero price")
                    else:
                        results[ticker] = (None, "Ticker not found")
                else:
                    # Single ticker response
                    if not data.empty:
                        price = float(data['Close'].iloc[-1])
                        if price > 0:
                            results[ticker] = (round(price, 2), None)
                        else:
                            results[ticker] = (None, "Zero price")
                    else:
                        results[ticker] = (None, "Empty data")
            except Exception as e:
                results[ticker] = (None, str(e)[:50])
        
        # Fill in any missing tickers
        for ticker in tickers:
            if ticker not in results:
                results[ticker] = (None, "Not in response")
        
    except ImportError:
        for ticker in tickers:
            results[ticker] = (None, "yfinance not installed")
    except Exception as e:
        for ticker in tickers:
            results[ticker] = (None, str(e)[:50])
    
    return results


# =============================================================================
# API Testing Functions
# =============================================================================

def test_endpoint(
    method: str, 
    path: str, 
    headers: Optional[Dict] = None,
    body: Optional[Dict] = None,
    expected_status: int = 200
) -> ApiTestResult:
    """Test a single API endpoint with retry logic."""
    
    url = f"{BASE_URL}{path}"
    result = ApiTestResult(
        endpoint=path,
        method=method,
        status="UNKNOWN",
        status_code=None,
        response_time_ms=0
    )
    
    for attempt in range(MAX_RETRIES):
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=TIMEOUT)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body or {}, timeout=TIMEOUT)
            else:
                response = requests.request(method, url, headers=headers, json=body, timeout=TIMEOUT)
            
            elapsed = (time.time() - start_time) * 1000
            result.response_time_ms = round(elapsed, 2)
            result.status_code = response.status_code
            
            # Handle rate limiting
            if response.status_code == 429:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                result.status = "RATE_LIMITED"
                result.error = "Rate limit exceeded"
                return result
            
            # Determine status
            if response.status_code == expected_status:
                result.status = "PASS"
                try:
                    result.response_data = response.json()
                except:
                    result.response_data = {"raw": response.text[:500]}
            elif response.status_code == 401:
                result.status = "AUTH_REQUIRED"
            elif response.status_code == 404:
                result.status = "NOT_FOUND"
            elif response.status_code == 422:
                result.status = "VALIDATION_ERROR"
            else:
                result.status = "FAIL"
                result.error = f"Expected {expected_status}, got {response.status_code}"
            
            return result
            
        except requests.exceptions.Timeout:
            result.status = "TIMEOUT"
            result.error = f"Request timed out after {TIMEOUT}s"
            result.response_time_ms = TIMEOUT * 1000
        except requests.exceptions.ConnectionError:
            result.status = "CONNECTION_ERROR"
            result.error = "Cannot connect to backend"
        except Exception as e:
            result.status = "ERROR"
            result.error = str(e)[:100]
        
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    
    return result


# =============================================================================
# Price Validation
# =============================================================================

def validate_prices(
    backend_data: List[Dict],  # List of {symbol: name, ltp: price}
    source_name: str
) -> List[PriceValidationResult]:
    """Compare backend prices with yfinance using company-to-ticker mapping."""
    
    results = []
    
    # First, map company names to tickers and collect prices to fetch
    tickers_to_fetch = []
    backend_by_ticker = {}
    
    for item in backend_data:
        company_name = item.get('symbol', '')
        ltp = item.get('ltp', 0)
        
        ticker = COMPANY_TO_TICKER.get(company_name)
        
        if ticker and ltp and ltp > 0:
            tickers_to_fetch.append(ticker)
            backend_by_ticker[ticker] = {'name': company_name, 'price': ltp}
    
    if not tickers_to_fetch:
        print("  ⚠️ No mappable symbols found")
        return results
    
    # Fetch prices from yfinance
    print(f"  Validating {len(tickers_to_fetch)} stocks with ticker mapping...")
    external_prices = get_yfinance_prices_batch(tickers_to_fetch)
    
    # Compare prices
    for ticker, backend_info in backend_by_ticker.items():
        ext_price, ext_error = external_prices.get(ticker, (None, "Not fetched"))
        backend_price = backend_info['price']
        company_name = backend_info['name']
        
        result = PriceValidationResult(
            symbol=company_name,
            ticker=ticker,
            backend_price=backend_price,
            external_price=ext_price,
            difference_percent=None,
            status="UNKNOWN",
            tolerance_percent=PRICE_TOLERANCE_PERCENT,
            backend_source=source_name
        )
        
        if ext_price is None:
            result.status = "EXTERNAL_ERROR"
        else:
            # Calculate difference
            diff_pct = abs((backend_price - ext_price) / ext_price) * 100
            result.difference_percent = round(diff_pct, 3)
            
            if diff_pct <= PRICE_TOLERANCE_PERCENT:
                result.status = "MATCH"
            else:
                result.status = "MISMATCH"
        
        results.append(result)
    
    return results


# =============================================================================
# Edge Case Tests
# =============================================================================

def test_edge_cases() -> List[ApiTestResult]:
    """Test error handling and edge cases."""
    
    results = []
    
    # Test 1: Invalid symbol - expect 404
    result = test_endpoint("GET", "/api/v3/scanner/symbol/INVALID_SYMBOL_XYZ", expected_status=404)
    result.endpoint = "/api/v3/scanner/symbol/{invalid}"
    if result.status_code == 404:
        result.status = "PASS"
    results.append(result)
    
    # Test 2: Health check
    result = test_endpoint("GET", "/health", expected_status=200)
    results.append(result)
    
    # Test 3: Ready check
    result = test_endpoint("GET", "/ready", expected_status=200)
    results.append(result)
    
    return results


# =============================================================================
# Main Test Runner
# =============================================================================

def run_full_test_suite() -> TestReport:
    """Run complete API testing and price validation suite."""
    
    print("=" * 70)
    print("QuantAI Stock Price Validator")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"Price Tolerance: ±{PRICE_TOLERANCE_PERCENT}%")
    print(f"Mappable Symbols: {len(COMPANY_TO_TICKER)}")
    print("=" * 70)
    
    api_results: List[ApiTestResult] = []
    price_results: List[PriceValidationResult] = []
    
    # ==========================================================================
    # Phase 1: Health Tests
    # ==========================================================================
    print("\n[Phase 1: Health Checks]")
    
    health_result = test_endpoint("GET", "/health")
    api_results.append(health_result)
    print(f"  {'✓' if health_result.status == 'PASS' else '✗'} Health: {health_result.status}")
    
    ready_result = test_endpoint("GET", "/ready")
    api_results.append(ready_result)
    print(f"  {'✓' if ready_result.status == 'PASS' else '✗'} Ready: {ready_result.status}")
    
    if health_result.status != "PASS":
        print("\n⚠️  Backend not responding. Aborting tests.")
        return create_report(api_results, price_results)
    
    # ==========================================================================
    # Phase 2: Stock Price API Tests
    # ==========================================================================
    print("\n[Phase 2: Stock Price APIs]")
    
    all_stock_data: List[Dict] = []
    
    # Test snapshots endpoint (main source of stock data)
    result = test_endpoint("GET", "/api/v3/scanner/snapshots")
    api_results.append(result)
    status_icon = "✓" if result.status == "PASS" else "✗"
    print(f"  {status_icon} Snapshots: {result.status} ({result.response_time_ms}ms)")
    
    if result.status == "PASS" and result.response_data:
        data = result.response_data.get('data', [])
        all_stock_data.extend(data)
        print(f"    → Found {len(data)} stocks")
    
    # Test top movers endpoint
    result = test_endpoint("GET", "/api/market/nifty100/top-movers")
    api_results.append(result)
    status_icon = "✓" if result.status == "PASS" else "✗"
    print(f"  {status_icon} Top Movers: {result.status} ({result.response_time_ms}ms)")
    
    # Test market indices
    result = test_endpoint("GET", "/api/trading/market-indices")
    api_results.append(result)
    status_icon = "✓" if result.status == "PASS" else "✗"
    print(f"  {status_icon} Market Indices: {result.status} ({result.response_time_ms}ms)")
    
    time.sleep(0.2)
    
    # ==========================================================================
    # Phase 3: Edge Case Tests
    # ==========================================================================
    print("\n[Phase 3: Edge Cases]")
    
    edge_results = test_edge_cases()
    for result in edge_results:
        api_results.append(result)
        status_icon = "✓" if result.status == "PASS" else "✗"
        print(f"  {status_icon} {result.endpoint}: {result.status}")
    
    # ==========================================================================
    # Phase 4: Price Validation Against yFinance
    # ==========================================================================
    print("\n[Phase 4: Price Validation vs yFinance]")
    
    if all_stock_data:
        # Limit to stocks that have mapping
        mapped_stocks = [s for s in all_stock_data if s.get('symbol') in COMPANY_TO_TICKER][:20]
        
        if mapped_stocks:
            print(f"  Found {len(mapped_stocks)} stocks with ticker mapping")
            validation_results = validate_prices(mapped_stocks, "backend_api")
            price_results.extend(validation_results)
            
            # Print summary
            matches = sum(1 for r in validation_results if r.status == "MATCH")
            mismatches = sum(1 for r in validation_results if r.status == "MISMATCH")
            errors = sum(1 for r in validation_results if r.status == "EXTERNAL_ERROR")
            
            print(f"\n  Results:")
            print(f"    ✓ Matches (within ±{PRICE_TOLERANCE_PERCENT}%): {matches}")
            print(f"    ⚠ Mismatches: {mismatches}")
            print(f"    ✗ Errors: {errors}")
            
            # Show details
            if mismatches > 0:
                print("\n  Mismatches:")
                for r in validation_results:
                    if r.status == "MISMATCH":
                        print(f"    • {r.ticker}: Backend=₹{r.backend_price}, yFinance=₹{r.external_price}, Diff={r.difference_percent}%")
            
            if matches > 0:
                print("\n  Matches:")
                for r in validation_results[:5]:  # Show first 5 matches
                    if r.status == "MATCH":
                        print(f"    ✓ {r.ticker}: ₹{r.backend_price} ≈ ₹{r.external_price} ({r.difference_percent}%)")
        else:
            print("  ⚠️ No stocks with ticker mapping found")
    else:
        print("  ⚠️ No stock data extracted from APIs")
    
    # ==========================================================================
    # Generate Report
    # ==========================================================================
    return create_report(api_results, price_results)


def create_report(
    api_results: List[ApiTestResult], 
    price_results: List[PriceValidationResult]
) -> TestReport:
    """Create test report from results."""
    
    api_passed = sum(1 for r in api_results if r.status == "PASS")
    api_failed = len(api_results) - api_passed
    
    price_matches = sum(1 for r in price_results if r.status == "MATCH")
    price_mismatches = sum(1 for r in price_results if r.status == "MISMATCH")
    price_errors = sum(1 for r in price_results if r.status in ["EXTERNAL_ERROR", "NO_MAPPING"])
    
    return TestReport(
        timestamp=datetime.now().isoformat(),
        total_api_tests=len(api_results),
        api_passed=api_passed,
        api_failed=api_failed,
        total_price_validations=len(price_results),
        price_matches=price_matches,
        price_mismatches=price_mismatches,
        price_errors=price_errors,
        api_results=[asdict(r) for r in api_results],
        price_results=[asdict(r) for r in price_results]
    )


def generate_markdown_report(report: TestReport) -> str:
    """Generate markdown report."""
    
    lines = [
        "# QuantAI Stock Price Validation Report",
        "",
        f"**Generated:** {report.timestamp}",
        f"**Backend URL:** {BASE_URL}",
        f"**Price Tolerance:** ±{PRICE_TOLERANCE_PERCENT}%",
        "",
        "## 📊 Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total API Tests | {report.total_api_tests} |",
        f"| ✅ API Passed | {report.api_passed} |",
        f"| ❌ API Failed | {report.api_failed} |",
        f"| Total Price Validations | {report.total_price_validations} |",
        f"| ✅ Price Matches | {report.price_matches} |",
        f"| ⚠️ Price Mismatches | {report.price_mismatches} |",
        f"| ❌ Price Errors | {report.price_errors} |",
        "",
    ]
    
    # Pass rates
    api_rate = (report.api_passed / report.total_api_tests * 100) if report.total_api_tests > 0 else 0
    lines.append(f"**API Pass Rate:** {api_rate:.1f}%")
    
    if report.total_price_validations > 0:
        price_rate = (report.price_matches / report.total_price_validations * 100)
        lines.append(f"**Price Match Rate:** {price_rate:.1f}%")
    
    lines.append("")
    
    # API Results
    lines.append("## 🔌 API Test Results")
    lines.append("")
    lines.append("| Endpoint | Status | Code | Time (ms) |")
    lines.append("|----------|--------|------|-----------|")
    
    for result in report.api_results:
        status_emoji = {"PASS": "✅", "FAIL": "❌", "TIMEOUT": "⏱️"}.get(result['status'], "⚠️")
        code = result.get('status_code') or 'N/A'
        time_ms = result.get('response_time_ms', 0)
        lines.append(f"| `{result['endpoint']}` | {status_emoji} {result['status']} | {code} | {time_ms} |")
    
    lines.append("")
    
    # Price Validation Results
    if report.price_results:
        lines.append("## 💰 Price Validation Results")
        lines.append("")
        lines.append("| Ticker | Company | Backend | yFinance | Diff % | Status |")
        lines.append("|--------|---------|---------|----------|--------|--------|")
        
        for result in report.price_results:
            status_emoji = {"MATCH": "✅", "MISMATCH": "⚠️"}.get(result['status'], "❌")
            backend = f"₹{result.get('backend_price')}" if result.get('backend_price') else 'N/A'
            external = f"₹{result.get('external_price')}" if result.get('external_price') else 'N/A'
            diff = f"{result.get('difference_percent')}%" if result.get('difference_percent') is not None else 'N/A'
            ticker = result.get('ticker', 'N/A')
            symbol = result.get('symbol', '')[:25]  # Truncate long names
            lines.append(f"| {ticker} | {symbol} | {backend} | {external} | {diff} | {status_emoji} |")
    
    lines.append("")
    
    # Recommendations
    lines.append("## 💡 Analysis")
    lines.append("")
    
    if report.price_matches > 0:
        lines.append(f"- ✅ **{report.price_matches} prices matched** within ±{PRICE_TOLERANCE_PERCENT}% tolerance")
    
    if report.price_mismatches > 0:
        lines.append(f"- ⚠️ **{report.price_mismatches} price mismatches** - may be due to:")
        lines.append("  - Real-time price fluctuations during market hours")
        lines.append("  - yfinance 15-min delay vs live backend data")
        lines.append("  - Different data source update timings")
    
    if api_rate >= 80:
        lines.append("- ✅ **API Health:** Backend is operating normally")
    
    return "\n".join(lines)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    try:
        report = run_full_test_suite()
        
        # Save JSON report
        json_path = "stock_price_validation_results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2)
        
        # Save Markdown report
        md_path = "stock_price_validation_report.md"
        md_content = generate_markdown_report(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        # Print summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"API Tests: {report.api_passed}/{report.total_api_tests} passed")
        print(f"Price Validations: {report.price_matches}/{report.total_price_validations} matched")
        print(f"\nReports saved:")
        print(f"  • {md_path}")
        print(f"  • {json_path}")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
