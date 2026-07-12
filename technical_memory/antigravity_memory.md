# Antigravity IDE System Context Memory

This document is compiled for direct ingestion by the Antigravity AI assistant. It represents the active coding standards and system invariants.

---

## 1. Codebase Architecture

```text
quantai-india/
├── backend/
│   ├── api/          # FastAPI routers
│   ├── services/     # core calculations
│   │   ├── price_manager/ # PriceService
│   │   └── scanners/ # Strategy scanners
├── frontend/
│   └── src/
│       ├── components/ # Shared React UI
│       └── pages/      # View tabs (Dashboard, Scanner, Heatmap)
```

---

## 2. Invariants & Rules

1.  **Spot Quotes (LTP)**:
    - Code MUST resolve stock prices using `PriceService` (`backend/services/price_manager/price_service.py`).
    - Standard returned keys: `ltp`, `previous_close`, `change_percent`, `source`.
2.  **Upstox-Only Live Data**:
    - No simulated ticks or off-market price generations in production.
    - If market APIs fail, throw an explicit connection error immediately.
3.  **Database Sessions**:
    - Manage connections via `SessionLocal` with clean `finally: session.close()` blocks.
4.  **Consolidated Pages**:
    - Do not re-introduce `TradeScreener.tsx` or `SectorAnalysisPage.tsx`. Route scans and heatmap tabs to `<Scanner />` and `<SectorHeatmapPage />` respectively.
