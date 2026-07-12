# Technical Memory: System Architecture

## 1. Architectural Layers

The codebase is organized following **Clean Architecture** principles to separate concerns and enforce module boundaries:

```
[Presentation Layer: React SPA]
           │
           ▼
[Application Layer: FastAPI API Endpoints]
           │
           ▼
[Service Layer: Business Logic Engines (PriceService, Scanners)]
           │
           ▼
[Data Layer: SQLAlchemy ORM / Postgres / DragonflyDB Cache]
```

1.  **Presentation (UI)**: Built with React, Zustand, and TailwindCSS. Communicates via REST APIs and WebSockets.
2.  **Application (API)**: Routers in `backend/api/` handle requests, validate schemas, and run dependencies.
3.  **Service (Business Rules)**: Services located in `backend/services/` compute rankings, run scans, compute indicators, and orchestrate LLMs.
4.  **Data (Database/Cache)**: `backend/database.py` manages SQLAlchemy sessions. DragonflyDB maintains active caches.

## 2. Dependency Flow
Dependencies flow inwards: API routers import service classes, services query database structures, and database classes represent entity models. There are no circular dependencies.
