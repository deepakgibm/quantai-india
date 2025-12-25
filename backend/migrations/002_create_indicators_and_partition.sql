-- QuantAI Performance Optimization - Phase 2 SQL Migrations
-- Creates precomputed_indicators table and sets up partitioning

-- ============================================
-- 1. Create precomputed_indicators table
-- ============================================

CREATE TABLE IF NOT EXISTS precomputed_indicators (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL DEFAULT '1d',
    timestamp TIMESTAMP NOT NULL,
    
    -- Price context
    close DOUBLE PRECISION,
    volume INTEGER,
    
    -- Momentum Indicators
    rsi_14 DOUBLE PRECISION,
    roc_10 DOUBLE PRECISION,
    roc_20 DOUBLE PRECISION,
    macd DOUBLE PRECISION,
    macd_signal DOUBLE PRECISION,
    macd_histogram DOUBLE PRECISION,
    
    -- Volume Indicators
    mfi_14 DOUBLE PRECISION,
    vwap DOUBLE PRECISION,
    volume_sma_20 DOUBLE PRECISION,
    volume_ratio DOUBLE PRECISION,
    
    -- Volatility Indicators
    atr_14 DOUBLE PRECISION,
    bollinger_upper DOUBLE PRECISION,
    bollinger_mid DOUBLE PRECISION,
    bollinger_lower DOUBLE PRECISION,
    bollinger_pct DOUBLE PRECISION,
    
    -- Trend Indicators
    ema_9 DOUBLE PRECISION,
    ema_20 DOUBLE PRECISION,
    ema_50 DOUBLE PRECISION,
    sma_20 DOUBLE PRECISION,
    sma_50 DOUBLE PRECISION,
    trend_strength DOUBLE PRECISION,
    
    -- Composite Scores
    momentum_score DOUBLE PRECISION,
    volatility_score DOUBLE PRECISION,
    
    -- Metadata
    computed_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 2. Add optimized indexes for indicator lookups
-- ============================================

-- Primary lookup: symbol + interval + time range
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_indicators_symbol_interval_ts 
ON precomputed_indicators (symbol, interval, timestamp DESC);

-- Fast "latest" query per symbol
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_indicators_symbol_ts_desc 
ON precomputed_indicators (symbol, timestamp DESC);

-- Score-based queries (find top momentum stocks)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_indicators_momentum_score 
ON precomputed_indicators (momentum_score DESC NULLS LAST);

-- Uniqueness constraint for upserts
ALTER TABLE precomputed_indicators 
ADD CONSTRAINT uq_indicator_symbol_interval_ts 
UNIQUE (symbol, interval, timestamp);

-- ============================================
-- 3. Create indicator_compute_jobs table for tracking
-- ============================================

CREATE TABLE IF NOT EXISTS indicator_compute_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    symbols_count INTEGER,
    interval VARCHAR(10),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    
    symbols_processed INTEGER DEFAULT 0,
    rows_computed INTEGER DEFAULT 0,
    
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds DOUBLE PRECISION,
    
    error_message VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compute_job_status 
ON indicator_compute_jobs (status);

-- ============================================
-- 4. Table Partitioning for stock_data (Monthly)
-- ============================================
-- NOTE: This creates a NEW partitioned table. Data migration required.

-- Step 1: Create partitioned table structure
CREATE TABLE IF NOT EXISTS stock_data_partitioned (
    id SERIAL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume INTEGER NOT NULL,
    interval VARCHAR(10) NOT NULL DEFAULT '1min',
    source VARCHAR(20) NOT NULL DEFAULT 'upstox',
    created_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Step 2: Create partitions for recent months
-- Adjust dates as needed for your data range

CREATE TABLE IF NOT EXISTS stock_data_y2024m10 
PARTITION OF stock_data_partitioned 
FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');

CREATE TABLE IF NOT EXISTS stock_data_y2024m11 
PARTITION OF stock_data_partitioned 
FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');

CREATE TABLE IF NOT EXISTS stock_data_y2024m12 
PARTITION OF stock_data_partitioned 
FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

CREATE TABLE IF NOT EXISTS stock_data_y2025m01 
PARTITION OF stock_data_partitioned 
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE IF NOT EXISTS stock_data_y2025m02 
PARTITION OF stock_data_partitioned 
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Step 3: Add indexes to partitioned table
CREATE INDEX IF NOT EXISTS idx_partitioned_symbol_ts 
ON stock_data_partitioned (symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_partitioned_symbol_interval_ts 
ON stock_data_partitioned (symbol, interval, timestamp DESC);

-- ============================================
-- 5. Data Migration (RUN CAREFULLY)
-- ============================================
-- Uncomment and run this ONLY when ready to migrate data
-- This preserves the original table as backup

-- -- Migrate data from stock_data to stock_data_partitioned
-- INSERT INTO stock_data_partitioned 
--     (symbol, timestamp, open, high, low, close, volume, interval, source, created_at)
-- SELECT 
--     symbol, timestamp, open, high, low, close, volume, 
--     COALESCE(interval, '1min'), 
--     COALESCE(source, 'upstox'), 
--     COALESCE(created_at, NOW())
-- FROM stock_data
-- WHERE timestamp >= '2024-10-01';  -- Adjust date range as needed

-- -- After verifying migration, you can:
-- -- 1. Rename tables: ALTER TABLE stock_data RENAME TO stock_data_old;
-- -- 2. Rename partitioned: ALTER TABLE stock_data_partitioned RENAME TO stock_data;
-- -- 3. Update constraints and sequences

-- ============================================
-- Verification queries
-- ============================================

-- Check partition info:
-- SELECT 
--     parent.relname AS parent_table,
--     child.relname AS partition_name
-- FROM pg_inherits
-- JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
-- JOIN pg_class child ON pg_inherits.inhrelid = child.oid
-- WHERE parent.relname = 'stock_data_partitioned';

-- Check indicator table row count:
-- SELECT COUNT(*) FROM precomputed_indicators;

ANALYZE precomputed_indicators;
ANALYZE indicator_compute_jobs;
