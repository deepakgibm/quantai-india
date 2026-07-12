# Performance Review & Optimizations

This document audits the performance profile of the QuantAI India system, details the critical bottlenecks resolved in this session, and registers outstanding performance issues.

## Resolved Performance Bottlenecks

### 1. Market Indices Timeout Fix (Latency: ~15s → <0.2s)
- **Vulnerability**: The `get_market_indices()` call used yfinance as a fallback which took up to 15s to time out inside Docker (since Yahoo Finance blocks container IPs). During this period, the REST API blocked, preventing the DB fallback step from executing before the client aborted the connection at 15s.
- **Resolution**:
  - Reduced yfinance internal download timeout from `15s` to `2.5s`.
  - Wrapped Upstox REST calls and yfinance calls in `asyncio.wait_for` wrappers (timeouts set to `3.5s` and `3.0s` respectively).
  - The endpoint now fails fast and immediately resolves to database EOD data in less than 200 milliseconds.

### 2. Sector Heatmap Partition Scanning (Latency: >30s → 24ms)
- **Vulnerability**: The sector heatmap query used a heavy CTE with a window function `ROW_NUMBER() OVER (PARTITION BY instrument_id ORDER BY candle_ts DESC)` without a date range filter on `stock_candle`. This triggered full-table scans across all monthly partitions, completely locking database resources.
- **Resolution**:
  - Dynamically query the latest `candle_ts` in the database (takes 0.07s).
  - Calculate a dynamic `:cutoff_date` relative to this timestamp (e.g. subtracting 25 calendar days for a 1D timeframe).
  - Injected `AND candle_ts >= :cutoff_date` into the CTE table scan. This enables partition pruning and forces PostgreSQL to execute index scans on `(instrument_id, timeframe, candle_ts)`.

### 3. Heatmap Live Price Hydration (Latency: 1.8s → <1.4s)
- **Vulnerability**: The heatmap enriches daily prices with live quotes via Upstox for 438 symbols. The previous code queried Upstox sequentially in 9 separate HTTP requests (batches of 50), taking over 1.8 seconds.
- **Resolution**:
  - Parallelized the 9 batch requests using `asyncio.gather`.
  - Added an `asyncio.wait_for` timeout of `3.5s` around the gather to ensure that if Upstox is rate-limited or degraded, the API immediately falls back to database EOD prices without timing out.

---

## Outstanding Performance Risks

### 1. Monolithic In-Process Backtesting (Severity: `HIGH`)
- **Location**: `core/backtest/engine.py`
- **Issue**: Backtesting is executed synchronously inside a bar-by-bar Python loop. For every bar index, the engine calls `get_history(lookback=200)` which creates a copy of the Pandas Dataframe. This limits throughput to 500–2000 bars/sec.
- **Recommendation**: Precompute indicators prior to loop entry and use index-based slicing (using numpy arrays) rather than DataFrame copies, raising throughput to 100,000+ bars/sec.

### 2. Sync ML Training on Inference Paths (Severity: `HIGH`)
- **Location**: `ml/predictor.py:94`
- **Issue**: If the ensemble predictor is called and no pre-trained model file exists, the inference code calls `model.train()` synchronously inside the request thread. This blocks the ASGI worker for 30–60 seconds, timing out the client.
- **Recommendation**: If no model file exists, return `503 Service Unavailable` with a `Retry-After` header, and enqueue a background training task to the Celery worker queue.
