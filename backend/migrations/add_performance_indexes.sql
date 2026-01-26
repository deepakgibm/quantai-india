-- ============================================================
-- Performance Optimization Indexes for QuantAI
-- ============================================================
-- Run this migration to improve query performance on hot paths.
-- 
-- Usage: psql -d quantai -f add_performance_indexes.sql
-- ============================================================

-- 1. stock_candle table - Primary query pattern: (instrument_id, timeframe, candle_ts range)
-- BRIN index is ideal for time-series data with natural ordering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_candle_ts_brin 
ON stock_candle USING BRIN (candle_ts) 
WITH (pages_per_range = 128);

-- Covering index for common lookup pattern
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_candle_lookup_desc 
ON stock_candle (instrument_id, timeframe, candle_ts DESC);

-- 2. instrument_master - Symbol lookups by exchange
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_instrument_exchange_symbol 
ON instrument_master (exchange, symbol);

-- Active instruments filter
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_instrument_active_exchange 
ON instrument_master (is_active, exchange) 
WHERE is_active = TRUE;

-- 3. alpha_signals - Temporal queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alpha_signals_timestamp 
ON alpha_signals (timestamp DESC);

-- Symbol + recent signals
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alpha_signals_symbol_recent 
ON alpha_signals (symbol, timestamp DESC);

-- 4. trade_decisions - User history lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trade_decisions_user_time 
ON trade_decisions (user_id, timestamp DESC);

-- 5. precomputed_indicators - Latest indicator lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_indicators_symbol_interval_latest 
ON precomputed_indicators (symbol, interval, timestamp DESC);

-- 6. etl_logs - Recent job status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_logs_recent 
ON etl_logs (timestamp DESC) 
WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days';

-- ============================================================
-- Analyze tables to update statistics
-- ============================================================
ANALYZE stock_candle;
ANALYZE instrument_master;
ANALYZE alpha_signals;
ANALYZE trade_decisions;

-- ============================================================
-- Verify indexes were created
-- ============================================================
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('stock_candle', 'instrument_master', 'alpha_signals', 'trade_decisions', 'precomputed_indicators')
ORDER BY tablename, indexname;
