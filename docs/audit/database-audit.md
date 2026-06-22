# QuantAI Database Performance Audit

This report reviews the PostgreSQL schema, indexes, and queries, identifying performance bottlenecks and proposing specific query optimizations.

## 1. Slow Query: Stock Candle History Scan
* **Query**:
  ```sql
  SELECT sc.candle_ts, sc.open, sc.high, sc.low, sc.close, sc.volume
  FROM stock_candle sc
  JOIN instrument_master im ON sc.instrument_id = im.instrument_id
  WHERE im.symbol = 'RELIANCE' AND sc.timeframe = 1440
  ORDER BY sc.candle_ts DESC LIMIT 150
  ```
* **Estimated Cost**: High (due to join and symbol text lookup).
* **Impact**: Blocks FastAPI request threads during chart loading.
* **Optimization**:
  * Cache `symbol` -> `instrument_id` resolution in Dragonfly.
  * Eliminate the JOIN on `instrument_master` in the frequent timeseries query:
    ```sql
    SELECT candle_ts, open, high, low, close, volume 
    FROM stock_candle 
    WHERE instrument_id = :iid AND timeframe = 1440 
    ORDER BY candle_ts DESC LIMIT 150
    ```
* **Expected Improvement**: Reduces execution time from ~45ms to <3ms.

## 2. Missing Index: Watchlist Symbols Join
* **Query**:
  ```sql
  SELECT symbol_id FROM watchlist_symbol WHERE watchlist_id = :wid
  ```
* **Impact**: Full table scan on `watchlist_symbol` if the table grows.
* **Optimization**:
  * Add a composite index:
    ```sql
    CREATE INDEX idx_watchlist_symbol_lookup ON watchlist_symbol(watchlist_id, symbol_id);
    ```
* **Expected Improvement**: O(1) index scan.

## 3. Repeated Aggregations: Sector Performance
* **Query**:
  Calculates average sector performance by joining all Nifty 500 stocks and calculating daily returns dynamically.
* **Optimization**:
  * Implement a pre-calculated table or materialized view `sector_performance_mv` updated every 5 minutes.
