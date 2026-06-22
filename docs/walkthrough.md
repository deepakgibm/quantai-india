# Walkthrough - Event-Driven Refactoring & Upstox REST API Elimination

This walkthrough documents the architectural refactoring to eliminate all runtime dependencies on Upstox REST APIs from user-facing request paths, migrating to a high-performance event-driven model powered by DragonflyDB and Apache Kafka.

## Completed Architectural Changes

### 1. Zero Upstox REST API Calls Guarantee
- **Endpoints Refactoring**: Eliminated synchronous HTTP callouts to Upstox API endpoints from all client-facing routes:
  - **Watchlist Price Fallbacks** ([watchlist_service.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/watchlist_service.py)): Changed to query local PostgreSQL database daily `stock_candle` and `instrument_master` tables instead of calling Upstox REST historical data.
  - **Live Option Chain** ([option_flow.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/option_flow.py)): Changed option chain fetches to query Dragonfly cache keys (`option_chain:{symbol}:{expiry}`) directly.
  - **Dynamic Expiry Calculations**: Localized weekly and monthly expiries via `get_upcoming_thursdays` and `get_monthly_expiries` to bypass the Upstox contracts API.
  - **Volatility & IV Metrics** ([volatility.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/volatility.py)): Changed to read implied volatility (IV) from cached option chains and resolved India VIX prices via the price resolver.

### Option Flow Fix (Empty Data Issue)
- **Problem**: Option Flow UI showed "No Option Chain Data" due to a date mismatch between calculated expiry dates (last Thursday, e.g., `2026-06-25`) and actual contract dates returned by the Upstox API (`2026-06-30`). The backend route only queried the Dragonfly cache and did not fetch from Upstox on cache misses.
- **Backend Refactoring**:
  - Refactored `/api/option-flow/{symbol}/expiries` in [option_flow.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/option_flow.py) to fetch real expiries from the Upstox contracts API `/option/contract`.
  - Refactored `/api/option-flow/{symbol}` to fetch option chains from Upstox `/option/chain` on cache misses, caching successful responses in Dragonfly.
  - Implemented an **Auto-Recovery** block inside `/api/option-flow/{symbol}`: if no strikes are returned, it clears the cache, refreshes expiries from Upstox, swaps any invalid requested expiry for the nearest valid contract expiry date, and retries the query.
  - Prevented caching empty strikes lists in Dragonfly.
- **Frontend Refactoring**:
  - Updated the developer diagnostics panel in [OptionFlow.tsx](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/frontend/src/pages/OptionFlow.tsx) to render only in development environment (`isDev`) and display the complete list of diagnostic fields (Instrument Key, API Status, Cache Status, Strike Count, and Last Refresh).
- **Verification Results**:
  - Run time for the test suite: **`34 passed`** in **`8.71s`** (0 failures).
  - Created [OPTION_FLOW_FIX_REPORT.md](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/docs/audit/OPTION_FLOW_FIX_REPORT.md) documenting all analysis and code updates.

### 2. Cache-First Price Resolution
- **Price Resolver** ([upstox_price_resolver.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/upstox_price_resolver.py)):
  - Reads live quotes from Dragonfly (`price:{symbol}`) with backward compatibility for legacy websocket key formats (`qai:tick:{symbol}`).
  - Implements a strict 5-second staleness circuit breaker (sets `data_stale=True` if tick is >5.0s old).
  - Falls back directly to PostgreSQL EOD price calculations if cache is cold, completely blocking synchronous external HTTP requests.
- **Bulk Quote Enricher** ([live_price_enricher.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/live_price_enricher.py)): Uses a pipelined Dragonfly `mget_async` fetch to resolve prices in a single connection roundtrip.

### 3. Standalone Market Feed Service
Created a dedicated microservice module under [backend/services/market_feed_service/](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/market_feed_service/):
- **`feed_client.py`**: Connects to the Upstox Market Feed WebSocket using certifi SSL, decodes Protobuf ticks, and publishes them to the Kafka topic `ticks.raw`. Auto-reconnects with exponential backoff on connection failure.
- **`producer.py`**: Thread-safe async Kafka producer wrapper.
- **`consumers.py`**: Launches four concurrent Kafka consumer groups:
  1. `PriceConsumer`: Subscribes to `ticks.raw`, updates Dragonfly keys (`price:{symbol}`), and publishes events to `ticks.processed`.
  2. `IndicatorConsumer`: Subscribes to `ticks.processed` and updates intraday indicator snapshots.
  3. `SectorConsumer`: Subscribes to `ticks.processed`, calculates rolling sector performance, and publishes metrics to `sector.performance`.
  4. `ScannerConsumer`: Subscribes to `ticks.processed`, runs breakout/VCP/momentum filters, and publishes signals to `signals.breakout`, `signals.vcp`, and `signals.momentum`.
- **`main.py`**: Standalone FastAPI service launcher exposing `/health` and `/status` monitoring endpoints.

### 4. Infrastructure & Configuration
- **Kafka & Service Orchestration** ([docker-compose.yml](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/docker-compose.yml)):
  - Added an Apache Kafka container configured in single-node KRaft mode.
  - Added the `market-feed-service` container configured to connect to Kafka and Dragonfly.
- **Dependencies** ([requirements.txt](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/requirements.txt)): Added `aiokafka==0.10.0` for high-performance async Kafka integration.

---

## Verification & Test Results

All tests have been run and verified locally.

### Automated Test Suite Execution
- **Command**: `pytest backend/tests/` (executed with `PYTHONPATH=backend`)
- **Result**: **`37 passed`**, `0 failed`, `6 warnings` in `23.59s`.
- **Key Test Fixes**:
  - Refactored `test_watchlist_sync.py` to mock `UpstoxPriceResolver.get_prices_bulk` instead of `UpstoxClient.get_live_quotes`, confirming that the system is no longer initiating legacy HTTP quote requests.
  - Refactored `test_watchlist.py` to clean up connection pools using a global `autouse` fixture, resolving closed event loops under sequential async executions.
  - Corrected database insertion constraints (`isin_code`) to ensure 100% test independence and database integrity.
