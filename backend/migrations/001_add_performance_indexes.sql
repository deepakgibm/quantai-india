-- QuantAI Performance Optimization - Phase 1 SQL Migrations
-- Run these migrations to add optimized indexes

-- ============================================
-- 1. Add optimized composite index for multi-timeframe queries
-- ============================================
-- This index optimizes queries like:
-- SELECT * FROM stock_data WHERE symbol='RELIANCE' AND interval='1min' AND timestamp >= X

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_symbol_interval_ts 
ON stock_data (symbol, interval, timestamp DESC);

-- ============================================
-- 2. Partial index for recent data queries (last 30 days)
-- ============================================
-- This dramatically speeds up "latest data" queries by indexing only recent rows

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_data_recent 
ON stock_data (symbol, timestamp DESC)
WHERE timestamp >= NOW() - INTERVAL '30 days';

-- ============================================
-- 3. Analyze tables to update statistics
-- ============================================
-- Ensures query planner has accurate statistics after adding indexes

ANALYZE stock_data;
ANALYZE alpha_signals;
ANALYZE trade_decisions;

-- ============================================
-- Verification queries
-- ============================================
-- Run these to verify indexes were created:

-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'stock_data';

-- Check index usage stats:
-- SELECT relname, indexrelname, idx_scan, idx_tup_read, idx_tup_fetch 
-- FROM pg_stat_user_indexes 
-- WHERE relname = 'stock_data';
