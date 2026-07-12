# Technical Memory: Performance Optimization

## 1. Request Deduplication
To prevent "thundering herd" problems on database connectors, the central `PriceService` implements an async queue mapper that resolves duplicate concurrent requests for the same symbol using a single fetch hook.

## 2. DB Indexing
EOD queries leverage clustered index keys:
*   `idx_stock_candle_symbol_date`: Covering `(symbol, date DESC)`.
*   `idx_precomputed_indicators_symbol_date`: Covering `(symbol, date DESC)`.

## 3. Cache Management
*   DragonflyDB maintains a fast quote store (TTL: 1-5s).
*   Celery Warmup: Background workers warm up active indexes cache at market pre-open.
