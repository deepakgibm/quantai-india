# Antigravity IDE Workspace Context: QuantAI India

This document serves as the primary system context file for AI-assisted development inside the Antigravity IDE. It specifies codebase rules, dependency structures, and design guidelines.

---

## 1. Core Principles

### Single Source of Truth for Pricing (LTP)
*   All spot price lookups must go through `backend/services/price_manager/price_service.py` (`PriceService`).
*   Never compute price change percentages or write ad-hoc price resolvers.
*   Standard keys to return/consume:
    *   `ltp`: Last Traded Price (float)
    *   `previous_close`: Previous trading session's close (float)
    *   `change_percent`: Price change percentage (float)
    *   `source`: Live source label (e.g. `UPSTOX_WS` or `DB_EOD`)

### Production-Only Feed Policy
*   Simulation, mock feeds, or synthetic data points are strictly forbidden in production.
*   If Upstox REST or WS feeds fail, bubble up a clean validation/error state immediately.

---

## 2. Directory & Component Mapping

*   `backend/api/`: REST endpoints.
*   `backend/services/`: Core logic engines.
*   `frontend/src/pages/`: Main page components.
*   `frontend/src/components/`: Shared UI widgets.
*   `docs/`: Consolidated system documentation.
*   `review_to_delete/`: Archived unreferenced legacy scripts (do not import anything from here).

---

## 3. Database Rules

*   Table models reside in `backend/models.py`.
*   All Postgres indexes should follow the format `idx_<table_name>_<column_names>`.
*   Always use session lifecycle wrappers (`SessionLocal`) and ensure sessions are closed in `finally` blocks.

---

## 4. Coding Conventions

*   **Python**:
    *   Use type hints for all service functions.
    *   Leverage structured logging (`logger.info`, `logger.error`) instead of `print()`.
    *   FastAPI dependencies should utilize `Depends` injections.
*   **React / TypeScript**:
    *   Strictly use TypeScript interfaces for component props.
    *   TailwindCSS is the primary style sheet. Do not insert inline style sheets.
    *   Verify responsive states for charts and tables.
