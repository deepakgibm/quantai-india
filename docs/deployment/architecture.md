# Deployment Architecture

QuantAI India is designed as a containerized stack that can run locally via Docker Compose or scale in a production cluster using Kubernetes.

## Docker Compose Orchestration (Local/Single-VM)
The [docker-compose.yml](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/docker-compose.yml) configures 7 core services running in a bridge network:

1. **`quantai-frontend`**:
   - **Image**: Built from `Dockerfile.frontend`.
   - **Engine**: Nginx reverse proxy serving static React Vite assets.
   - **Port**: Maps port `3000` on the host to port `80` inside the container.
2. **`quantai-backend`**:
   - **Image**: Built from `Dockerfile` in `/backend`.
   - **Engine**: FastAPI running via Uvicorn (binds to port `8000`).
3. **`quantai-dragonfly`**:
   - **Image**: `docker.dragonflydb.io/dragonflydb/dragonfly`.
   - **Engine**: High-throughput in-memory cache and Celery broker. Binds to `6379`.
4. **`quantai-worker`**:
   - **Image**: Custom Celery worker image.
   - **Engine**: Executes backtesting tasks, indicator precomputation, and signal bot runs.
5. **`quantai-prometheus`**:
   - **Image**: `prom/prometheus:latest`.
   - **Engine**: Collects time-series system metrics from the backend `/metrics` endpoint.
6. **`quantai-grafana`**:
   - **Image**: `grafana/grafana:latest`.
   - **Engine**: Visualization dashboard accessible at port `3001`.
7. **`quantai-redis-exporter`**:
   - **Image**: `oliver006/redis_exporter`.
   - **Engine**: Scrapes DragonflyDB engine statistics and exports them to Prometheus on port `9121`.

---

## Production Deployment Topology

```
                       [Internet Traffic]
                               │
                               ▼
                    [Nginx Ingress / ALB]
                               │
            ┌──────────────────┴──────────────────┐ (SSL/TLS terminated)
            ▼                                     ▼
   [React Frontend Pods]                 [FastAPI Backend Pods]
   (Nginx Static Server)                 (ASGI Application Servers)
                                                  │
            ┌──────────────────┬──────────────────┼──────────────────┐
            ▼                  ▼                  ▼                  ▼
      [Celery Workers]   [PgBouncer Pool]  [Dragonfly Cluster] [S3 Bucket]
    (Compute Task Nodes)       │           (Redis Cache Nodes) (Parquet Data)
                               ▼
                      [Postgres DB Node]
```

---

## Observability & Metrics Scraper
- **RED Method Metrics**: The backend `/metrics` endpoint collects:
  - **Rate**: Request counters per route, method, and HTTP status code.
  - **Errors**: 5xx server exceptions and network timeouts.
  - **Duration**: Execution latencies histogram.
- **Monitoring Exporters**:
  - The `redis_exporter` scrapes memory usage, connected clients, hit/miss ratios, and CPU load of DragonflyDB.
  - Prometheus consolidates these metrics every 15 seconds.
  - Grafana imports dashboards to visualize latencies and memory growth.
