# QuantAI Backend API Test Summary

**Test Date:** 2026-01-14 22:24:31
**Base URL:** http://localhost:8000

## 📊 Overall Summary

| Metric | Count |
|--------|-------|
| Total Tests | 56 |
| ✅ Passed | 29 |
| ❌ Failed | 1 |
| ⏱️ Timeout | 0 |
| 🔌 Connection Error | 0 |
| 🔒 Auth Required | 15 |
| ❓ Not Found | 11 |
| ⚠️ Validation Error | 0 |

**Pass Rate:** 51.8%

## 📁 Results by Category

| Category | Passed | Failed | Total | Pass Rate |
|----------|--------|--------|-------|-----------|
| Health & Status | 3 | 0 | 3 | 100% |
| Trading | 2 | 1 | 3 | 67% |
| AI Strategies | 10 | 1 | 11 | 91% |
| Scanner | 1 | 9 | 10 | 10% |
| HP Scanner v3 | 7 | 0 | 7 | 100% |
| Market | 5 | 1 | 6 | 83% |
| Heatmap | 0 | 1 | 1 | 0% |
| Upstox | 1 | 2 | 3 | 33% |
| Orders | 0 | 1 | 1 | 0% |
| Algorithms | 0 | 1 | 1 | 0% |
| Risk Management | 0 | 1 | 1 | 0% |
| Settings | 0 | 1 | 1 | 0% |
| User Config | 0 | 1 | 1 | 0% |
| Engines | 0 | 2 | 2 | 0% |
| Strategy Lab | 0 | 2 | 2 | 0% |
| Quant | 0 | 2 | 2 | 0% |
| Portfolio | 0 | 1 | 1 | 0% |

## 📋 Detailed Results


### Health & Status

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Root | GET | ✅ PASS | 200 | 16.76ms |
| Health Check | GET | ✅ PASS | 200 | 46.69ms |
| Readiness Check | GET | ✅ PASS | 200 | 8.06ms |

### Trading

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Trading Health | GET | ✅ PASS | 200 | 15.18ms |
| Market Indices | GET | ❌ FAIL | 500 | 6475.85ms |
| Instruments | GET | ✅ PASS | 200 | 26.77ms |

### AI Strategies

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Get AI Strategies | GET | 🔒 AUTH_REQUIRED | 401 | 7.19ms |
| Market Analysis | GET | ✅ PASS | 200 | 6348.54ms |
| Trend Finder | GET | ✅ PASS | 200 | 335.33ms |
| Breakout Stocks | GET | ✅ PASS | 200 | 1705.97ms |
| Top 5 Picks | GET | ✅ PASS | 200 | 11.79ms |
| Momentum Scanner | GET | ✅ PASS | 200 | 208.56ms |
| Mean Reversion | GET | ✅ PASS | 200 | 927.48ms |
| Gap Scanner | GET | ✅ PASS | 200 | 11.33ms |
| Relative Strength | GET | ✅ PASS | 200 | 9.93ms |
| VWAP Scanner | GET | ✅ PASS | 200 | 20.1ms |
| S/R Bounce | GET | ✅ PASS | 200 | 16.3ms |

### Scanner

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Get Strategies | GET | 🔒 AUTH_REQUIRED | 401 | 8.26ms |
| Get Indices | GET | 🔒 AUTH_REQUIRED | 401 | 17.73ms |
| Get Timeframes | GET | 🔒 AUTH_REQUIRED | 401 | 7.05ms |
| Presets | GET | 🔒 AUTH_REQUIRED | 401 | 5.91ms |
| Momentum Data | GET | 🔒 AUTH_REQUIRED | 401 | 9.08ms |
| Breakout Data | GET | ✅ PASS | 200 | 13125.59ms |
| Reversal Data | GET | 🔒 AUTH_REQUIRED | 401 | 8.06ms |
| TrendFinder Data | GET | 🔒 AUTH_REQUIRED | 401 | 13.38ms |
| 52-Week Breakouts | GET | ❓ NOT_FOUND | 404 | 5.94ms |
| Momentum Status | GET | ❓ NOT_FOUND | 404 | 5.75ms |

### HP Scanner v3

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Momentum | GET | ✅ PASS | 200 | 5.9ms |
| Breakout | GET | ✅ PASS | 200 | 10.12ms |
| Reversal | GET | ✅ PASS | 200 | 9.06ms |
| Signals | GET | ✅ PASS | 200 | 8.24ms |
| Snapshots | GET | ✅ PASS | 200 | 25.78ms |
| Status | GET | ✅ PASS | 200 | 13.34ms |
| Metrics | GET | ✅ PASS | 200 | 6.14ms |

### Market

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| NIFTY 100 Top Movers | GET | ✅ PASS | 200 | 4548.57ms |
| NIFTY 100 Status | GET | ✅ PASS | 200 | 5.71ms |
| Top Movers (Alias) | GET | ✅ PASS | 200 | 3656.57ms |
| Orchestrator Status | GET | ✅ PASS | 200 | 6.69ms |
| Market Health | GET | ✅ PASS | 200 | 50.36ms |
| Sector Heatmap | GET | ❓ NOT_FOUND | 404 | 25.47ms |

### Heatmap

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Get Sectors | GET | 🔒 AUTH_REQUIRED | 401 | 24.43ms |

### Upstox

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Status | GET | ✅ PASS | 200 | 5.04ms |
| User Profile | GET | 🔒 AUTH_REQUIRED | 401 | 6.12ms |
| Portfolio | GET | 🔒 AUTH_REQUIRED | 401 | 16.25ms |

### Orders

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Get Orders | GET | 🔒 AUTH_REQUIRED | 401 | 12.68ms |

### Algorithms

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Get Algorithms | GET | 🔒 AUTH_REQUIRED | 401 | 7.93ms |

### Risk Management

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Get Risk Settings | GET | 🔒 AUTH_REQUIRED | 401 | 6.63ms |

### Settings

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Get Settings | GET | 🔒 AUTH_REQUIRED | 401 | 7.46ms |

### User Config

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Get User Config | GET | ❓ NOT_FOUND | 404 | 6.37ms |

### Engines

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Analytics Engine Status | GET | ❓ NOT_FOUND | 404 | 7.39ms |
| Paper Trading Status | GET | ❓ NOT_FOUND | 404 | 5.28ms |

### Strategy Lab

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Get Strategies | GET | ❓ NOT_FOUND | 404 | 7.02ms |
| Strategy Status | GET | ❓ NOT_FOUND | 404 | 6.27ms |

### Quant

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Backtest Status | GET | ❓ NOT_FOUND | 404 | 6.26ms |
| ML Models | GET | ❓ NOT_FOUND | 404 | 7.65ms |

### Portfolio

| Endpoint | Method | Status | Code | Time |
|----------|--------|--------|------|------|
| Get Portfolio | GET | ❓ NOT_FOUND | 404 | 5.32ms |

## ⚠️ Failed/Error Endpoints

- **Market Indices** (`/api/trading/market-indices`)
  - Status: FAIL
- **52-Week Breakouts** (`/api/scanner/52week-breakouts`)
  - Status: NOT_FOUND
- **Momentum Status** (`/api/scanner/momentum-status`)
  - Status: NOT_FOUND
- **Sector Heatmap** (`/api/market/sector-heatmap`)
  - Status: NOT_FOUND
- **Get User Config** (`/api/user-config/`)
  - Status: NOT_FOUND
- **Analytics Engine Status** (`/api/engines/analytics/status`)
  - Status: NOT_FOUND
- **Paper Trading Status** (`/api/engines/paper-trading/status`)
  - Status: NOT_FOUND
- **Get Strategies** (`/api/strategy-lab/strategies`)
  - Status: NOT_FOUND
- **Strategy Status** (`/api/strategy-lab/status`)
  - Status: NOT_FOUND
- **Backtest Status** (`/api/quant/backtest/status`)
  - Status: NOT_FOUND
- **ML Models** (`/api/quant/ml/models`)
  - Status: NOT_FOUND
- **Get Portfolio** (`/api/portfolio/`)
  - Status: NOT_FOUND

## 💡 Recommendations

- 🔐 **Authentication Required**: Some endpoints require authentication. Consider testing with a valid JWT token.
- 🔍 **Not Found**: Some endpoints returned 404. Verify the API routes are correctly registered.
- ⚡ **Moderate Health**: Some endpoints are working but issues exist.