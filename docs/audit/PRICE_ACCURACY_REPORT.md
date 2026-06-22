# Phase 5: PRICE_ACCURACY_REPORT.md

Verification of live prices displayed in the React client against PostgreSQL and Dragonfly cache sources.

## 1. Price Tracing Test Cases
We verified the current prices of active symbols:
- **Symbol**: `RELIANCE`
- **Cache Price (Dragonfly `price:RELIANCE`)**: Not set (cache miss)
- **Database EOD Fallback (Postgres `stock_candle`)**: 1336.40
- **API Response (`/api/market-quote/RELIANCE`)**: 1336.40
- **Frontend Card Render**: 1336.40
- **Accuracy**: 100% Match.

## 2. Root Cause Analysis (Stale Cache Fallback)
- **Problem**: In a cache miss scenario, or when the WebSocket feed is inactive, the price resolver defaults to EOD candles. If EOD tables are not seeded daily, this creates a price discrepancy between the actual live market price and the displayed UI price.
- **Remediation**:
  1. Implemented a strict 5-second staleness circuit breaker. If the cache key exists but is older than 5.0s, the price resolver sets `data_stale=True`.
  2. Set up pre-warming startup cache execution to seed active quotes.
  3. Ensure daily candle synchronizer executes daily during off-market hours.
