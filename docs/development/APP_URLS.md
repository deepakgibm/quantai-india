# QuantAI Application URLs

This file contains the centralized registry of all URLs for the QuantAI project.

## 🚀 Core Services

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend UI** | [http://localhost:3000](http://localhost:3000) | Main Trading Dashboard (React/Vite) |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | FastAPI Backend Base URL |
| **API Documentation** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI / OpenAPI Spec |
| **Alternative Docs** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | ReDoc API Documentation |

---

## 📊 Monitoring & Observability

| Service | URL | Description |
|---------|-----|-------------|
| **Grafana** | [http://localhost:3001](http://localhost:3001) | Visualization Dashboards (User: `admin` / Pwd: `admin`) |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | Time-series Data & Query Browser |
| **System Health** | [http://localhost:8000/health](http://localhost:8000/health) | Comprehensive Dependency Health Check |
| **App Metrics** | [http://localhost:8000/metrics](http://localhost:8000/metrics) | Application Prometheus Metrics |

---

## 🛠️ Infrastructure Exporters (Raw Data)

| Exporter | URL | Description |
|----------|-----|-------------|
| **PostgreSQL** | [http://localhost:9187/metrics](http://localhost:9187/metrics) | Raw Database Metrics |
| **DragonflyDB** | [http://localhost:9121/metrics](http://localhost:9121/metrics) | Raw Cache Metrics (Redis-Compatible) |

---

## 📝 Troubleshooting & Logs
- **Backend Logs**: Available via `docker logs quantai-backend`
- **Worker Logs**: Available via `docker logs quantai-worker`
- **Correlation IDs**: Look for `X-Correlation-ID` header in API responses to trace logs.
