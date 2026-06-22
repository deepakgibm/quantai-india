# Backend Architecture

The QuantAI India backend is built on **FastAPI**, running asynchronously via Uvicorn, and backed by a **Celery** background worker pool and a **DragonflyDB** caching layer.

## High-Level Application Layout

```
                        ┌────────────────────────┐
                        │      FastAPI App       │
                        │      (main.py)         │
                        └───────────┬────────────┘
                                    │ (Registers)
            ┌───────────────────────┼──────────────────────┐
            ▼                       ▼                      ▼
┌───────────────────────┐ ┌───────────────────┐ ┌─────────────────────┐
│      Middlewares      │ │    API Routers    │ │    Startup Tasks    │
│  - CORS (Config)      │ │   - /api/auth     │ │  (asyncio task)     │
│  - Observability      │ │   - /api/trading  │ │  - MarketOrchestrat │
│  - Correlation ID     │ │   - /api/heatmap  │ │  - BreakoutService  │
│  - Metrics Scraper    │ │   - /api/scanner  │ │  - SectorService    │
└───────────────────────┘ └───────────────────┘ └─────────────────────┘
```

---

## Router & Middleware Registrations
[main.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/main.py) registers:
- **Middlewares**:
  - `CORSMiddleware` with dynamically resolved origins.
  - Observability Middleware: Automatically measures endpoint execution times, intercepts incoming request payloads, injects a unique correlation ID into HTTP headers, and reports latency to Prometheus metrics.
- **Routers**: Over 17 domain routers mounted under the `/api` prefix.
- **Exception Handlers**: Standard handlers formatting database connection errors, ValidationErrors, and general exceptions into consistent JSON error responses.

---

## Startup Sequence (Background Services)
Upon application startup (`@app.on_event("startup")`), FastAPI registers and kicks off 5 background tasks:
1. **`MarketDataOrchestrator.start()`**: Periodically synchronizes live feeds, manages WebSocket fallbacks, and writes tick buffers to cache.
2. **`start_nifty100_ranking_service()`**: Ranks top Nifty 100 movers and updates rankings every 30 seconds.
3. **`start_sector_service()`**: Calculates aggregate sector relative-strength metrics.
4. **`start_realtime_breakout_service()`**: Scans for 52-week highs and momentum breakouts.
5. **`RealtimeScannerEngine.initialize()`**: Restores scanner states, pulls cached tickers, and registers callbacks.

*Note: In `SAFE_MODE`, blocking initialization tasks are bypassed to ensure rapid container boot times.*

---

## Caching Strategy (DragonflyDB)
DragonflyDB is used as the high-performance cache broker. The cache client is defined in [cache.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/cache.py) and [dragonfly_client.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/dragonfly_client.py):
- **Cache TTL Policies**:
  - `qai:tick:{symbol}`: Tick cache, TTL = 60s.
  - `indicator:{symbol}`: Technical indicators, TTL = 5s.
  - `heatmap:{mode}:{timeframe}`: Page level performance, TTL = 30s.
- **Cache Decorator**: A custom `@cache_decorator` wraps service methods to automatically serialize and cache query outputs using JSON hashing.
- **Fail-Fast Policy**: In production, the client enforces a strict fail-fast policy with no in-memory fallbacks if the Dragonfly container becomes unavailable, preventing stale/inconsistent data states.

---

## Worker & Task Queue Architecture
Background tasks are handled by **Celery** via [celery_app.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/celery_app.py):
- **Broker & Backend**: DragonflyDB (`redis://dragonfly:6379/1`).
- **Pre-fetch Configuration**: Prefetch multiplier is restricted to `1` to guarantee fair task distribution among workers during long backtest runs.
- **Memory Leak Protection**: Each worker process is automatically recycled after executing `50` tasks or when reaching a `512MB` RSS memory threshold.
- **Acks Late**: Enabled to ensure tasks are only acknowledged *after* completion. If a worker container crashes during execution, the task is safely rescheduled back into the queue.
- **Scheduled Tasks (Celery Beat)**:
  - `sync_institutional_flows`: Parses block/bulk deals daily.
  - `run_signal_bot`: Runs the quantitative signal bot at market open (9:20 AM IST) and close (3:40 PM IST).
