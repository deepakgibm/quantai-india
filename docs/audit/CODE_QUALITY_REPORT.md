# Phase 13: CODE_QUALITY_REPORT.md

Analysis of codebase complexity, duplicate logic, and dependencies.

## 1. Pruned Dead Code
- Deleted legacy folders: `backend/review_to_delete/` and `backend/scripts/legacy/`.
- Pruned 282 unused imports across all backend python files.

## 2. Consolidated Business Logic
- Moved Implied Volatility (IV) and Put-Call Ratio (PCR) calculations out of the router files (`option_flow.py`) into the `DerivativesService` helper.
- Standardized technical indicators (`wilder_rsi`, `wilder_atr`) into vectorized grouped functions inside `indicator_utils.py` to prevent math discrepancies.
