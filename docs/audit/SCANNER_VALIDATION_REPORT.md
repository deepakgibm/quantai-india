# Phase 9: SCANNER_VALIDATION_REPORT.md

Diagnostic verification of core stock scanners and signal generation.

## 1. Active Scanners Reviewed
1. **Breakout Scanner**: Identifies 52-week price breakouts.
2. **Momentum Scanner**: Identifies momentum stocks based on relative returns.
3. **VWAP Scanner**: Signals when price crosses the Volume-Weighted Average Price.
4. **Volume Scanner**: Detects stocks with volume > 200% of their 20-day average.

## 2. Signal Verification & Data Shape
- Calculations use unified group-aware technical indicators (`grouped_atr`, `grouped_rsi`, `grouped_sma`) from `indicator_utils.py`.
- Signals are calculated on pandas DataFrames, written to PostgreSQL `bot_signal` / `breakout_candidates` tables, and broadcasted to WebSockets.
- All scanner endpoints return compliant lists of active candidates.
