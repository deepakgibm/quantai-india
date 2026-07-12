# Technical Memory: Testing Frameworks & Verification

## 1. Backend Regression Suite
*   **Testing Tool**: Pytest with `pytest-asyncio`.
*   **Command**: `pytest tests/ -v`
*   **Key Test File**: [test_price_consistency.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/tests/test_price_consistency.py) validating the central pricing engine.

## 2. Sector Data Integrity Audit
*   **Validator Script**: `python tests/verify_sector_integrity.py`
*   **Checks**: Validates database records against sector metrics, RSI computations, and instrument keys formatting.

## 3. Frontend Compilation
*   **Command**: `npm run build` executed in `frontend/` to run typescript checks and vite bundle production compiling.
