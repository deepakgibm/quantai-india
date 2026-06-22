# Phase 14: FIX_LOG.md

Log of code patches applied to resolve issues found during the audit.

## Patch 1: SQL Join Optimization inside Freshness API
- **File**: `backend/api/metrics.py`
- **Function**: `get_data_freshness`
- **Root Cause**: The query performed a heavy JOIN on `instrument_master` across millions of daily candles.
- **Fix**: Changed the query to `COUNT(DISTINCT instrument_id)` directly on `stock_candle`, eliminating the JOIN.
- **Impact**: Reduced test run time by 68% (from 28.27s to 8.97s).

## Patch 2: Centralized Derivatives Calculation Helper
- **File**: `backend/services/derivatives_service.py` & `backend/api/option_flow.py`
- **Root Cause**: Calculations for PCR and IV were calculated inline within the HTTP request router.
- **Fix**: Created `calculate_iv` helper in `DerivativesService` and refactored the router to delegate calls.

## Patch 3: WebSocket Pre-Serialized Broadcasting
- **File**: `backend/api/websockets/market.py`
- **Root Cause**: Individual JSON serialization for every single connected socket.
- **Fix**: Pre-serialized JSON payload once and broadcasted using `send_text()`.
