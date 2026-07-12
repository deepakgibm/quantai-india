# Technical Memory: Market Data Pipeline

## 1. Upstox Ingestion
*   **Source**: Upstox REST and WebSocket API.
*   **Protobuf Streaming**: WebSocket ticks are transmitted as binary Protobuf packages, decoded in `backend/utils/upstox_proto.py` to extract LTP, volumes, and bid/ask lists.
*   **Fail-Fast Policy**: 100% Upstox data. If live feeds fail, the system bubbles up an error immediately instead of synthesizing mock rates.

## 2. Telemetry and Reconnections
WebSocket connections are monitored for timeouts. In case of connection drops, the system schedules a reconnection attempt after 1000ms.
