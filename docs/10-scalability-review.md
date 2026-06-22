# Scalability Review & Roadmap

This document outlines the current capacity limits, scaling bottlenecks, and a multi-stage roadmap to scale QuantAI India to **1,000,000 concurrent users**.

## Current Capacity (Single Server)
- **Concurrent API Requests**: ~50–100 requests/sec.
- **Concurrent WebSockets**: ~20 active feeds.
- **Data Ingestion Universe**: 439 symbols.
- **Database Limits**: Max 60 connections (without PgBouncer active).
- **Compute Capability**: In-process training/backtesting blocks workers.

---

## Scaling Roadmaps & Milestones

### Milestone 1: 1,000 Users (Stabilization & Decoupling)
- **PgBouncer Connection Pooling**: Enable PgBouncer in transaction mode to pool and compress database client connection overhead.
- **Background Backtesting Queue**: Decouple backtesting execution from Uvicorn request loops. Send requests to Celery background tasks hosted on DragonflyDB.
- **WebSocket Pub/Sub Conversion**: Transition from pull-based WebSocket queries (polling Redis every 1s) to push-based DragonflyDB Pub/Sub subscriptions.

### Milestone 2: 10,000 Users (Read-Write Isolation)
- **Read Replicas**: Set up two read replicas of the PostgreSQL primary database. Routes like heatmap (`GET /api/heatmap`) and indicators are directed to `get_read_db()`, leaving the primary database for orders and user state writes.
- **Caching Layer Clustering**: Set up a DragonflyDB Primary/Replica pair, separating cache read requests from ingestion writes.

### Milestone 3: 100,000 Users (Cloud-Native Orchestration)
- **Kubernetes Migration**: Port the Docker Compose architecture to Kubernetes (manifests defined in `/kubernetes`).
- **Autoscaling (HPA)**: Define Horizontal Pod Autoscalers targeting CPU (>70%) and queue depth, scaling FastAPI instances dynamically (min: 3, max: 25 pods).
- **Database Partitioning by Timeframe**: Partition the partitioned `stock_candle` table by timeframe (e.g. creating distinct partitions for 1m, 5m, and daily candles) to keep indexes compact.

### Milestone 4: 1,000,000 Users (Distributed Streaming & Sharding)
- **Distributed Database Sharding**: Migrate from standard Postgres to Citus or TimescaleDB, sharding data nodes horizontally by `instrument_id`.
- **Event-Driven Streaming (Apache Kafka)**: Replace the direct Upstox ingestion worker with a Kafka cluster. Ingest ticks into Kafka topics (`ticks-raw`), and deploy specialized consumers (e.g. `indicator-processor`, `vcp-scanner`) in parallel.
- **Columnar Analytics (Apache Iceberg)**: Replace the flat Parquet files in local storage with Apache Iceberg tables stored on S3/GCS, managed by a DuckDB/Athena query engine.
