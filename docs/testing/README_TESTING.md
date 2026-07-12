# QuantAI Backend API Testing Guide

## Overview

Comprehensive test suite for validating QuantAI India backend APIs, including:
- **API Health Tests**: Status codes, response schemas, latency
- **Price Accuracy Tests**: Validate prices against Upstox reference
- **Candle Data Tests**: OHLC sanity, ordering, completeness
- **DB Consistency Tests**: API vs PostgreSQL data matching

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements-test.txt
```

### 2. Configure Environment

Copy the example config and update with your values:

```bash
cp config/.env.example config/.env.test
```

Edit `config/.env.test`:
```env
BASE_URL=http://localhost:8000
TEST_USERNAME=testuser@quantai.in
TEST_PASSWORD=TestPass123!
UPSTOX_ACCESS_TOKEN=your_upstox_token_here
DATABASE_URL=postgresql://postgres:admin@localhost:5432/quantai
```

### 3. Run Tests

**Run all tests:**
```bash
pytest tests/ -v
```

**Run with HTML report:**
```bash
pytest tests/ --html=tests/reports/report.html --self-contained-html
```

**Run in parallel (faster):**
```bash
pytest tests/ -n auto --html=tests/reports/report.html
```

**Run specific test categories:**
```bash
# API Health tests only
pytest tests/test_api_health.py -v

# Price validation tests only
pytest tests/test_price_accuracy.py -v -m price_validation

# Skip slow tests
pytest tests/ -v -m "not slow"
```

## Test Categories

### API Health Tests (`test_api_health.py`)

| Test Class | Description |
|------------|-------------|
| `TestAPIHealth` | Root, health, ready endpoints |
| `TestPublicEndpoints` | All public (no auth) endpoints |
| `TestAuthenticatedEndpoints` | Auth-required endpoints |
| `TestOptionalAuthEndpoints` | Optional auth endpoints |
| `TestHPScannerEndpoints` | HP Scanner v3 endpoints |
| `TestResponseSchemas` | Response schema validation |
| `TestResponseTimes` | Latency checks |
| `TestErrorHandling` | Error handling validation |

### Price Accuracy Tests (`test_price_accuracy.py`)

| Test Class | Description |
|------------|-------------|
| `TestPriceAccuracy` | LTP comparison vs Upstox |
| `TestOHLCAccuracy` | OHLC data validation |
| `TestPriceValidationReport` | Generate price report |

**Tolerance Thresholds:**
- LTP: ≤ 0.1% difference
- OHLC: ≤ 0.2% difference

### Candle Data Tests (`test_candle_data.py`)

| Test Class | Description |
|------------|-------------|
| `TestCandleOHLCSanity` | High ≥ max(O,C), Low ≤ min(O,C) |
| `TestHistoricalCandles` | Historical data fetch |
| `TestCandleOrdering` | Time ordering validation |
| `TestCandleDataCompleteness` | Data gaps, volume presence |
| `TestCandleValueRanges` | Positive values, ranges |

### DB Consistency Tests (`test_db_consistency.py`)

| Test Class | Description |
|------------|-------------|
| `TestDatabaseConsistency` | API vs DB data matching |
| `TestCacheConsistency` | Cache vs source consistency |
| `TestDataIntegrity` | Symbol mappings, duplicates |

## Test Data

### Test Symbols (NIFTY 50 Subset)
```
RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, HDFC, SBIN, 
BHARTIARTL, KOTAKBANK, ITC, LT, AXISBANK, ASIANPAINT, 
MARUTI, SUNPHARMA, BAJFINANCE, TITAN, NESTLEIND, WIPRO, 
ULTRACEMCO, TECHM, HCLTECH, POWERGRID, ONGC, NTPC
```

### Quick Test Symbols (for fast runs)
```
RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK
```

## Reports

After running tests, reports are generated in `tests/reports/`:

| File | Description |
|------|-------------|
| `report.html` | Full HTML test report |
| `price_validation_report.json` | Price accuracy details |

## CI/CD Integration

```yaml
# Example GitHub Actions step
- name: Run API Tests
  run: |
    pip install -r requirements-test.txt
    pytest tests/ -v --junitxml=test-results.xml
```

## Troubleshooting

### Authentication Failures
- Ensure test user exists: Create via `/api/auth/signup`
- Check `TEST_USERNAME` and `TEST_PASSWORD` in config

### Upstox Reference Failures
- Verify `UPSTOX_ACCESS_TOKEN` is valid and not expired
- Check rate limiting (tests include delays)

### Database Connection Issues
- Ensure PostgreSQL is running
- Verify `DATABASE_URL` is correct
- Check firewall/network access

## Contributing

When adding new tests:
1. Follow existing patterns in test files
2. Use appropriate pytest markers (`@pytest.mark.price_validation`, etc.)
3. Add to relevant test class
4. Update this README if needed
