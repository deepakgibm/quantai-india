# QuantAI Real-Time Market Data Audit

This report evaluates the Upstox WebSocket tick ingestion pipeline, caching layers, and browser client subscription mechanics, identifying critical gaps and performance issues.

---

## 1. Client Subscriptions Gap

*   **Vulnerability**: When a browser client connects to `/api/ws/live` and subscribes to a list of symbols (e.g., `["RELIANCE", "TCS"]`), the subscription is only saved to the connection's local memory inside `ConnectionManager.active_connections`. The router does *not* notify the `WebSocketFeedManager` to subscribe to those symbols at the Upstox API level.
*   **Impact**: If the symbol is not already part of the Nifty 100 universe (which is pre-subscribed on startup by the ranking service), the backend will never receive ticks for it from Upstox, leaving the user with an empty feed.
*   **Fix Recommendation**: When the WebSocket router receives a subscribe action, trigger a non-blocking background task to register the symbols with the feed manager:
    ```python
    await get_websocket_feed_manager().ensure_active(symbols)
    ```

---

## 2. Event Loop Blockage during Ingestion

*   **Vulnerability**: In [backend/services/websocket_feed_manager.py:60](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/websocket_feed_manager.py#L60), the tick callback writes data to the cache using `cache.set()`, which is a synchronous network operation. Because this callback is executed synchronously from the main WebSocket listener thread, it blocks the async event loop for every incoming price tick.
*   **Impact**: Under high market volatility, the event loop will lock up, leading to tick lag, socket disconnects, and dropped frames.
*   **Fix Recommendation**: Replace the synchronous `cache.set` call with the asynchronous `cache.set_async`.

---

## 3. Cache Bypassing & Local State Drift

*   **Vulnerability**: The `WebSocketFeedManager` updates a local memory cache in the `UpstoxPriceResolver` using `resolver.update_local_cache()`. 
*   **Impact**: When running multiple Uvicorn worker processes (which is standard for production), each worker maintains its own local memory cache. Price updates received by one worker are not visible to other workers, causing inconsistent pricing data across different API requests.
*   **Fix Recommendation**: All components (scanners, indicators, APIs) must read live price data from the centralized DragonflyDB cache, eliminating worker-local state duplication.
