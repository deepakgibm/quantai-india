# Technical Memory: Deployment & Infrastructure

## 1. Container Architecture
The platform is deployed via Docker Compose with the following service registry:
*   `quantai-frontend` (Port 3000)
*   `quantai-backend` (Port 8000)
*   `quantai-market-service` (Port 8001)
*   `quantai-market-feed` (Port 8002)
*   `quantai-dragonfly` (Port 6379)
*   `quantai-worker` & `quantai-celery-worker` (Background jobs)

## 2. Docker Stack Control
To apply refactored source changes, restart target containers cleanly to clear python compiled caches:
```bash
docker restart quantai-backend quantai-worker quantai-celery-worker
```
