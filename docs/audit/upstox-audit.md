# QuantAI Upstox Integration Audit

An analysis of all integrations with the Upstox REST and WebSocket APIs, identifying inefficiencies and rate-limiting risks.

## 1. Upstox API Call Inventory
* **WebSocket API**:
  * Used by `market_feed_service` to receive live tick data.
* **REST API**:
  * `/market-quote/quotes`: Used for active quotes fallback.
  * `/historical-candles`: Used for chart loading.

## 2. API Call Inefficiencies
* **Duplicate Quote Requests**:
  * The backend api requests live quotes for stocks in watchlists individually instead of batching them in groups of 50 (Upstox's batch limit).
* **Blocking REST Calls inside Async Loops**:
  * Direct HTTP GET requests inside FastAPI request handlers block the event loop, causing request timeouts during high-traffic periods.

## 3. Remediation Plan
* **Consolidate to event-driven updates**:
  * Eliminate all synchronous REST calls from `/api/` endpoints.
  * All active prices must be fetched exclusively from Dragonfly (`price:{symbol}`) populated by the `market-feed-service` WebSocket and Kafka consumers.
