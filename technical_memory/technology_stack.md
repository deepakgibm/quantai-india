# Technical Memory: Technology Stack

This document declares all active technologies, frameworks, and database engines used in production.

---

## 1. Backend Core
*   **Language**: Python 3.11
*   **Web Framework**: FastAPI (ASGI)
*   **Task Queue**: Celery (handles asynchronous tasks like backtests and scans)
*   **ORM**: SQLAlchemy (relational mapping and session pool operations)
*   **Task Broker & Results Cache**: DragonflyDB (Redis-compatible broker)

## 2. Frontend Core
*   **Framework**: React 19
*   **Build Tool**: Vite
*   **State Management**: Zustand
*   **Styling**: TailwindCSS
*   **Charts**: Recharts (for analytics and bar metrics), Lightweight Charts (trading canvas)

## 3. Databases & Cache
*   **Primary DB**: PostgreSQL 15 (EOD candles, watchlists, billing history)
*   **InMemory Cache**: DragonflyDB (active quotes cache, WebSocket Pub/Sub)
*   **Testing DB**: SQLite (used for rapid test suites)
