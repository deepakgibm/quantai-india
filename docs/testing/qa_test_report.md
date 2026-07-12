# QuantAI API Test Report

**Run Timestamp:** 2026-02-01T18:53:36.302521+00:00

## Summary

| Metric | Value |
|--------|-------|
| Total Endpoints | 46 |
| Passed | 46 |
| Failed | 0 |
| Pass Rate | 100.0% |
| Avg Latency | 32.5ms |
| P95 Latency | 135.0ms |
| Endpoints > 2s | 0 |
| Price Verifications | 22/22 |

## Price Verification Results

| Endpoint | Symbol | App Price | Upstox Price | Deviation | Verdict |
|----------|--------|-----------|--------------|-----------|---------|
| `/api/trading/top-gainers` | INDIA VIX | ₹15.10 | ₹15.10 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/trading/top-gainers` | MEDANTA | ₹1120.10 | ₹1120.10 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/trading/top-gainers` | ANANTRAJ | ₹531.05 | ₹531.05 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/trading/top-gainers` | NETWEB | ₹3305.70 | ₹3305.70 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/trading/top-gainers` | AMBER | ₹5993.00 | ₹5993.00 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/hp/momentum` | BDL | ₹1384.10 | ₹1384.10 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/hp/momentum` | ABB | ₹5437.00 | ₹5437.00 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/hp/momentum` | ANGELONE | ₹2313.00 | ₹2313.00 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/hp/momentum` | GRSE | ₹2522.20 | ₹2522.20 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/hp/momentum` | BANKINDIA | ₹150.44 | ₹150.44 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/hp/breakout` | BDL | ₹1384.10 | ₹1384.10 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/hp/breakout` | ABB | ₹5437.00 | ₹5437.00 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/hp/breakout` | ANGELONE | ₹2313.00 | ₹2313.00 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/hp/breakout` | GRSE | ₹2522.20 | ₹2522.20 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/hp/breakout` | BANKINDIA | ₹150.44 | ₹150.44 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/ai/momentum` | ABB | ₹5437.00 | ₹5437.00 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/scanner/ai/vwap` | ABB | ₹5437.00 | ₹5437.00 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/market/top-movers` | INDIA VIX | ₹15.10 | ₹15.10 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/market/top-movers` | MEDANTA | ₹1120.10 | ₹1120.10 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/market/top-movers` | ANANTRAJ | ₹531.05 | ₹531.05 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/market/top-movers` | NETWEB | ₹3305.70 | ₹3305.70 | 0.00% | ✅ VERIFIED_REAL_PRICE |
| `/api/market/top-movers` | AMBER | ₹5993.00 | ₹5993.00 | 0.00% | ✅ VERIFIED_REAL_PRICE |

## All Endpoints

| # | Endpoint | Method | Status | Latency | Result |
|---|----------|--------|--------|---------|--------|
| 1 | `/` | GET | 200 | 4ms | ✅ |
| 2 | `/api/health/` | GET | 200 | 16ms | ✅ |
| 3 | `/api/health/ready` | GET | 200 | 3ms | ✅ |
| 4 | `/api/auth/signup` | POST | 200 | 13ms | ✅ |
| 5 | `/api/auth/login` | POST | 200 | 234ms | ✅ |
| 6 | `/api/auth/me` | GET | 200 | 34ms | ✅ |
| 7 | `/api/upstox/status` | GET | 200 | 7ms | ✅ |
| 8 | `/api/upstox/auth-url` | GET | 200 | 33ms | ✅ |
| 9 | `/api/upstox/user-profile` | GET | 200 | 29ms | ✅ |
| 10 | `/api/upstox/portfolio` | GET | 200 | 17ms | ✅ |
| 11 | `/api/upstox/positions` | GET | 200 | 23ms | ✅ |
| 12 | `/api/upstox/market-quote/ABB` | GET | 200 | 31ms | ✅ |
| 13 | `/api/trading/health` | GET | 200 | 7ms | ✅ |
| 14 | `/api/trading/market-indices` | GET | 200 | 8ms | ✅ |
| 15 | `/api/trading/instruments` | GET | 200 | 6ms | ✅ |
| 16 | `/api/trading/stats` | GET | 200 | 85ms | ✅ |
| 17 | `/api/trading/dashboard` | GET | 200 | 82ms | ✅ |
| 18 | `/api/trading/top-gainers` | GET | 200 | 36ms | ✅ |
| 19 | `/api/trading/gainers-losers` | GET | 200 | 13ms | ✅ |
| 20 | `/api/market/heatmap` | GET | 200 | 9ms | ✅ |
| 21 | `/api/market/sector/IT` | GET | 200 | 12ms | ✅ |
| 22 | `/api/ai/strategies` | GET | 200 | 10ms | ✅ |
| 23 | `/api/ai/market-analysis` | GET | 200 | 135ms | ✅ |
| 24 | `/api/ai/sentiment` | GET | 200 | 13ms | ✅ |
| 25 | `/api/ai/prompt` | POST | 200 | 43ms | ✅ |
| 26 | `/api/orders/` | GET | 200 | 13ms | ✅ |
| 27 | `/api/risk/` | GET | 200 | 17ms | ✅ |
| 28 | `/api/forecast/algorithms` | GET | 200 | 9ms | ✅ |
| 29 | `/api/forecast/predict` | GET | 200 | 188ms | ✅ |
| 30 | `/api/scanner/strategies` | GET | 200 | 3ms | ✅ |
| 31 | `/api/scanner/presets` | GET | 200 | 12ms | ✅ |
| 32 | `/api/scanner/hp/momentum` | GET | 200 | 19ms | ✅ |
| 33 | `/api/scanner/hp/breakout` | GET | 200 | 10ms | ✅ |
| 34 | `/api/scanner/ai/momentum` | GET | 200 | 123ms | ✅ |
| 35 | `/api/scanner/ai/vwap` | GET | 200 | 18ms | ✅ |
| 36 | `/api/market/top-movers` | GET | 200 | 4ms | ✅ |
| 37 | `/api/market/status` | GET | 200 | 5ms | ✅ |
| 38 | `/api/market/heatmap` | GET | 200 | 11ms | ✅ |
| 39 | `/api/market/sector/IT` | GET | 200 | 10ms | ✅ |
| 40 | `/api/analytics/overview` | GET | 200 | 9ms | ✅ |
| 41 | `/api/analytics/momentum/top` | GET | 200 | 23ms | ✅ |
| 42 | `/api/analytics/volatility/ABB` | GET | 200 | 19ms | ✅ |
| 43 | `/api/analytics/support-resistance/ABB` | GET | 200 | 23ms | ✅ |
| 44 | `/api/analytics/archive/list` | GET | 200 | 18ms | ✅ |
| 45 | `/api/analytics/archive/stats` | GET | 200 | 23ms | ✅ |
| 46 | `/api/analytics/indicators/latest/ABB` | GET | 200 | 35ms | ✅ |