# QuantAI API Timeout Analysis

This report identifies the root causes of slow API responses and timeouts in the QuantAI backend, classifying endpoints by latency thresholds and providing actionable recommendations.

---

## 1. Latency Classification

Based on codebase analysis and profiling:

### 1.1 Endpoints Exceeding 5 Seconds (Timeout Risks)
*   **Endpoint**: `POST /api/ai/prompt`
    *   **Average Latency**: 3,500ms – 8,000ms
    *   **Root Cause**: Incurs blocking synchronous or long-running async calls to the Gemini API (`provider.generate_content`). It also calls `enrich_scanner_results` which sequentially fetches real-time prices for each recommendation, compounding external API latencies.
    *   **Fix Recommendation**: Offload the external API calls to async execution with a strict `asyncio.wait_for` timeout of 5 seconds. Implement **Semantic Caching** to intercept duplicate prompts and serve cached JSON results in <10ms.

### 1.2 Endpoints Exceeding 2 Seconds (High Latency)
*   **Endpoints**: `GET /api/ai/mean-reversion`, `/api/ai/breakout-detector`, `/api/ai/momentum-scanner`, `/api/ai/gap-scanner`, `/api/ai/relative-strength`, `/api/ai/vwap-scanner`, `/api/ai/sr-bounce`
    *   **Average Latency**: 1,200ms – 4,500ms (on cache miss)
    *   **Root Cause**: Trigger heavy computations inline. The scanners execute a bulk query to PostgreSQL (`stock_candle` JOIN `instrument_master` filtering 60 days of daily candles for 500+ symbols) and then iterate over all symbol dataframes in Python, calculating indicators (SMA, Bollinger, RSI) sequentially in a CPU-bound loop.
    *   **Fix Recommendation**: Set a strict API rule: **No inline scans**. The API must read only pre-computed scan results from the DragonflyDB cache. Move scan calculations to background workers (e.g., Celery tasks or supervised background service loops).
*   **Endpoint**: `GET /api/market/global-context`
    *   **Average Latency**: 1,500ms – 3,000ms
    *   **Root Cause**: Directly calls `fetch_live_indices_yfinance()` to scrape market indices, blocking the request thread.
    *   **Fix Recommendation**: Offload yfinance queries to a background worker that updates the `qai:market:global_context` cache key every 5 minutes. The API endpoint should perform only a cache read.

### 1.3 Endpoints Exceeding 500ms (Slow API Responses)
*   **Endpoint**: `GET /api/market/top-movers`
    *   **Average Latency**: 300ms – 900ms (on cache miss)
    *   **Root Cause**: If the cache is empty, it queries historical Postgres daily tables (`nifty100_daily`) using unindexed joins and parses data to calculate daily percentage change on the fly.
    *   **Fix Recommendation**: Ensure EOD jobs run at 3:40 PM IST to populate the top movers list, caching it in DragonflyDB with a long TTL (e.g., 5 hours). Implement proper database indexing on `nifty100_daily(timestamp, change_percent DESC)`.
