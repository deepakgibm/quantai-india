# QuantAI Transformation Plan

This document outlines the 12-month execution roadmap for refactoring the QuantAI codebase, prioritizing code-level fixes and compute isolation over premature infrastructure scaling.

---

## 1. Prioritized Roadmap

```
+-----------------------------------------------------------------------------+
| Q1: P0 Critical - Security & Logic Consolidation                           |
| Q2: P1 High     - Database & Compute Isolation                              |
| Q3: P2 Medium   - Frontend & UI Optimization                                |
| Q4: P3 Future   - Scaling Infrastructure (Only if traffic warrants)         |
+-----------------------------------------------------------------------------+
```

---

## 2. Phase-by-Phase Execution Details

### Phase P0: Security & Logic Consolidation (Months 1–3)
Focus on removing critical security risks and consolidating duplicate indicator and backtesting code.

*   **P0.1 CORS & SQL Injection Fixes**
    *   *Task*: Restrict wildcard CORS in `main.py` and parameterize features queries in `feature_store.py`.
    *   *Effort*: Low (1 day)
    *   *Risk*: Low
    *   *Performance Gain*: N/A (Security focus)
    *   *Business Impact*: Critical. Prevents database exploits and unauthorized access.
*   **P0.2 Consolidated Technical Indicators**
    *   *Task*: Deprecate custom loops in `workers/indicator_worker.py` and `api/volume_profile.py`. Standardize on vectorized indicators in `core/scanner/indicator_utils.py`.
    *   *Effort*: Medium (1 week)
    *   *Risk*: Medium (Requires verifying scanner output matches)
    *   *Performance Gain*: 3x – 5x speedup in computations.
    *   *Business Impact*: High. Ensures consistent signals across the platform.
*   **P0.3 Unified Backtest Engine**
    *   *Task*: Consolidate simulation logic under `core/backtest/engine.py`. Refactor legacy engines and WFA services to wrap this core logic.
    *   *Effort*: High (2–3 weeks)
    *   *Risk*: High (Requires regression testing backtest results)
    *   *Performance Gain*: Redundant code reduction (saves ~1,500 LOC).
    *   *Business Impact*: Critical. Simplifies maintenance and fixes logic drift.

### Phase P1: Database & Compute Isolation (Months 3–6)
Offload heavy compute from HTTP threads and optimize the PostgreSQL query engine.

*   **P1.1 Offload Scanners to Background Workers**
    *   *Task*: Deploy a task queue (Celery/RQ) to run scanner computations in a separate process. The API should only read pre-computed results from the DragonflyDB cache.
    *   *Effort*: Medium (2 weeks)
    *   *Risk*: Medium
    *   *Performance Gain*: Eliminates API timeout errors for scanner endpoints.
    *   *Business Impact*: High. Keeps the platform responsive.
*   **P1.2 PostgreSQL Index Optimization**
    *   *Task*: Apply composite indexes on `stock_candle(timeframe, candle_ts)` and `instrument_master(symbol)`.
    *   *Effort*: Low (2 days)
    *   *Risk*: Low
    *   *Performance Gain*: 10x – 50x query speedup.
    *   *Business Impact*: High. Speeds up historical data fetches.
*   **P1.3 Connection Pool Management**
    *   *Task*: Force `db_data_fetcher.py` and other services to use SQLAlchemy's `SessionLocal` pool, eliminating raw psycopg2 socket connections.
    *   *Effort*: Low (2 days)
    *   *Risk*: Low
    *   *Performance Gain*: Reduces DB connection handshake times by ~30ms.
    *   *Business Impact*: High. Prevents database connection exhaustion under load.

### Phase P2: Frontend & UI Optimization (Months 6–9)
Optimize rendering speeds and reduce JS bundle sizes on the client side.

*   **P2.1 Route-Based Code Splitting**
    *   *Task*: Use `React.lazy` and `Suspense` inside `App.tsx` to split the monolithic Vite bundle.
    *   *Effort*: Low (1 day)
    *   *Risk*: Low
    *   *Performance Gain*: First Contentful Paint (FCP) reduced from >3.0s to <1.5s.
    *   *Business Impact*: High. Improves initial loading speed for users.
*   **P2.2 State Management Migration (Zustand)**
    *   *Task*: Migrate high-frequency ticks and active watchlist data from React Context to Zustand stores to reduce re-renders.
    *   *Effort*: Medium (1–2 weeks)
    *   *Risk*: Medium
    *   *Performance Gain*: 50% reduction in CPU utilization on the client.
    *   *Business Impact*: Medium. Provides a smoother UI experience.

### Phase P3: Scaling Infrastructure (Future / Optional)
Introduce Kafka and ClickHouse only if user volume warrants the cost.

*   **P3.1 ClickHouse Analytical Data Store**
    *   *Task*: Migrate time-series candle queries from PostgreSQL to ClickHouse.
    *   *Effort*: High (1 month)
    *   *Risk*: High
    *   *Performance Gain*: Sub-second queries on 100M+ candles.
    *   *Business Impact*: Low until user base > 10,000 active quants.
*   **P3.2 Kafka Market Data Pipeline**
    *   *Task*: Set up a centralized Kafka streaming broker to decouple Upstox WebSocket ingestion.
    *   *Effort*: High (1 month)
    *   *Risk*: High
    *   *Performance Gain*: Decouples Upstox connection scaling limits.
    *   *Business Impact*: Low until concurrent WebSocket connections > 1,000.
