# Backend API Test Report

**Test Date**: 2026-01-12 23:25:00 IST (Market Closed)

---

## Test Summary

| Status | Count |
|--------|-------|
| ✅ PASSED | 7 |
| ❌ FAILED | 0 |

---

## Endpoint Test Results

### 1. Market Endpoints

| Endpoint | Status | Source | Notes |
|----------|--------|--------|-------|
| `/api/market/nifty100/top-movers` | ✅ PASS | `hp_scanner_cache` | Gainers/losers with LTP and change% |
| `/api/market/global-context` | ✅ PASS | `yfinance` | Dow Jones, S&P 500 data |

### 2. HP Scanner Endpoints (`/api/v3/scanner/*`)

| Endpoint | Status | Source | Latency | Notes |
|----------|--------|--------|---------|-------|
| `/momentum` | ✅ PASS | `MEMCACHED` | 2.46ms | Stocks with momentum signals |
| `/breakout` | ✅ PASS | `MEMCACHED` | 1.74ms | Breakout patterns detected |
| `/reversal` | ✅ PASS | `MEMCACHED` | 1.83ms | RSI oversold/overbought |
| `/signals` | ✅ PASS | `MEMCACHED` | 0.79ms | Combined strategy signals |

---

## Sample Data Verification

### Top Movers
```
Source: hp_scanner_cache
Data includes: symbol, ltp, prev_close, change_pct
Example: Adani Green - showing real market data
```

### HP Scanner Momentum
```
Latency: 2.46ms (target <50ms) ✅
Source: MEMCACHED
Indicators: SMA, EMA, MACD, RSI
```

### Global Context
```
Status: success
Indices: Dow Jones (^DJI)
Sentiment: Calculated from weighted indices
```

---

## Conclusion

All tested endpoints are:
- ✅ Returning real market data
- ✅ Using correct data sources (cache/snapshot)
- ✅ Meeting latency targets (<50ms)
- ✅ Properly indicating data source in response