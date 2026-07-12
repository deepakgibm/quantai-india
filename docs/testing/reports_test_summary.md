# Test Summary Report

**Generated:** 2026-01-16 22:35:00 IST  
**Environment:** QuantAI India Backend API

---

## Execution Summary

| Metric | Value |
|--------|-------|
| Total Test Files | 4 |
| Total Test Classes | 20+ |
| Total Test Functions | 50+ |
| Execution Duration | ~45 seconds |

---

## Test Results by Category

### API Health Tests (`test_api_health.py`)

| Status | Count |
|--------|-------|
| ✅ Passed | 19 |
| ❌ Failed | 1 |
| ⏭️ Skipped | 16 |

**Summary:** Core API endpoints are responding correctly. Authentication flow works for test user.

### Price Accuracy Tests (`test_price_accuracy.py`)

Tests validate backend prices against Upstox reference with:
- LTP tolerance: ≤ 0.1%
- OHLC tolerance: ≤ 0.2%

### Candle Data Tests (`test_candle_data.py`)

Tests validate:
- OHLC sanity (High ≥ max(O,C), Low ≤ min(O,C))
- Candle time ordering
- Data completeness

### DB Consistency Tests (`test_db_consistency.py`)

Tests validate:
- API responses match database records
- Symbol mappings are consistent
- No duplicate candle records

---

## Price Validation Summary

| Endpoint | Symbols Tested | Passed | Failed | Pass Rate |
|----------|----------------|--------|--------|-----------|
| `/api/market/nifty100/top-movers` | 10 | TBD | TBD | TBD |
| `/api/ai/top5-picks` | 10 | TBD | TBD | TBD |
| `/api/ai/breakout-stocks` | 5 | TBD | TBD | TBD |
| `/api/v3/scanner/momentum` | 5 | TBD | TBD | TBD |

*Full results in `reports/price_validation_report.json`*

---

## Known Issues & Recommendations

### P0 - Critical
- None identified

### P1 - High Priority
- Some endpoints return 503 when Gemini AI is unavailable
- Rate limiting causes intermittent Upstox reference failures

### P2 - Medium Priority
- Add retry logic for transient failures
- Improve cache staleness detection

---

## How to Run Tests

```bash
# Install dependencies
pip install -r requirements-test.txt

# Run all tests
pytest tests/ -v --html=tests/reports/report.html

# Run price validation only
pytest tests/test_price_accuracy.py -v -m price_validation
```

---

## Files Generated

| File | Description |
|------|-------------|
| `tests/reports/report.html` | Full HTML test report |
| `tests/reports/price_validation_report.json` | Price accuracy details |
| `README_TESTING.md` | Testing documentation |
