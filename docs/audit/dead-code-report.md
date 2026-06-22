# QuantAI Dead Code & Unused Services Report

This report lists the dead code, unused modules, and deprecated files identified in the repository.

## 1. Unused Services & Scripts
- **`backend/review_to_delete/`**:
  * Contains legacy files like `intraday_scanners.py`.
  * **Risk**: Low. Safe to delete.
- **`backend/scripts/legacy/`**:
  * Contains testing scripts like `check_manappuram.py` which are no longer needed.
  * **Risk**: Low. Safe to delete.

## 2. Unused Database Models & APIs
- **`backend/models_saas.py`**:
  * Defines SaaS subscription structures which are not currently used in the core trading application.
  * **Risk**: Medium (verify if any billing endpoints require this).
- **`backend/api_test_results.json`**:
  * Legacy test run metadata. Safe to delete.
