# Database Design & Schema

QuantAI India utilizes **PostgreSQL** as the primary relational database, supporting both asynchronous query execution (`asyncpg` for API requests) and synchronous connection pooling (`psycopg2` for Celery background tasks).

## Entity Relationship (ER) Summary

```
                      ┌──────────────────────┐
                      │        users         │
                      │  - id (PK)           │
                      │  - email             │
                      │  - username          │
                      │  - subscription_lvl  │
                      └──────────┬───────────┘
            ┌────────────────────┼───────────────────┐
            ▼                    ▼                   ▼
┌──────────────────────┐ ┌──────────────┐ ┌──────────────────────┐
│  saas_subscriptions  │ │  watchlist   │ │        orders        │
│  - user_id (FK)      │ │ - user_id(FK)│ │  - user_id (FK)      │
│  - plan_name         │ │ - symbol     │ │  - symbol            │
│  - status            │ └──────────────┘ │  - quantity, price   │
└──────────────────────┘                  └──────────────────────┘

                      ┌──────────────────────┐
                      │  instrument_master   │
                      │  - instrument_id (PK)│
                      │  - symbol (Index)    │
                      │  - sector            │
                      └──────────┬───────────┘
                                 │ (1-to-Many)
                                 ▼
                      ┌──────────────────────┐
                      │     stock_candle     │
                      │  - instrument_id (FK)│
                      │  - timeframe (PK)    │
                      │  - candle_ts (PK)    │
                      │  - OHLCV numeric     │
                      └──────────────────────┘
```

---

## Core Table Schemas

### 1. `instrument_master`
Contains the master reference list of all traded instruments. Used to resolve symbols to unique exchange instrument keys.
- `instrument_id` (BigInteger, Primary Key)
- `instrument_key` (String 100, Unique Index) - E.g. `NSE_EQ|RELIANCE`
- `symbol` (String 20, Index) - E.g. `RELIANCE`
- `series` (String 10) - E.g. `EQ`
- `exchange` (String 10) - E.g. `NSE`
- `company_name` (Text)
- `sector` (Text)
- `isin_code` (String 20)
- `is_active` (Boolean)
- *Constraints*: Unique constraint `uq_instrument` on `(symbol, series, exchange)`.

### 2. `stock_candle`
A massive, high-throughput table storing OHLCV candles across multiple timeframes.
- `instrument_id` (BigInteger, Foreign Key references `instrument_master`, Primary Key)
- `timeframe` (SmallInteger, Primary Key) - Minutes: 1, 5, 15, 30, 60, 1440 (Daily)
- `candle_ts` (DateTime, Primary Key) - UTC Timestamp
- `open` / `high` / `low` / `close` (Numeric 12, 4) - High-precision decimals
- `volume` (BigInteger)
- *Indexes*: Composite index `idx_candle_lookup` on `(instrument_id, timeframe, candle_ts)`.
- *Partitioning Strategy*: Monthly range partitioning based on `candle_ts` to keep indexes shallow and enable fast data purging.

### 3. `precomputed_indicators`
Stores technical indicators updated by daily cron jobs, avoiding on-demand calculation during screening.
- `symbol` (String 20, Primary Key)
- `interval` (String 10, Primary Key)
- `timestamp` (DateTime, Primary Key)
- `rsi_14` / `roc_10` / `roc_20` (Float)
- `macd` / `macd_signal` / `macd_histogram` (Float)
- `atr_14` / `adx_14` / `cci_20` (Float)
- `bollinger_h` / `bollinger_l` (Float)
- `momentum_score` (Float, Index)
- *Constraints*: Unique constraint `uq_indicator_symbol_interval_ts` on `(symbol, interval, timestamp)`.

### 4. `vcp_scores`
Persists Volatility Contraction Pattern metrics computed by background screening workers.
- `symbol` (String 20, Unique Index)
- `current_price` (Float)
- `vcp_score` (Float) - Volatility Contraction Score (0–100)
- `num_contractions` (Integer) - Number of visual contraction waves
- `latest_contraction_pct` (Float)
- `volume_dry_up_pct` (Float)
- `breakout_pivot` (Float)

### 5. `darvas_boxes`
Tracks consolidation ranges defined by Nicolas Darvas theory.
- `symbol` (String 20, Unique Index)
- `box_top` (Float) - Resistance ceiling
- `box_bottom` (Float) - Support floor
- `days_inside_box` (Integer)
- `breakout_status` (String 50) - E.g. `Inside Box`, `Bullish Breakout`

---

## Indexing & Partitioning Optimization
1. **Partition Pruning**: The `stock_candle` table is partitioned monthly on the `candle_ts` column. Query planner uses partition pruning to scan only the active month's partition when querying live intraday tickers.
2. **Composite Keys**: Composite primary key `(instrument_id, timeframe, candle_ts)` serves as a clustered index structure, optimizing range-scans (fetching a history of daily candles for a stock) so that data is physically ordered on disk by symbol and timestamp.
3. **Index Cleanup**: Standard b-tree indexes are set on foreign keys (`user_id`, `instrument_id`) to prevent table locks during cascades, and on frequently sorted metrics like `momentum_score` to optimize API sorting.
