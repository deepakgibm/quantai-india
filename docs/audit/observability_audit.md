# QuantAI Observability Audit

This report reviews the structured logging, metrics, and tracing capabilities of QuantAI, diagnosing gaps in error tracing and system performance analysis.

---

## 1. Diagnostics Questionnaire

We evaluated whether the current observability configuration can answer key operational questions:

### 1.1 Why did an API fail?
*   **Answerability**: *Partial*.
*   **Assessment**: `StructuredFormatter` captures traceback exceptions and correlation IDs. However, because logs are output only to standard output (stdout), if a container crashes or is rescheduled, logs are lost unless we manually parse files on the host node. There is no log aggregator (such as Grafana Loki or Elasticsearch) to query logs.

### 1.2 Why is a scanner slow?
*   **Answerability**: *No*.
*   **Assessment**: We cannot profile scanner execution. There is no APM (Application Performance Monitoring) or distributed tracing (OpenTelemetry) configured. We cannot see whether latency was caused by database query blocking, network roundtrips to Upstox, or CPU-bound calculations in the indicator workers without writing manual code timers.

### 1.3 Why is a stock price stale?
*   **Answerability**: *No*.
*   **Assessment**: While ticks are decoded and cached, there are no metrics tracking price staleness. If the Upstox feed stops sending quotes for a symbol, the system does not raise alerts or update health endpoints.

### 1.4 Why did a WebSocket disconnect?
*   **Answerability**: *No*.
*   **Assessment**: `ConnectionManager` logs `WebSocket Client disconnected` inside `websockets/market.py` but does not log the WebSocket close frame status code (e.g., `1006` Abnormal Closure, `1011` Server Error). This makes it difficult to diagnose network issues.

---

## 2. Gaps & Technical Debt

1.  **No Distributed Tracing**: Lack of OpenTelemetry spans makes it difficult to debug performance bottlenecks across routers, services, and workers.
2.  **No Log Aggregation**: Standard output logs are lost on container restart.
3.  **Missing Alert Rules**: Prometheus metrics are exported at `/metrics` but there are no alert configurations for high latency or connection drops.
