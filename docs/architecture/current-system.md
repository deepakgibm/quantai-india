# QuantAI Current System Architecture

This document describes the current architecture of QuantAI India as verified from the codebase.

---

## 1. Frontend Architecture (React)

The frontend is a single-page application (SPA) built using Vite, React, and TypeScript.

### 1.1 Project Structure
*   **Directory**: `frontend/src/`
*   **Routing**: Defined in [App.tsx](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/frontend/src/App.tsx) using `react-router-dom` (v7.18.0). All pages are statically imported at the root, leading to a single large JS chunk.
*   **Entry Points**: [index.tsx](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/frontend/src/index.tsx) mounts the React app, loading the global styles from [index.css](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/frontend/src/index.css).

### 1.2 State Management & Hooks
*   **Global State**: Managed via React Context (`AuthContext` in `contexts/AuthContext.tsx`). There is no dedicated state management library like Zustand or Redux implemented.
*   **Server State**: Managed using `@tanstack/react-query` (v5.101.0). Used to cache REST API responses for scanners, indicators, and profile settings.
*   **Custom Hooks**: Custom hooks under `hooks/` fetch data (e.g., `useWatchlist`, `useScanner`) and manage WebSocket connections (e.g., `useWebSocket`).

### 1.3 Charting & Visual Libraries
*   **Trading Charts**: Uses `lightweight-charts` (v4.1.1) from TradingView for interactive candlestick charts.
*   **Analytical Charts**: Uses `recharts` (v3.4.1) for dashboard stats, portfolio metrics, and performance charts.
*   **Complex Visualizations**: Uses `echarts` (v6.0.0) for multi-dimensional diagrams like volatility grids and option payoff diagrams.
*   **Icons**: Standardized on `lucide-react`.

---

## 2. Backend Architecture (FastAPI)

The backend is built as a Python-based FastAPI application running on Uvicorn.

### 2.1 Router Mapping
API endpoints are defined in [main.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/main.py) and routed under `/api/`:
*   `/api/auth`: [auth.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/auth.py) (SSO, JWT)
*   `/api/market`: [market_data.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/market_data.py) (LTP, indicators, indices)
*   `/api/scanner`: [scanners.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/scanners.py) (Equities screenings)
*   `/api/ws`: [websockets.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/websockets.py) (Client tick stream)
*   `/api/option-flow`: [option_flow.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/option_flow.py) (Greeks, chains)
*   `/api/saas`: [saas_router.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/saas_router.py) (SaaS billing, billing levels)

### 2.2 Caching & Database Access
*   **Database**: PostgreSQL managed using SQLAlchemy 2.0 with async (`asyncpg`) and sync (`psycopg2`) connections configured in [database.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/database.py).
*   **Cache**: DragonflyDB (Redis-compatible) acts as the cache layer. Managed through [dragonfly_client.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/dragonfly_client.py) (and partially [cache.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/cache.py)), storing ticks, indicators, and page cache keys.

### 2.3 Compute & Background Workers
*   **Scanner Engine**: Scans are processed using background processes in [hp_scanner_service.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/hp_scanner_service.py) and [indicator_worker.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/workers/indicator_worker.py), which runs parallel processes to bypass the GIL.
*   **Backtesting Engines**: Duplicated across `core/backtest/engine.py`, `services/backtest_engine.py`, and `services/walk_forward_backtest_service.py`.
*   **AI Analytics**: Powered by Google Gemini (`@google/genai`) to generate fundamental summaries.

---

## 3. Database Layer (PostgreSQL)

Relational structures and time-series data schemas are defined in [models.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/models.py) and [models_alpha.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/models_alpha.py):

*   `users`: User credentials, subscription level, status.
*   `instrument_master`: Traded instrument identifiers, symbols, and company sectors.
*   `stock_candle`: Primary time-series table. Composite PK is `(instrument_id, timeframe, candle_ts)`. Timeframe values are stored as integers (`timeframe` = 1, 5, 15, 60, 1440).
*   `alpha_signals` & `trade_decisions`: ML model alpha scores, action logs, P&L trackers.

### 3.1 DB Query Patterns
*   **Sync vs Async**: FastAPI uses `AsyncSessionLocal` for transactional operations. Sync `SessionLocal` is used by Celery tasks and legacy modules.
*   **Connection Pools**: Pool size is configured to 10 connections (max overflow 20) in [database.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/database.py).

---

## 4. Market Data & Real-Time Feed

*   **Upstox REST API**: Historical candle downloads are managed by [rest_data_fetcher.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/rest_data_fetcher.py) and [upstox_client.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/upstox_client.py) using an analytics token.
*   **Upstox WebSocket API**: Managed by [upstox_ws_manager.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/upstox_ws_manager.py). Connects via `wss://api.upstox.com/v2/feed/market-data-feed`, decodes Protobuf ticks, updates the Dragonfly cache, and runs callbacks registered by services like [websocket_feed_manager.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/websocket_feed_manager.py).
*   **Client WebSocket Updates**: Connected client browsers receive updates from the FastAPI WS server, which retrieves cached ticks from DragonflyDB.
