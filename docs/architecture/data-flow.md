# Data Flow Analysis

This document describes the flow of data within the QuantAI India application, including client request lifecycles, real-time WebSocket ticks, and background ETL pipelines.

## 1. User Request Flow (REST API)

```
[Browser Client] 
      │ 1. HTTP Request (with Firebase JWT Token)
      ▼
[Nginx Gateway] 
      │ 2. Route Matching & TLS Termination (Forward to backend:8000)
      ▼
[FastAPI Router] 
      │ 3. Setup correlation ID, run Auth dependency, check authorization
      ▼
[Business Service] 
      │ 4. Read cache (Dragonfly) first; if miss, execute SQL query
      ▼
[PostgreSQL Database] (or Dragonfly Cache)
      │ 5. Returns query results
      ▼
[Business Service] 
      │ 6. Process calculations (e.g. Pandas/Numpy matrices)
      ▼
[FastAPI Router] 
      │ 7. Serialize Pydantic model, register response metrics
      ▼
[Browser Client] (Renders dashboard data)
```

---

## 2. Real-Time WebSocket Streaming Flow

```
[Upstox WebSocket Server]
             │
             │ 1. Stream binary Protobuf tick packets
             ▼
[UpstoxWSManager (Background Worker)]
             │
             │ 2. Decode Protobuf byte arrays into structured dictionaries
             ▼
[DragonflyDB Cache] (SET key `qai:snap:{symbol}`)
             │
             │ 3. PUBLISH event to channel `qai:channel:ticks`
             ▼
[FastAPI WebSocket Router] (Subscribed to Dragonfly channel)
             │
             │ 4. Receives event notification in async loop
             ▼
[Web Browser Client] (Pushed via WS frame)
             │
             │ 5. Hydrates Lightweight Charts (updates latest candle)
             ▼
      [UI Chart Panel]
```

---

## 3. End-Of-Day (EOD) Ingestion & ETL Flow

```
 [Celery Beat Scheduler]
            │
            │ 1. Triggers daily tasks at 3:40 PM IST (post-market)
            ▼
   [Celery Worker Pool]
   ┌────────┴────────┐
   │                 │ 2. Download NSE Bhavcopy & yfinance fallback
   ▼                 ▼
[NSE CSV Files]   [yfinance Tickers]
   │                 │
   └────────┬────────┘
            │ 3. Parse data, filter active symbols, cast decimals
            ▼
   [stock_candle DB Table] (Inserts daily candles, Partition pruning active)
            │
            │ 4. Enqueues `PrecomputeIndicators` job
            ▼
[IndicatorComputeWorker] (Calculates RSI, MACD, Contractions in multiprocessing pool)
            │
            │ 5. Writes to `precomputed_indicators` table
            ▼
   [DragonflyDB Cache] (Warms up scanners and sector heatmap caches)
```
