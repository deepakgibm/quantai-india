# Technical Memory: Feature Inventory

This document registers all implemented, active functional components in the QuantAI India platform.

---

| Feature | Status | Service Owner | Dependencies | Documentation |
| --- | --- | --- | --- | --- |
| **Real-time Ingestion** | Active | `upstox_ws_manager` | Dragonfly Redis, Upstox | `market_data.md` |
| **Price Management** | Active | `PriceService` | Dragonfly Redis Cache | `business_rules.md` |
| **VCP Scanner** | Active | `InstitutionalScanner` | Postgres indicators, DB | `scanner_engine.md` |
| **Week 52 Breakout** | Active | `Week52BreakoutService` | Postgres EOD database | `scanner_engine.md` |
| **Sector Heatmap** | Active | `SectorService` | PostgreSQL, `PriceService` | `scanner_engine.md` |
| **Swarm Committee** | Active | `SwarmCommittee` | Google Gemini API | `ai_features.md` |
| **Backtester** | Active | `BacktestRunner` | PostgreSQL, Celery | `trading_engine.md` |
