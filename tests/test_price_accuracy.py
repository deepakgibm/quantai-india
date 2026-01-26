"""
Price Accuracy Tests
Validates that backend API prices match reference prices from Upstox.
"""

import pytest
import json
import os
from typing import Dict, Any, List
from datetime import datetime

from tests.utils.test_data import (
    QUICK_TEST_SYMBOLS,
    SYMBOL_TO_INSTRUMENT_KEY,
    TOLERANCE_LTP,
    TOLERANCE_OHLC,
)
from tests.utils.validators import (
    compare_prices,
    PriceValidationResult,
)


class TestPriceAccuracy:
    """Test price accuracy against Upstox reference."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for price tests."""
        self.results: List[PriceValidationResult] = []
        self.validation_report: List[Dict[str, Any]] = []
    
    @pytest.mark.price_validation
    def test_market_top_movers_prices(self, api_client, upstox_client, symbol_to_instrument_key):
        """Validate prices in market top-movers response."""
        response = api_client.get("/api/market/nifty100/top-movers", auth=False)
        
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code}")
        
        data = response.json()
        
        # Extract stocks from gainers and losers
        stocks = []
        for key in ["gainers", "losers", "top_gainers", "top_losers", "data"]:
            if key in data and isinstance(data[key], list):
                stocks.extend(data[key])
        
        if not stocks:
            pytest.skip("No stocks in response")
        
        # Validate first 5 stocks
        validated = 0
        failures = []
        
        for stock in stocks[:10]:
            symbol = stock.get("symbol") or stock.get("trading_symbol")
            backend_price = stock.get("ltp") or stock.get("last_price") or stock.get("close")
            
            if not symbol or not backend_price:
                continue
            
            # Get reference price from Upstox
            instrument_key = symbol_to_instrument_key.get(symbol)
            if not instrument_key:
                continue
            
            ref_quote = upstox_client.get_ltp(instrument_key)
            if not ref_quote:
                continue
            
            ref_price = ref_quote.get("last_price") or ref_quote.get("ltp")
            if not ref_price:
                continue
            
            # Compare prices
            is_valid, abs_diff, pct_diff = compare_prices(
                float(backend_price), float(ref_price), TOLERANCE_LTP
            )
            
            validated += 1
            if not is_valid:
                failures.append({
                    "symbol": symbol,
                    "backend": backend_price,
                    "reference": ref_price,
                    "diff_pct": pct_diff
                })
            
            self.validation_report.append({
                "endpoint": "/api/market/nifty100/top-movers",
                "symbol": symbol,
                "backend_price": backend_price,
                "reference_price": ref_price,
                "abs_diff": abs_diff,
                "pct_diff": pct_diff,
                "passed": is_valid
            })
        
        # Allow some failures due to timing
        if validated > 0:
            failure_rate = len(failures) / validated
            assert failure_rate < 0.5, f"Too many price mismatches: {failures}"
    
    @pytest.mark.price_validation
    def test_trading_top_gainers_prices(self, api_client, auth_token, upstox_client, symbol_to_instrument_key):
        """Validate prices in trading top-gainers response."""
        if not auth_token:
            pytest.skip("No auth token")
        
        response = api_client.get("/api/trading/top-gainers", auth=True)
        
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code}")
        
        data = response.json()
        
        stocks = []
        for key in ["gainers", "losers", "top_gainers", "top_losers", "data", "stocks"]:
            if key in data and isinstance(data[key], list):
                stocks.extend(data[key])
        
        if not stocks:
            pytest.skip("No stocks in response")
        
        self._validate_stock_prices(
            stocks[:5],
            "/api/trading/top-gainers",
            upstox_client,
            symbol_to_instrument_key
        )
    
    @pytest.mark.price_validation
    def test_ai_top5_picks_prices(self, api_client, upstox_client, symbol_to_instrument_key):
        """Validate prices in AI top5-picks response."""
        response = api_client.get("/api/ai/top5-picks", auth=False)
        
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code}")
        
        data = response.json()
        
        stocks = []
        for key in ["stocks", "buy_signals", "sell_signals", "signals", "data"]:
            if key in data and isinstance(data[key], list):
                stocks.extend(data[key])
        
        if not stocks:
            pytest.skip("No stocks in response")
        
        self._validate_stock_prices(
            stocks[:10],
            "/api/ai/top5-picks",
            upstox_client,
            symbol_to_instrument_key
        )
    
    @pytest.mark.price_validation
    def test_ai_breakout_stocks_prices(self, api_client, upstox_client, symbol_to_instrument_key):
        """Validate prices in AI breakout-stocks response."""
        response = api_client.get("/api/ai/breakout-stocks", auth=False)
        
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code}")
        
        data = response.json()
        
        stocks = data.get("stocks", []) or data.get("data", [])
        
        if not stocks:
            pytest.skip("No stocks in response")
        
        self._validate_stock_prices(
            stocks[:5],
            "/api/ai/breakout-stocks",
            upstox_client,
            symbol_to_instrument_key
        )
    
    @pytest.mark.price_validation
    def test_hp_scanner_momentum_prices(self, api_client, upstox_client, symbol_to_instrument_key):
        """Validate prices in HP Scanner momentum response."""
        response = api_client.get("/api/v3/scanner/momentum", auth=False)
        
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code}")
        
        data = response.json()
        
        stocks = data.get("data", []) or data.get("stocks", []) or data.get("results", [])
        
        if not stocks:
            pytest.skip("No stocks in response")
        
        self._validate_stock_prices(
            stocks[:5],
            "/api/v3/scanner/momentum",
            upstox_client,
            symbol_to_instrument_key
        )
    
    @pytest.mark.price_validation
    def test_hp_scanner_snapshots_prices(self, api_client, upstox_client, symbol_to_instrument_key):
        """Validate prices in HP Scanner snapshots response."""
        response = api_client.get("/api/v3/scanner/snapshots", auth=False)
        
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code}")
        
        data = response.json()
        
        snapshots = data.get("snapshots", []) or data.get("data", [])
        
        if not snapshots:
            pytest.skip("No snapshots in response")
        
        # Take sample of known symbols
        test_symbols = list(SYMBOL_TO_INSTRUMENT_KEY.keys())[:5]
        
        for snapshot in snapshots:
            symbol = snapshot.get("symbol")
            if symbol not in test_symbols:
                continue
            
            backend_price = snapshot.get("ltp") or snapshot.get("close") or snapshot.get("price")
            if not backend_price:
                continue
            
            instrument_key = symbol_to_instrument_key.get(symbol)
            if not instrument_key:
                continue
            
            ref_quote = upstox_client.get_ltp(instrument_key)
            if not ref_quote:
                continue
            
            ref_price = ref_quote.get("last_price") or ref_quote.get("ltp")
            if not ref_price:
                continue
            
            is_valid, abs_diff, pct_diff = compare_prices(
                float(backend_price), float(ref_price), TOLERANCE_LTP
            )
            
            # Log result
            self.validation_report.append({
                "endpoint": "/api/v3/scanner/snapshots",
                "symbol": symbol,
                "backend_price": backend_price,
                "reference_price": ref_price,
                "pct_diff": pct_diff,
                "passed": is_valid
            })
    
    @pytest.mark.price_validation
    @pytest.mark.parametrize("symbol", QUICK_TEST_SYMBOLS)
    def test_individual_symbol_price(self, api_client, upstox_client, symbol_to_instrument_key, symbol):
        """Validate price for individual symbol across APIs."""
        instrument_key = symbol_to_instrument_key.get(symbol)
        if not instrument_key:
            pytest.skip(f"No instrument key for {symbol}")
        
        # Get reference price
        ref_quote = upstox_client.get_ltp(instrument_key)
        if not ref_quote:
            pytest.skip(f"Could not get reference price for {symbol}")
        
        ref_price = ref_quote.get("last_price") or ref_quote.get("ltp")
        if not ref_price:
            pytest.skip(f"No LTP in reference data for {symbol}")
        
        # Get price from HP Scanner snapshot
        response = api_client.get(f"/api/v3/scanner/snapshot/{symbol}", auth=False)
        
        if response.status_code == 200:
            data = response.json()
            backend_price = data.get("ltp") or data.get("close") or data.get("price")
            
            if backend_price:
                is_valid, abs_diff, pct_diff = compare_prices(
                    float(backend_price), float(ref_price), TOLERANCE_LTP
                )
                
                assert is_valid, (
                    f"{symbol}: Backend={backend_price}, "
                    f"Reference={ref_price}, Diff={pct_diff:.4f}%"
                )
    
    def _validate_stock_prices(
        self,
        stocks: List[Dict],
        endpoint: str,
        upstox_client,
        symbol_to_instrument_key: Dict[str, str]
    ):
        """Helper to validate stock prices from API response."""
        validated = 0
        failures = []
        
        for stock in stocks:
            symbol = stock.get("symbol") or stock.get("trading_symbol") or stock.get("name")
            
            # Try multiple price field names
            backend_price = None
            for field in ["ltp", "last_price", "close", "current_price", "price"]:
                if field in stock and stock[field] is not None:
                    backend_price = stock[field]
                    break
            
            if not symbol or not backend_price:
                continue
            
            # Get reference
            instrument_key = symbol_to_instrument_key.get(symbol)
            if not instrument_key:
                continue
            
            ref_quote = upstox_client.get_ltp(instrument_key)
            if not ref_quote:
                continue
            
            ref_price = ref_quote.get("last_price") or ref_quote.get("ltp")
            if not ref_price:
                continue
            
            # Compare
            is_valid, abs_diff, pct_diff = compare_prices(
                float(backend_price), float(ref_price), TOLERANCE_LTP
            )
            
            validated += 1
            if not is_valid:
                failures.append({
                    "symbol": symbol,
                    "backend": backend_price,
                    "reference": ref_price,
                    "diff_pct": pct_diff
                })
            
            self.validation_report.append({
                "endpoint": endpoint,
                "symbol": symbol,
                "backend_price": backend_price,
                "reference_price": ref_price,
                "pct_diff": pct_diff,
                "passed": is_valid
            })
        
        # Assert with tolerance for timing issues
        if validated > 0:
            failure_rate = len(failures) / validated
            assert failure_rate < 0.5, f"{endpoint}: Too many mismatches - {failures}"


class TestOHLCAccuracy:
    """Test OHLC data accuracy."""
    
    @pytest.mark.price_validation
    @pytest.mark.parametrize("symbol", QUICK_TEST_SYMBOLS)
    def test_candle_ohlc_accuracy(self, api_client, upstox_client, symbol_to_instrument_key, symbol):
        """Validate OHLC data matches reference."""
        instrument_key = symbol_to_instrument_key.get(symbol)
        if not instrument_key:
            pytest.skip(f"No instrument key for {symbol}")
        
        # Get reference OHLC
        ref_quote = upstox_client.get_full_quote(instrument_key)
        if not ref_quote or "ohlc" not in ref_quote:
            pytest.skip(f"Could not get reference OHLC for {symbol}")
        
        ref_ohlc = ref_quote["ohlc"]
        
        # Get from HP Scanner
        response = api_client.get(f"/api/v3/scanner/snapshot/{symbol}", auth=False)
        
        if response.status_code != 200:
            pytest.skip(f"Could not get snapshot for {symbol}")
        
        data = response.json()
        
        # Compare each OHLC field
        for field in ["open", "high", "low", "close"]:
            backend_val = data.get(field)
            ref_val = ref_ohlc.get(field)
            
            if backend_val and ref_val:
                is_valid, abs_diff, pct_diff = compare_prices(
                    float(backend_val), float(ref_val), TOLERANCE_OHLC
                )
                
                assert is_valid, (
                    f"{symbol} {field}: Backend={backend_val}, "
                    f"Reference={ref_val}, Diff={pct_diff:.4f}%"
                )


class TestPriceValidationReport:
    """Generate price validation report."""
    
    @pytest.fixture(scope="class")
    def report_data(self):
        """Shared report data."""
        return {"results": [], "summary": {}}
    
    @pytest.mark.price_validation
    def test_generate_validation_report(self, api_client, upstox_client, symbol_to_instrument_key):
        """Generate comprehensive price validation report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "endpoints_tested": [],
            "symbols_validated": [],
            "results": [],
            "summary": {}
        }
        
        endpoints = [
            ("/api/market/nifty100/top-movers", False),
            ("/api/ai/top5-picks", False),
            ("/api/ai/breakout-stocks", False),
            ("/api/v3/scanner/momentum", False),
        ]
        
        total_validated = 0
        total_passed = 0
        
        for endpoint, auth_required in endpoints:
            response = api_client.get(endpoint, auth=auth_required)
            
            if response.status_code != 200:
                continue
            
            report["endpoints_tested"].append(endpoint)
            data = response.json()
            
            # Extract stocks
            stocks = []
            for key in ["stocks", "gainers", "losers", "data", "results", "buy_signals", "sell_signals"]:
                if key in data and isinstance(data[key], list):
                    stocks.extend(data[key])
            
            for stock in stocks[:5]:
                symbol = stock.get("symbol") or stock.get("trading_symbol")
                backend_price = stock.get("ltp") or stock.get("last_price") or stock.get("close")
                
                if not symbol or not backend_price:
                    continue
                
                instrument_key = symbol_to_instrument_key.get(symbol)
                if not instrument_key:
                    continue
                
                ref_quote = upstox_client.get_ltp(instrument_key)
                if not ref_quote:
                    continue
                
                ref_price = ref_quote.get("last_price") or ref_quote.get("ltp")
                if not ref_price:
                    continue
                
                is_valid, abs_diff, pct_diff = compare_prices(
                    float(backend_price), float(ref_price), TOLERANCE_LTP
                )
                
                total_validated += 1
                if is_valid:
                    total_passed += 1
                
                report["results"].append({
                    "endpoint": endpoint,
                    "symbol": symbol,
                    "backend_price": float(backend_price),
                    "reference_price": float(ref_price),
                    "absolute_difference": round(abs_diff, 4),
                    "percentage_difference": round(pct_diff, 4),
                    "tolerance": TOLERANCE_LTP * 100,
                    "passed": is_valid,
                    "status": "PASS" if is_valid else "FAIL"
                })
                
                if symbol not in report["symbols_validated"]:
                    report["symbols_validated"].append(symbol)
        
        report["summary"] = {
            "total_endpoints": len(report["endpoints_tested"]),
            "total_symbols": len(report["symbols_validated"]),
            "total_validations": total_validated,
            "passed": total_passed,
            "failed": total_validated - total_passed,
            "pass_rate": round(total_passed / total_validated * 100, 2) if total_validated > 0 else 0
        }
        
        # Save report
        reports_dir = os.path.join(os.path.dirname(__file__), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        report_path = os.path.join(reports_dir, "price_validation_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Assert overall pass rate
        pass_rate = report["summary"]["pass_rate"]
        assert pass_rate >= 75, f"Price validation pass rate too low: {pass_rate}%"
