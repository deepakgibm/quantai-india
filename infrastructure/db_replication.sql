-- PostgreSQL Logical Replication Setup for Multi-Region Disaster Recovery
-- Run on PRIMARY Region Database (Publisher)
-- Run on SECONDARY Region Database (Subscriber)

-------------------------------------------------------------------------------
-- STEP 1: PRIMARY REGION (PUBLISHER)
-------------------------------------------------------------------------------

-- 1. Ensure wal_level is set to logical in postgresql.conf
-- ALTER SYSTEM SET wal_level = 'logical';
-- SELECT pg_reload_conf();

-- 2. Create a replication user
CREATE USER replication_user WITH REPLICATION PASSWORD 'repl_super_secret_password';

-- 3. Grant table access to the replication user
GRANT SELECT ON ALL TABLES IN SCHEMA public TO replication_user;

-- 4. Create the Publication
-- We include all tables for full state recovery, or specific heavy tables if bandwidth is limited.
CREATE PUBLICATION quantai_global_pub FOR ALL TABLES;

-------------------------------------------------------------------------------
-- STEP 2: SECONDARY REGION (SUBSCRIBER)
-------------------------------------------------------------------------------

-- 1. Create the database schema (metadata only)
-- Use: pg_dump -s quantai | psql quantai_replica

-- 2. Create the Subscription
-- Note: Replace <primary-db-host> with the internal IP or private DNS of the primary.
-- CREATE SUBSCRIPTION quantai_global_sub 
-- CONNECTION 'host=<primary-db-host> port=5432 user=replication_user password=repl_super_secret_password dbname=quantai' 
-- PUBLICATION quantai_global_pub;

-------------------------------------------------------------------------------
-- MONITORING REPLICATION
-------------------------------------------------------------------------------

-- Check replication slot status (on Publisher)
-- SELECT * FROM pg_replication_slots;

-- Check subscription progress (on Subscriber)
-- SELECT * FROM pg_stat_subscription;
