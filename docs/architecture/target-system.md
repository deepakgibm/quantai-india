# QuantAI Target Architecture Spec

This document evaluates the target architectural options for QuantAI and recommends the optimal path based on current traffic and codebase state.

---

## 1. Architectural Options Comparison

### Option A: Optimized Monolith
*   **Description**: Keep the codebase as a single application. Optimize inline loops with NumPy/TA-Lib, parameterize database queries, and add database indexes.
*   **Complexity**: Low. (No changes to directories or processes).
*   **Cost**: Low. Runs on a single virtual machine (VM).
*   **Performance**: Improved. Fixes the most severe bottlenecks but does not isolate CPU-bound tasks from API request handling.
*   **Maintenance Effort**: Low.

### Option B: Modular Monolith (Recommended)
*   **Description**: Keep a single repository but enforce strict boundary separation between domains (User, Market Ingestion, Quant Compute, and AI). Offload heavy compute tasks (scanners and backtests) to background workers using a task queue (Celery/RQ) running in a separate container from the same codebase. Use DragonflyDB for caching and Pub/Sub.
*   **Complexity**: Medium. Requires separating modules and adding a background task runner.
*   **Cost**: Low. Can run on a single medium-size VM or lightweight containers.
*   **Performance**: Very High. Computes are fully isolated, ensuring the API remains responsive.
*   **Maintenance Effort**: Medium-Low. Easy to deploy and test.

### Option C: Microservices
*   **Description**: Split the application into independent services (e.g., Market Data Service, Backtest Service, AI Service, Auth Service) running in separate containers/repos. Deployed on Kubernetes (EKS).
*   **Complexity**: Extremely High. Introduces distributed transaction overhead, network latency, and CI/CD complexity.
*   **Cost**: High. EKS, API Gateways, and service meshes significantly increase cloud costs.
*   **Performance**: High under very large concurrent user loads (>100,000), but introduces network serialization overhead for internal calls.
*   **Maintenance Effort**: High.

---

## 2. Recommendation & Rationale

We recommend **Option B: Modular Monolith**.

### Rationale
1.  **Avoid Premature Scaling**: Microservices are designed to scale development teams and handle extreme traffic. At the current stage (10–1,000 users), the primary bottlenecks are inefficient code paths, not server capacity.
2.  **Infrastructure Cost Efficiency**: Option B can run on a single VM (e.g., AWS EC2 t3.large) for under $50/month, compared to $800+/month for an EKS cluster.
3.  **Isolation without Overhead**: Offloading backtests and scanners to Celery/RQ workers prevents CPU starvation on FastAPI workers. Using DragonflyDB for Pub/Sub decouples the tick feed from the API without requiring a Kafka setup.
