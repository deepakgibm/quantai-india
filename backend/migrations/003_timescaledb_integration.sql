-- QuantAI Performance Optimization - Phase 3 SQL Migrations
-- TimescaleDB Integration for Optimized Time-Series Storage

-- ============================================
-- PREREQUISITES
-- ============================================
-- TimescaleDB must be installed on your PostgreSQL server
-- Install via: 
--   Ubuntu/Debian: apt install timescaledb-postgresql-14
--   Windows: Use TimescaleDB installer or Docker
--   Docker: docker run -d --name timescaledb -p 5432:5432 -e POSTGRES_PASSWORD=admin timescale/timescaledb:latest-pg14

-- ============================================
-- 1. Enable TimescaleDB Extension
-- ============================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================
-- 2. Convert stock_data to Hypertable
-- ============================================
-- NOTE: This requires the table to have a proper timestamp column
-- and no unique constraints that span across chunks

-- First, create a new table with TimescaleDB-compatible structure
CREATE TABLE IF NOT EXISTS stock_data_ts (
    id SERIAL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT NOT NULL,
    interval VARCHAR(10) NOT NULL DEFAULT '1min',
    source VARCHAR(20) NOT NULL DEFAULT 'upstox',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable (chunks by week for optimal query performance)
SELECT create_hypertable(
    'stock_data_ts', 
    'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ============================================
-- 3. Create Optimized Indexes for Hypertable
-- ============================================

-- Primary lookup pattern: symbol + time range
CREATE INDEX IF NOT EXISTS idx_ts_symbol_time 
ON stock_data_ts (symbol, timestamp DESC);

-- Multi-timeframe queries
CREATE INDEX IF NOT EXISTS idx_ts_symbol_interval_time 
ON stock_data_ts (symbol, interval, timestamp DESC);

-- ============================================
-- 4. Enable Compression (for data older than 7 days)
-- ============================================

ALTER TABLE stock_data_ts SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, interval',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Add compression policy: compress chunks older than 7 days
SELECT add_compression_policy('stock_data_ts', INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================
-- 5. Create Continuous Aggregates for Common Queries
-- ============================================

-- Daily OHLCV aggregates (for fast dashboard queries)
CREATE MATERIALIZED VIEW IF NOT EXISTS stock_data_daily
WITH (timescaledb.continuous) AS
SELECT
    symbol,
    time_bucket('1 day', timestamp) AS bucket,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM stock_data_ts
WHERE interval = '1min'
GROUP BY symbol, bucket
WITH NO DATA;

-- Hourly aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS stock_data_hourly
WITH (timescaledb.continuous) AS
SELECT
    symbol,
    time_bucket('1 hour', timestamp) AS bucket,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM stock_data_ts
WHERE interval = '1min'
GROUP BY symbol, bucket
WITH NO DATA;

-- Add refresh policies for continuous aggregates
SELECT add_continuous_aggregate_policy('stock_data_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy('stock_data_hourly',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '10 minutes',
    if_not_exists => TRUE
);

-- ============================================
-- 6. Data Retention Policy
-- ============================================
-- Automatically drop chunks older than 2 years (raw minute data)
-- Keep daily aggregates indefinitely

SELECT add_retention_policy('stock_data_ts', INTERVAL '2 years', if_not_exists => TRUE);

-- ============================================
-- 7. Migrate Data from stock_data to stock_data_ts
-- ============================================
-- UNCOMMENT AND RUN CAREFULLY DURING MAINTENANCE

-- INSERT INTO stock_data_ts (symbol, timestamp, open, high, low, close, volume, interval, source, created_at)
-- SELECT 
--     symbol, 
--     timestamp AT TIME ZONE 'Asia/Kolkata',
--     open, high, low, close, volume,
--     COALESCE(interval, '1min'),
--     COALESCE(source, 'upstox'),
--     COALESCE(created_at, NOW())
-- FROM stock_data;

-- ============================================
-- 8. Precomputed Indicators Hypertable (Optional)
-- ============================================

-- Convert indicators to hypertable for time-range queries
SELECT create_hypertable(
    'precomputed_indicators',
    'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- ============================================
-- Verification Queries
-- ============================================

-- Check hypertable info:
-- SELECT hypertable_name, num_chunks, compression_enabled 
-- FROM timescaledb_information.hypertables;

-- Check chunk sizes:
-- SELECT chunk_name, range_start, range_end, total_bytes
-- FROM timescaledb_information.chunks
-- WHERE hypertable_name = 'stock_data_ts'
-- ORDER BY range_start DESC;

-- Check compression stats:
-- SELECT * FROM hypertable_compression_stats('stock_data_ts');
