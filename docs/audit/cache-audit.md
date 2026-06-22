# QuantAI Caching & DragonflyDB Audit

This report analyzes the Dragonfly cache usage, identifies inefficiencies, and outlines an optimal caching hierarchy.

## 1. Caching Inefficiencies & Miss Hotspots
* **Cache Stampedes**: 
  * When the option chain cache (`option_chain:{symbol}`) expires, multiple parallel requests to `/api/option-flow/{symbol}` trigger simultaneous Upstox API queries and database writes.
  * **Solution**: Implement mutex locking (using Redis `SET NX`) to ensure only one thread warms up the cache upon expiration.
* **Incorrect TTL Policies**:
  * Active stock prices (`price:{symbol}`) expire in 300 seconds (5 minutes). This is too long for real-time applications and too short for caching.
  * **Solution**:
    * Set live price TTL to 10 seconds.
    * Use a background worker to continuously update active keys, ensuring zero cache-miss latency on API requests.

## 2. Recommended Caching Hierarchy
- **Level 1: Local In-Memory Cache (FastAPI)**:
  * Cache static instrument mappings (`symbol` -> `instrument_id`).
  * TTL: 24 hours.
- **Level 2: Shared Cache (DragonflyDB)**:
  * Cache live option chains and sector performance arrays.
  * TTL: 5 seconds for live prices, 5 minutes for option chains, 10 minutes for sector performance.
- **Level 3: Database (PostgreSQL)**:
  * Persistent storage for all historical candles and user settings.
