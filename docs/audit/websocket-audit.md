# QuantAI WebSocket Service Audit

Audit of the WebSocket feeds, subscription management, and client broadcasting handlers.

## 1. Zombie Connections
* **Issue**:
  * When a frontend client disconnects abruptly, the backend WebSocket handler (`backend/api/websockets/live`) does not immediately detect it, keeping the connection object in memory and continuing to process ticks.
* **Solution**:
  * Implement a ping/pong heartbeat (every 15 seconds) inside the WebSocket connection manager. If the client fails to pong within 5 seconds, terminate the connection.

## 2. Redundant Tick Broadcasts
* **Issue**:
  * If 50 clients are viewing the same workspace, the backend broadcasts individual tick payloads to all 50 sockets independently, leading to repeated JSON serialization.
* **Solution**:
  * Pre-serialize the JSON payload once for each symbol and broadcast the pre-serialized string to all subscribed channels, reducing CPU overhead by 90%.
