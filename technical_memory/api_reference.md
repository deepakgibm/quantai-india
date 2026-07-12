# Technical Memory: API Reference

This file outlines REST and WebSocket gateway endpoints.

---

## 1. Authentication
*   **Method**: Bearer JWT Token.
*   **Header**: `Authorization: Bearer <token>`
*   **Routes Required**: Most endpoints under `/api` (excluding landing pages and healthchecks).

## 2. API Endpoints

### Markets & Quotes
*   **GET** `/api/market-quote/{symbol}`: Returns live quote metrics (LTP, prev_close, change_percent).
*   **GET** `/api/market/indices`: Retrieves indexes status (Nifty 50, Bank Nifty, etc.).

### Scanners
*   **GET** `/api/scanner/week52-breakouts`: Fetches stocks making 52-week highs/lows.
*   **GET** `/api/scanners/v3/run`: Runs Minervini Trend Templates.

### WebSocket Feeds
*   **WS** `/api/ws/live?token=<JWT>`: Decodes Upstox Protobuf packets and streams live spot quotes.
*   **WS** `/api/scanner/ws`: Streams live scanner breakout notifications.
