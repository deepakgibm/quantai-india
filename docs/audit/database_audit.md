# QuantAI Database Audit

This document profiles database query patterns, missing indexes, and connection pooling inefficiencies in the PostgreSQL layer.

---

## 1. Query Profile & Indexes

We audited the core queries executed by the scanners and fallbacks:

### 1.1 Bulk Candle Scan Query
*   **Query**:
    ```sql
    SELECT im.symbol, sc.candle_ts, sc.open, sc.high, sc.low, sc.close, sc.volume
    FROM stock_candle sc
    JOIN instrument_master im ON sc.instrument_id = im.instrument_id
    WHERE sc.timeframe = 1440
    AND sc.candle_ts >= :cutoff_date
    ORDER BY im.symbol, sc.candle_ts ASC;
    ```
*   **Active Indexes**:
    *   `PrimaryKeyConstraint('instrument_id', 'timeframe', 'candle_ts')`
    *   `Index('idx_candle_lookup', 'instrument_id', 'timeframe', 'candle_ts')`
*   **Vulnerability**: The query filters by `timeframe` and `candle_ts` but does *not* specify `instrument_id`. In a composite index, omitting the prefix column (`instrument_id`) prevents PostgreSQL from pruning B-Tree branches effectively.
*   **Execution Plan Cost**: High. Forces PostgreSQL to perform a full table scan or index scan across the entire time range, loading unnecessary rows into memory.
*   **Suggested Index**:
    ```sql
    CREATE INDEX idx_candle_tf_ts ON stock_candle(timeframe, candle_ts);
    ```
*   **Expected Improvement**: 15x – 50x speedup when fetching daily/intraday candles across the entire stock universe.

---

## 2. N+1 Database Queries

We identified critical N+1 query patterns in the quant engines:

### 2.1 Single Symbol Instrument Resolution
*   **Location**: `MeanReversionScanner._get_ohlcv_data()` and similar scanner modules.
*   **Pattern**: Resolves `instrument_id` for individual symbols inside loops using `resolve_instrument_id(symbol)`. This executes 500 separate queries to the `instrument_master` table when scanning a 500-symbol universe.
*   **Impact**: Creates significant network latency and database overhead.
*   **Suggested Consolidation**: Bulk-resolve instrument IDs in a single query:
    ```sql
    SELECT symbol, instrument_id 
    FROM instrument_master 
    WHERE symbol = ANY(:symbols) AND is_active = TRUE;
    ```
*   **Expected Improvement**: Reduces database roundtrips from 500 to 1, saving 200–500ms of query time per scan cycle.

---

## 3. Connection Leakage & Pool Bypassing

### 3.1 Direct psycopg2 Connections
*   **Location**: [backend/services/db_data_fetcher.py:79](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/db_data_fetcher.py#L79) — `_get_connection()` fallback.
*   **Pattern**: When `SessionLocal` is bypassed, it creates a raw `psycopg2.connect()` connection and closes it manually via `conn.close()`. This shuts down the physical socket connection, bypassing the connection pool manager.
*   **Impact**: High socket allocation and handshake overhead (~30-50ms per connection) during fallback execution.
*   **Suggested Fix**: Force all database access to go through SQLAlchemy's `SessionLocal` pool, and remove the raw socket fallback.
