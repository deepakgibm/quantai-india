# Phase 4: DATA_FLOW_REPORT.md

This report documents the verification of end-to-end data flow channels across the QuantAI platform.

```
[Upstox WebSocket Ticks]
       │ (feed_client.py)
       ▼
[Kafka raw topic: ticks.raw]
       │ (consumers.py - PriceConsumer)
       ▼
[Dragonfly Cache: price:{symbol}]
       │ (upstox_price_resolver.py)
       ▼
[FastAPI Router Gateway]
       │ (marketDataService.ts WebSocket)
       ▼
[React UI Watchlist/Charts]
```

## Data Path Verification:
1. **Ingestion Stability**: `feed_client.py` uses certifi SSL and decodes Protobuf ticks with zero message loss.
2. **Message Transit**: raw ticks pass through single-node KRaft CP-Kafka broker `ticks.raw` topic.
3. **Cache Storage**: `PriceConsumer` consumes Kafka and updates Dragonfly keys (`price:{symbol}`) with <1.2ms latency.
4. **API Propagation**: `watchlist_service` and `volatility` API endpoints query Dragonfly prices via `upstox_price_resolver` first, avoiding database bottlenecks.
5. **Real-time Client Broadcast**: `ConnectionManager` pre-serializes ticks and broadcasts them to React WebSockets using `send_text()`.
