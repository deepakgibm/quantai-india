# QuantAI Duplicate Logic Report

This report identifies duplicate implementations in the QuantAI codebase, detailing their locations, performance impacts, and recommended consolidations.

---

## 1. Technical Indicators Duplication

We identified multiple redundant implementations of core technical indicators:

### 1.1 Relative Strength Index (RSI)
*   **Locations**:
    1.  [backend/workers/indicator_worker.py:192](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/workers/indicator_worker.py#L192) — `_rsi(closes, period=14)`: Custom Wilder's smoothing calculation using lists and Python loops.
    2.  [backend/api/volume_profile.py:18](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/volume_profile.py#L18) — `calculate_rsi(closes, period=14)`: Standard list-based loop calculation.
    3.  [backend/api/sector_analysis.py:20](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/sector_analysis.py#L20) — `compute_rsi(prices, period=14)`: Custom NumPy implementation.
    4.  [backend/agents/research_agent.py:208](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/agents/research_agent.py#L208) — Inline calculation using Pandas Series diff/clip operations.
    5.  [backend/core/scanner/indicator_utils.py:21](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/core/scanner/indicator_utils.py#L21) — `rsi(close, period=14)`: Vectorized Pandas `ewm` calculation.
*   **Impact**: Inconsistent calculations. List-based smoothing slightly drifts from Pandas `ewm` calculations, leading to mismatched buy/sell signals between the scanner and charts.
*   **CPU/Memory Cost**: Loop-based Python implementations run at \(O(N)\) complexity and cannot release the GIL, blocking CPU cores during scanner runs.
*   **Recommended Consolidation**: Standardize all calculations on the vectorized `core.scanner.indicator_utils.rsi` implementation.

### 1.2 Moving Averages (EMA / SMA)
*   **Locations**:
    1.  [backend/workers/indicator_worker.py:179](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/workers/indicator_worker.py#L179) — `_ema(data, period)`: Loop-based multiplier calculation.
    2.  [backend/core/scanner/indicator_utils.py:11](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/core/scanner/indicator_utils.py#L11) — `sma()`, `ema()`: Vectorized Pandas `rolling()` and `ewm()` implementations.
    3.  [backend/api/sector_analysis.py:107](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/sector_analysis.py#L107) — Re-calculates 50 DMA and 200 DMA.
*   **Impact**: Slower execution times during batch scanner calculations.
*   **CPU/Memory Cost**: High CPU overhead due to O(N) loops running in Python instead of Pandas compiled C-backend.
*   **Recommended Consolidation**: Replace custom loops in `indicator_worker.py` with `core.scanner.indicator_utils` exports.

---

## 2. Backtesting Engine Duplication

The codebase contains four separate backtesting implementations:

### 2.1 Backtest Engines
*   **Locations**:
    1.  [backend/core/backtest/engine.py:134](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/core/backtest/engine.py#L134) — `class BacktestEngine`: Standard bar-by-bar loop engine.
    2.  [backend/services/backtest_engine.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/backtest_engine.py) — Duplicate implementation for legacy API compatibility.
    3.  [backend/experiment_lab/engine/backtest_runner.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/experiment_lab/engine/backtest_runner.py) — Custom runner used for parameter comparison in the Experiment Lab.
    4.  [backend/services/walk_forward_backtest_service.py:42](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/walk_forward_backtest_service.py#L42) — Custom simulator loop used for Walk-Forward Optimization (WFA).
*   **Impact**:
    *   *High Risk of Logic Drift*: Fixes in order filling, slippage models, transaction fee math, or stop-loss triggers must be updated in 4 separate locations.
    *   *Complex Maintenance*: Impossible to test and maintain strategies consistently.
*   **CPU/Memory Cost**: Every engine uses a custom loop that copies dataframes (`get_history(lookback=200)`) on every bar. This consumes significant CPU and memory.
*   **Recommended Consolidation**: Consolidate simulation logic under `core/backtest/engine.py`. Refactor the services and runners to act as wrappers around this core engine.

---

## 3. Caching Client Duplication

### 3.1 Caching Clients
*   **Locations**:
    1.  [backend/services/dragonfly_client.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/dragonfly_client.py) — `CacheManager`: Standard sync/async client supporting structured keys.
    2.  [backend/services/cache.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/cache.py) — `CacheManager`: Sync-only client mapping `quantai:*` hashed keys.
*   **Impact**:
    *   Double connection pool allocations to DragonflyDB/Redis, increasing connection overhead.
    *   Namespace fragmentation (makes it impossible to invalidate or evict keys consistently).
*   **CPU/Memory Cost**: Extra TCP handshake overhead and socket memory allocation.
*   **Recommended Consolidation**: Deprecate `backend/services/cache.py` and migrate all modules to `backend/services/dragonfly_client.py`.
