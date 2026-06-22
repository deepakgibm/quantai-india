# API Documentation & Inventory

This document outlines the core public and authenticated endpoints exposed by the QuantAI India FastAPI application.

## Authentication Overview
- **Public Endpoints**: `/health`, `/ready`, `/metrics`, `/api/auth/signup`, `/api/auth/login`, `/api/trading/market-indices`.
- **Authenticated Endpoints**: All other endpoints require a Firebase ID token passed in the header as:
  `Authorization: Bearer <firebase_token>`

---

## API Catalog

### 1. Authentication Module

#### `POST /api/auth/signup`
- **Purpose**: Creates a new user profile in the local database.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword",
    "username": "user123",
    "full_name": "John Doe"
  }
  ```
- **Response**: `201 Created` with created user metadata.

#### `POST /api/auth/firebase-login`
- **Purpose**: Synchronizes a Firebase client session, generates a local session token, and returns user details.
- **Request Headers**: Requires Bearer Firebase Token.
- **Response**:
  ```json
  {
    "status": "success",
    "user": {
      "email": "user@example.com",
      "subscription_level": "FREE",
      "is_active": true
    }
  }
  ```

---

### 2. Market Data & Analytics Module

#### `GET /api/trading/market-indices`
- **Purpose**: Returns real-time or cached quotes for NIFTY 50, BANK NIFTY, and INDIA VIX.
- **Response**:
  ```json
  [
    {
      "name": "NIFTY 50",
      "value": 23643.5,
      "change": -46.1,
      "percent": -0.19,
      "source": "database",
      "stale": true
    }
  ]
  ```

#### `GET /api/heatmap`
- **Purpose**: Returns sector-grouped, market-cap weighted treemap hierarchy data for Nifty 500 stocks.
- **Query Parameters**:
  - `mode` (string): `performance` (default), `volatility`, `momentum`, `delivery`, `relative_strength`.
  - `timeframe` (string): `1D`, `1W`, `1M`, `3M`, `6M`, `1Y`.
- **Response**:
  ```json
  {
    "status": "success",
    "mode": "performance",
    "timeframe": "1D",
    "sectors": [
      {
        "name": "Bank",
        "avg_value": 0.52,
        "total_market_cap": 85000000000.0,
        "stocks": [
          {
            "symbol": "HDFCBANK",
            "name": "HDFC Bank Limited",
            "price": 1450.2,
            "market_cap": 11000000000.0,
            "change_pct": 1.25,
            "value": 1.25
          }
        ]
      }
    ]
  }
  ```

#### `GET /api/volume-profile`
- **Purpose**: Returns Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL) volume histograms.
- **Query Parameters**:
  - `symbol` (string): Stock symbol (e.g. `RELIANCE`).
  - `lookback` (integer): Number of daily candles to parse (e.g. `30`).
- **Response**:
  ```json
  {
    "symbol": "RELIANCE",
    "poc_price": 2420.0,
    "vah_price": 2450.0,
    "val_price": 2380.0,
    "profile_bins": [
      {"price": 2400.0, "volume": 125000, "is_poc": false, "in_value_area": true}
    ]
  }
  ```

---

### 3. AI & Backtesting Module

#### `POST /api/ai/prompt`
- **Purpose**: Evaluates a conversational prompt with Gemini LLM context injected with current market states.
- **Request Body**:
  ```json
  {
    "prompt": "Analyze RELIANCE structure and recommend trade setups."
  }
  ```
- **Response**:
  ```json
  {
    "response": "Reliance is showing a VCP consolidation with 3 contractions...",
    "referenced_symbols": ["RELIANCE"],
    "verdict": "BULLISH"
  }
  ```

#### `POST /api/backtest/run`
- **Purpose**: Submits a backtest configuration to the Celery worker queue.
- **Request Body**:
  ```json
  {
    "strategy_name": "EMA_Cross",
    "symbols": ["RELIANCE", "TCS"],
    "timeframe": "1d",
    "start_date": "2025-01-01",
    "end_date": "2026-01-01",
    "parameters": {"fast_ema": 20, "slow_ema": 50}
  }
  ```
- **Response**:
  ```json
  {
    "task_id": "87b0a8-826e-4eda-abd7-a4b2b1755807",
    "status": "QUEUED"
  }
  ```
