# Audit Fix Plan

**Date:** 2026-01-21
**Phase:** 0 (Baseline Safety)

## Findings & Scan Results

### 1. Duplicate Indicator Logic
We found that **RSI, MACD, EMA, Bollinger Bands** are implemented in:
- `backend/services/indicator_compute_service.py` (Manual pandas implementation)
- `backend/services/intraday_scanners.py` (Likely manual or mixed)
- `backend/strategies/tier1/rsi_mean_reversion.py` (Imports from `core.scanner.indicator_utils`)
- `backend/core/scanner/indicator_utils.py` (The likely "source of truth")

**Resolution:**
We will refactor all services to import from a new `backend/core/indicators/` package. We will migrate logic from `indicator_utils.py` into this new package to strict files (`rsi.py`, `macd.py`) as requested.

### 2. Inefficient Backtesting Loops
Found `for i in range(len(df))` in:
- `backend/services/backtest_engine.py`
- `backend/services/walk_forward_backtest_service.py`
- `backend/core/scanner/indicator_utils.py` (Parabolic SAR implementation is iterative - this is unavoidable for SAR, but others should be vectorized)

**Resolution:**
Rewrite `backtest_engine.py` to use vectorized pandas operations.

### 3. Frontend Redundancy
`Dashboard.tsx` uses both polling and WebSocket.

**Resolution:**
Implement `useMarketDataStream` hook to manage exclusive connection.

### 4. Observability Gaps
Many `print()` statements found in `backend/services/`.
Existing logging module `backend/core/observability/logging.py` exists but is not universally used.

**Resolution:**
Replace prints with `logger.info/error` and ensure strict usage of the `core.observability` module.

## Risk Assessment
- **High Risk:** Backtest refactor. A vectorized implementation might differ slightly in float precision or edge cases (NaN handling) vs the iterative one.
- **Mitigation:** We will keep the legacy method accessible (renamed) or strictly benchmark result parity before deleting.

## Action Plan
1.  **Frontend:** Fix `Dashboard.tsx` (Safe).
2.  **Indicators:** Create `core/indicators`, move logic, verify tests (Safe).
3.  **Backtest:** Refactor `backtest_engine` (Risky - careful verification needed).
4.  **Logging:** Replace prints (Safe).
