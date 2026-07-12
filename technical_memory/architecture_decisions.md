# Technical Memory: Architecture Decision Records (ADRs)

## ADR 01: Single Source of Pricing (PriceService)
*   **Context**: The application had multiple resolvers querying price tickers, leading to inconsistent prices on the same dashboard.
*   **Decision**: Mandate that all REST endpoints, indicators engines, and React UI components fetch stock price data via `PriceService`.
*   **Status**: Active.

## ADR 02: Strict Upstox-Only Live Data
*   **Context**: Codebase included mock simulation fallbacks during off-hours, posing compliance risks.
*   **Decision**: Enforce a strict **Upstox-Only** data retrieval policy. Fail fast if both WS and REST connections are down.
*   **Status**: Active.

## ADR 03: Page Consolidation
*   **Context**: Codebase contained duplicate views for sector analytics and scanner presets.
*   **Decision**: Delete `TradeScreener.tsx` and `SectorAnalysisPage.tsx`, routing all features to `<Scanner />` and a togglable `<SectorHeatmapPage />`.
*   **Status**: Active.
