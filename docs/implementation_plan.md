# Implementation Plan - Fix API Timeouts (Indices & Heatmap)

This plan details the steps to resolve client-side timeout issues for the `/api/market/indices` and `/api/heatmap` endpoints in the QuantAI India backend application.

## User Review Required

> [!IMPORTANT]
> The database table `stock_candle` is partitioned and contains a large history of daily candles. The current heatmap SQL query does a full table scan over all partitions because it lacks a `candle_ts` filter in the initial CTE. Filtering `candle_ts` to a dynamic time window based on the timeframe (e.g., last 15 days for 1D, last 500 days for 1Y) will dramatically improve query execution times from >30s down to milliseconds.

## Open Questions
No open questions at this stage.

## Proposed Changes

### Backend APIs and Services

---

#### [MODIFY] [market_fallback.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/utils/market_fallback.py)
Reduce the yfinance indices fetch timeout from `15.0` seconds to `2.5` seconds to prevent blocking when yfinance is blocked from inside Docker.
- Modify the `timeout` parameter in `asyncio.wait_for` inside `fetch_live_indices_yfinance()` from `15.0` to `2.5`.

#### [MODIFY] [trading_service.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/services/trading_service.py)
Add a protective timeout wrapper around the yfinance fallback call.
- Wrap `await fetch_live_indices_yfinance()` with `asyncio.wait_for(..., timeout=3.0)` to ensure it never exceeds the overall response time limit, even if the internal timeout fails or hangs.

#### [MODIFY] [heatmap.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/api/heatmap.py)
Optimize the sector heatmap query by introducing a dynamic `cutoff_date` filter.
- Calculate `cutoff_date` dynamically based on the requested `timeframe`:
  - `1D` -> 15 calendar days
  - `1W` -> 30 calendar days
  - `1M` -> 60 calendar days
  - `3M` -> 150 calendar days
  - `6M` -> 250 calendar days
  - `1Y` -> 500 calendar days
- Pass `:cutoff_date` parameter to the SQL query.
- Add `AND candle_ts >= :cutoff_date` to the `candle_ranks` CTE inside `stock_candle` subquery.

---

## Verification Plan

### Automated/Manual Verification
1. Rebuild and restart the backend container:
   `docker compose build backend`
   `docker compose up -d backend`
2. Test `/api/market/indices` response speed:
   `docker exec quantai-backend curl -s "http://localhost:8000/api/trading/market-indices" -o /dev/null -w "%{time_total}s\n"`
   Ensure response is returned in < 3 seconds.
3. Verify that the console no longer logs timeout / abort errors for market indices and SectorHeatmapPage.
