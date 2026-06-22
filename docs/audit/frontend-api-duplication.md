# QuantAI Frontend API & Request Duplication Audit

An audit of the frontend React pages, hooks, and services to identify redundant API requests, polling overlaps, and websocket subscription inefficiencies.

## 1. Sector Analysis and Heatmap Polling Overlaps
* **Current Flow**:
  * `SectorAnalysisPage.tsx` fetches `/api/sector-analysis/` on mount and polls every 30 seconds.
  * `SectorHeatmapPage.tsx` fetches `/api/heatmap/` on mount and polls every 15 seconds.
  * Both pages invoke a full scan of stock data on the backend, leading to redundant PostgreSQL aggregations.
* **Recommended Flow**:
  * Consolidate these endpoints. Introduce a single `/api/sector/overview` endpoint that caches results in Dragonfly with a 10-second TTL.
  * Share the fetched sector data state via a React Context or a shared React Query key, eliminating parallel fetches.
* **Expected Latency Savings**: Saves ~350ms of backend DB aggregation time per client request.

## 2. Watchlist & Dashboard Parallel Quote Queries
* **Current Flow**:
  * The `Dashboard.tsx` page renders watchlist cards and fetches quotes via `useApi` from `/api/watchlist/` and `/api/trading/market-indices` simultaneously.
  * `Watchlist.tsx` independently queries `/api/watchlist/{id}/quotes` while rendering, causing redundant fetches for the same symbols.
* **Recommended Flow**:
  * Use React Query's query sharing. Keep a single query key `['watchlist', id]` and share it across the dashboard components.
* **Expected Latency Savings**: Reduces HTTP requests by 2x on dashboard load.

## 3. Duplicate WebSocket Subscriptions
* **Current Flow**:
  * `useMarketDataStream.ts` opens a websocket client. If the user navigates between the `QuantWorkspace` and `OptionFlow` pages, both pages instantiate their own instances of `useMarketDataStream`, opening parallel WebSocket connections to `ws://localhost:8000/api/websockets/live`.
* **Recommended Flow**:
  * Wrap the WebSocket connection inside a global `WebSocketProvider` at the root of `App.tsx`.
  * Components should subscribe to the shared context rather than opening new connections.
