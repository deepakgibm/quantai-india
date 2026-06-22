# Technology Stack Analysis

QuantAI India utilizes a modern, high-performance quantitative trading stack designed for low-latency market data processing and heavy backtesting compute.

## Frontend Stack

| Layer | Technology | Version | Purpose / Role |
| :--- | :--- | :--- | :--- |
| **Core Framework** | React | `^19.2.0` | User interface structure and page components |
| **Build Tooling** | Vite | `^6.2.0` | Fast development server and production builds |
| **Language** | TypeScript | `~5.8.2` | Static type safety across components and APIs |
| **Styling** | Tailwind CSS | `^3.4.17` | Premium modern utility-first CSS styling |
| **State Management** | React Context + Query | `^5.101.0` | Global state (Auth, symbols) + server-cache state |
| **Data Fetching** | Fetch API | Native | Promise-based request wrapper with custom retry/timeout |
| **Charts & Visuals** | Recharts / Lightweight Charts | `^3.4.1` / `4.1.1` | Financial stock charts, equity curves, drawdown distribution |
| **Authentication** | Firebase Client SDK | `^12.7.0` | SSO, Google/Email authentication |

---

## Backend Stack

| Layer | Technology | Version | Purpose / Role |
| :--- | :--- | :--- | :--- |
| **API Framework** | FastAPI | `^0.110.0` | High-performance ASGI web framework, automatic OpenAPI |
| **Task Queue** | Celery | `^5.3.0` | Distributed asynchronous task queue for backtesting |
| **Web Server** | Uvicorn | `^0.28.0` | ASGI server implementation, running multi-workers |
| **Database ORM** | SQLAlchemy | `^2.0.0` | Database schema mapping and connection pooling |
| **Async Driver** | asyncpg | `^0.29.0` | Low-level asynchronous database driver for Postgres |
| **Data Analysis** | Pandas / Numpy | `^2.2.0` | Dataframe manipulation and numerical vector math |
| **Local Analytics** | DuckDB | `^0.10.0` | In-memory vectorized DB for local feature store queries |
| **HTTP Client** | HTTPX | `^0.27.0` | Asynchronous HTTP client for external API requests |
| **AI Integration** | Google GenAI SDK | `^1.30.0` | Large language model prompts (Gemini API) |

---

## Cache & Database Stack

| Component | Technology | Version | Purpose / Role |
| :--- | :--- | :--- | :--- |
| **Primary Database** | PostgreSQL | `16` | Relational storage for users, orders, settings, and metrics |
| **Connection Pooler**| PgBouncer | `1.21` | Connection pooling to avoid DB connection exhaustion |
| **In-Memory Cache** | DragonflyDB | `latest` | Redis-compatible cache & broker (up to 25x faster than Redis) |
| **Data Warehouse** | Parquet | Columnar | Local file-based Hive-partitioned warehouse for ticks |

---

## Infrastructure & Observability

| Service | Technology | Version | Purpose / Role |
| :--- | :--- | :--- | :--- |
| **Containerization**| Docker / Compose | `v2` | Consistent container deployment and service isolation |
| **Proxy / Gateway** | Nginx | `1.25` | Reverse proxy, static file server, and SSL/TLS routing |
| **Metrics Collect** | Prometheus | `latest` | Time-series scraper collecting system and API metrics |
| **Visualization** | Grafana | `latest` | Dashboard visualization for API latencies, CPU, and Redis keys |
| **Redis Metrics** | Redis-exporter | `latest` | Exporter bridging Dragonfly stats into Prometheus |
