# QuantAI Refactoring Roadmap

A prioritized timeline to resolve all identified issues:

## Phase 1: Dead Code Cleanup
* Delete `backend/review_to_delete/` and legacy script folders.
* Remove unused imports.

## Phase 2: Consolidated Indicators
* Merge single-symbol and grouped multi-symbol calculations into `core/scanner/indicator_utils.py`.

## Phase 3: DB & Caching Optimizations
* Centralize metadata lookups to avoid redundant database joins.
* Implement cache warm-up and locking mechanisms.
