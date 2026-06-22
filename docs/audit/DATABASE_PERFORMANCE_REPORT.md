# Phase 8: DATABASE_PERFORMANCE_REPORT.md

Audit of PostgreSQL query execution plans and index utilization.

## 1. Table Size & Row Counts
- `intraday_candles`: 40,224,720 rows.
- `stock_candle_archive`: 245,393,561 rows.
- `stock_candle`: 2,091,305 rows.
- `instrument_master`: 9,357 rows.

---

## 2. Query Optimization (EXPLAIN ANALYZE)
- **Tuned Query**: Data freshness monitor `/api/metrics/freshness`.
- **Old Plan**: `JOIN instrument_master im ON sc.instrument_id = im.instrument_id GROUP BY sc.timeframe`.
- **Old Execution Time**: 28.27s (due to hash join on millions of timeseries rows).
- **New Plan**: `SELECT timeframe, COUNT(DISTINCT instrument_id) FROM stock_candle GROUP BY timeframe`.
- **New Execution Time**: 8.97s (no JOIN, index-only scan on primary key).

---

## 3. Recommended Indexing
- Create index on `stock_candle(instrument_id, timeframe)` for faster scanner calculations.
- Create index on `instrument_master(symbol)` for cached symbol resolutions.
