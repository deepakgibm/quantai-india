# Technical Debt Report

This document registers code smells, architectural limitations, and tech debt categories ranked by severity and priority for remediation.

## Code Smells & Maintenance Risks

### 1. Duplicated Backtest Engines (Severity: `CRITICAL`)
- **Vulnerability**: There are **four separate implementations** of the core backtesting logic:
  1. `core/backtest/engine.py` (370 lines)
  2. `experiment_lab/engine/backtest_runner.py` (417 lines)
  3. `services/walk_forward_backtest_service.py` (~850 lines)
  4. `services/backtest_engine.py` (~500 lines)
- **Impact**: Code changes or bug fixes to order execution, margin calculations, or slip adjustments must be manually duplicated across 4 files, creating a high risk of divergence.
- **Remediation**: Standardize on `core/backtest/engine.py` as the single source of truth, refactoring the Experiment Lab and Walk-Forward optimization pages to consume it via dependency injection.

### 2. God Classes
- **Vulnerability**:
  - `intraday_scanners.py` (923 lines): Contains the base class and all 9 distinct technical scanner strategies.
  - `walk_forward_backtest_service.py` (~850 lines): Handles parameters, optimization runs, and CSV exports in a single file.
- **Impact**: Highly coupled code, difficult to trace bugs, and impossible to develop or test individual strategies in isolation.
- **Remediation**: Split scanners into a modular package structure: `scanners/base.py`, `scanners/momentum.py`, `scanners/gap.py`, etc.

---

## Architectural Issues

### 1. Subprocess-based ML Training Pipeline (Severity: `HIGH`)
- **Vulnerability**: The ML training API (`ml_training.py`) starts model training by spinning up a local command-line subprocess: `subprocess.Popen(["python", "production_training.py"])`. The status of the job is written to a flat local file (`ml_status.json`), and the process is tracked using a global variable `_active_pid`.
- **Impact**:
  - If the application scales to multiple Uvicorn workers or runs inside a Kubernetes cluster, each worker has its own `_active_pid`, making tracking fail.
  - No locking mechanism: multiple users can trigger simultaneous training, crashing the server.
- **Remediation**: Decouple training entirely from the API thread. Send training requests as Celery tasks and use DragonflyDB to store job state.

### 2. duckdb_engine in-memory database configuration (Severity: `MEDIUM`)
- **Vulnerability**: The feature store in `core/lake_dal.py` initializes an in-memory DuckDB instance (`:memory:`) upon each request.
- **Impact**: Data is cleared at the end of the request. Cold start times are slow because DuckDB must scan the local Parquet directory tree recursively from scratch to warm up.
- **Remediation**: Initialize a persistent local DuckDB file database that is updated incrementally by background workers.

---

## Tech Debt Risk Register

| Risk Category | Impacted Module | Severity | Priority | Remediation Plan |
| :--- | :--- | :--- | :--- | :--- |
| **SQL Injection** | `feature_store.py` | 🔴 Critical | Immediate | Parameterize all dynamic DuckDB queries. |
| **Monolithic Routers**| `ai.py`, `scanner.py` | 🔴 High | High | Divide routers into feature-based sub-modules. |
| **CORS Wildcard** | `main.py` | 🔴 High | High | Define explicit allowed origin domain arrays. |
| **In-Process Backtest**| `core/backtest/engine` | 🔴 High | Medium | Transition backtesting execution to Celery queues. |
| **Pickle Deserialization**| `ml/ensemble.py` | 🟡 Medium | Medium | Implement tensor-based model formats. |
| **Dead Code** | `memcached_client.py` | 🟢 Low | Low | Delete unused stub files. |
