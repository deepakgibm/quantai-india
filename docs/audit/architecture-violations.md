# QuantAI Architectural Violations Audit

This document identifies layer violations and code smells that deviate from clean architecture principles.

## 1. Business Logic inside Routers
* **Hotspot**: `backend/api/option_flow.py` contains inline calculations for Implied Volatility (IV) and Put-Call Ratio (PCR) inside the request handler.
* **Correction**: Move all PCR and IV calculations to `backend/services/derivatives_service.py` and keep routers strictly responsible for request parsing and response rendering.

## 2. FastAPI Directly Instantiating Connections
* **Hotspot**: Some routes directly call `UpstoxClient()` instead of using a dependency injector or cached client registry.
* **Correction**: Standardize on dependency injection via FastAPI `Depends()`.
