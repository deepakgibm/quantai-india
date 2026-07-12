# QuantAI Backend API Refactoring Analysis & Recommendations

## Executive Summary
Your backend API structure has **multiple endpoints consolidated into single router files**, which violates the Single Responsibility Principle (SRP). This creates tight coupling between features and makes future maintenance difficult. This document provides analysis and a refactoring prompt for Antigravity IDE.

---

## Current Architecture Problems

### 1. **Files with Multiple Disparate APIs**

#### **ai.py** (977 lines) - ⚠️ CRITICAL
- **27+ endpoints** serving different AI strategies
- Endpoints cover: Market analysis, trend finding, breakout detection, momentum scanning, mean reversion, gap scanning, relative strength, VWAP, support/resistance, sentiment analysis, AI prompts, AI commands
- **Problem**: Adding/removing one strategy impacts entire file. Changes to trend-finder affect breakout-detector's performance.

**Current Endpoints**:
```
GET  /api/ai/strategies
POST /api/ai/prompt
GET  /api/ai/market-analysis
GET  /api/ai/trend-finder
GET  /api/ai/breakout-detector
GET  /api/ai/top5-picks
GET  /api/ai/top3-picks
GET  /api/ai/momentum-scanner
GET  /api/ai/mean-reversion
GET  /api/ai/gap-scanner
GET  /api/ai/relative-strength
GET  /api/ai/vwap-scanner
GET  /api/ai/sr-bounce
POST /api/ai/command
GET  /api/ai/sentiment
GET  /api/ai/momentum
GET  /api/ai/vwap
... and more
```

#### **scanner.py** (735 lines) - ⚠️ CRITICAL
- **10+ endpoints** for different scanning strategies
- Endpoints: Momentum, breakout, reversal, trendfinder, week52-breakouts, presets management
- **Problem**: Scanner logic tightly coupled with preset management and WebSocket handling

**Current Endpoints**:
```
GET  /api/scanner/strategies
GET  /api/scanner/indices
GET  /api/scanner/timeframes
POST /api/scanner/run
GET  /api/scanner/progress/{scan_id}
GET  /api/scanner/presets
POST /api/scanner/presets
DELETE /api/scanner/presets/{preset_id}
GET  /api/scanner/momentum
GET  /api/scanner/breakout
GET  /api/scanner/reversal
GET  /api/scanner/trendfinder
GET  /api/scanner/week52-breakouts
GET  /api/scanner/momentum/status
```

#### **market.py** (328 lines) - ⚠️ HIGH
- **6+ endpoints** mixing different concerns
- Endpoints: Top movers, rankings, orchestrator status, health, heatmap data, sector stocks
- **Problem**: Market data APIs, orchestrator status, and heatmap all in one file

**Current Endpoints**:
```
GET /api/market/nifty100/top-movers
GET /api/market/nifty100/status
GET /api/market/top-movers
GET /api/market/orchestrator/status
GET /api/market/health
GET /api/market/heatmap
GET /api/market/sector-stocks/{sector_name}
```

#### **trading.py** (229 lines) - ⚠️ MEDIUM
- **4+ endpoints** mixing dashboard stats, health checks, and market data
- Endpoints: Dashboard stats, health check, market indices, instruments, gainers

**Current Endpoints**:
```
GET /api/trading/dashboard
GET /api/trading/health
GET /api/trading/market-indices
GET /api/trading/instruments
GET /api/trading/top-gainers
GET /api/trading/gainers-losers
```

#### **analytics.py** (390 lines) - ⚠️ HIGH
- **11+ endpoints** for analytics, archives, and indicators
- Endpoints: Overview, momentum, volatility, correlation, support-resistance, DuckDB queries, archive management, indicators
- **Problem**: Analytics queries, archive management, and indicator computation all mixed

**Current Endpoints**:
```
GET  /api/analytics/overview
GET  /api/analytics/momentum/top
GET  /api/analytics/volatility/{symbol}
POST /api/analytics/correlation
GET  /api/analytics/support-resistance/{symbol}
POST /api/analytics/query
GET  /api/analytics/archive/list
GET  /api/analytics/archive/stats
POST /api/analytics/archive/month
POST /api/analytics/archive/old
POST /api/analytics/archive/restore
POST /api/analytics/indicators/compute
GET  /api/analytics/indicators/latest/{symbol}
```

#### **upstox.py** - ⚠️ MEDIUM
- **6+ endpoints** mixing authentication, portfolio, positions, and quotes
- Endpoints: Status, auth-url, user profile, callback, portfolio, positions, market quote

**Current Endpoints**:
```
GET  /api/upstox/status
GET  /api/upstox/auth-url
GET  /api/upstox/user-profile
POST /api/upstox/callback
GET  /api/upstox/portfolio
GET  /api/upstox/positions
GET  /api/upstox/market-quote/{symbol}
```

#### **auth.py** (207 lines) - ⚠️ MEDIUM
- **4 endpoints** mixing signup, login, and user management
- However, this is acceptable as auth is a cohesive domain

**Current Endpoints**:
```
POST /api/auth/signup
POST /api/auth/login
POST /api/auth/firebase-login
GET  /api/auth/me
```

### 2. **Other Multi-Purpose Files**

| File | Lines | Endpoints | Concern |
|------|-------|-----------|---------|
| quant_bot.py | ~250+ | 4 | Mixing backtest, walkforward, strategy list, symbols |
| orders.py | 147 | 3 | Mixing order creation, retrieval, and list |
| algorithms.py | ~150 | 5 | Mixing CRUD operations (OK - cohesive domain) |
| risk.py | ~100 | 2 | Risk settings (OK - cohesive) |
| settings.py | ~100 | 2 | User settings (OK - cohesive) |
| hp_scanner_api.py | ~300 | 8+ | High-performance scanner endpoints |
| heatmap.py | ~100 | 3 | Sector heatmap operations |
| agentic_bot.py | ~100 | 2 | Agentic bot operations |
| engine_performance.py | ~150 | 3 | Performance monitoring |

---

## Recommended Refactoring Structure

### Phase 1: **Critical Refactoring** (ai.py & scanner.py)

#### ai.py → Split into:
```
routers/ai/
├── __init__.py
├── base.py                    # Shared AI utilities
├── strategies.py              # GET /api/ai/strategies
├── market_analysis.py         # GET /api/ai/market-analysis
├── trend_finder.py            # GET /api/ai/trend-finder
├── breakout_detector.py       # GET /api/ai/breakout-detector
├── momentum_scanner.py        # GET /api/ai/momentum-scanner
├── mean_reversion.py          # GET /api/ai/mean-reversion
├── gap_scanner.py             # GET /api/ai/gap-scanner
├── relative_strength.py       # GET /api/ai/relative-strength
├── vwap_scanner.py            # GET /api/ai/vwap-scanner
├── sr_bounce.py               # GET /api/ai/sr-bounce
├── sentiment_analysis.py      # GET /api/ai/sentiment
├── prompt_engine.py           # POST /api/ai/prompt, /ai/command
├── top_picks.py               # GET /api/ai/top5-picks, /api/ai/top3-picks
└── router.py                  # Main router combining all sub-routers
```

#### scanner.py → Split into:
```
routers/scanner/
├── __init__.py
├── base.py                    # Shared scanner utilities
├── strategies.py              # GET /api/scanner/strategies
├── momentum.py                # GET /api/scanner/momentum
├── breakout.py                # GET /api/scanner/breakout
├── reversal.py                # GET /api/scanner/reversal
├── trendfinder.py             # GET /api/scanner/trendfinder
├── week52_breakout.py         # GET /api/scanner/week52-breakouts
├── presets.py                 # GET/POST/DELETE /api/scanner/presets
├── execution.py               # POST /api/scanner/run, GET /progress
├── reference_data.py          # GET /api/scanner/indices, /timeframes
└── router.py                  # Main router combining all sub-routers
```

### Phase 2: **High Priority Refactoring** (market.py, analytics.py, trading.py)

#### market.py → Split into:
```
routers/market/
├── __init__.py
├── top_movers.py              # GET /api/market/nifty100/top-movers
├── nifty100_ranking.py        # GET /api/market/nifty100/status
├── orchestrator.py            # GET /api/market/orchestrator/status
├── health.py                  # GET /api/market/health
├── heatmap_data.py            # GET /api/market/heatmap
├── sector_stocks.py           # GET /api/market/sector-stocks/{sector}
└── router.py
```

#### analytics.py → Split into:
```
routers/analytics/
├── __init__.py
├── overview.py                # GET /api/analytics/overview
├── momentum.py                # GET /api/analytics/momentum/top
├── volatility.py              # GET /api/analytics/volatility/{symbol}
├── correlation.py             # POST /api/analytics/correlation
├── support_resistance.py       # GET /api/analytics/support-resistance/{symbol}
├── query_engine.py            # POST /api/analytics/query
├── archive.py                 # Archive management endpoints
├── indicators.py              # POST/GET /api/analytics/indicators/*
└── router.py
```

#### trading.py → Split into:
```
routers/trading/
├── __init__.py
├── dashboard.py               # GET /api/trading/dashboard
├── health.py                  # GET /api/trading/health
├── market_data.py             # GET /api/trading/market-indices, instruments
├── gainers_losers.py          # GET /api/trading/gainers-losers
└── router.py
```

### Phase 3: **Medium Priority Refactoring** (upstox.py, others)

#### upstox.py → Split into:
```
routers/upstox/
├── __init__.py
├── auth.py                    # GET /auth-url, POST /callback
├── user.py                    # GET /user-profile, /status
├── portfolio.py               # GET /portfolio, /positions
├── quotes.py                  # GET /market-quote/{symbol}
└── router.py
```

---

## Implementation Strategy

### Step 1: Create new modular structure
- Create subdirectories for each module
- Create `__init__.py` files
- Create `router.py` in each subdirectory

### Step 2: Extract shared utilities
- Create `base.py` in each module with shared logic
- Create `services/` modules as needed

### Step 3: Migrate endpoints
- Move each endpoint function to dedicated file
- Update imports
- Keep router registration in `router.py`

### Step 4: Update main.py
- Change: `from routers import ai` 
- To: `from routers.ai import router as ai_router`
- Simpler: Keep the same import, just include sub-routers

### Step 5: Testing
- Run unit tests for each endpoint
- Verify routing still works
- Check API documentation generation

---

## Benefits of This Refactoring

✅ **Modularity**: Each API has its own file - easier to find and understand  
✅ **Single Responsibility**: Each file handles one feature  
✅ **Reduced Coupling**: Modifying trend-finder won't affect breakout-detector  
✅ **Easier Testing**: Can test individual features in isolation  
✅ **Better Scalability**: New features don't bloat existing files  
✅ **Team Collaboration**: Different developers can work on different features without conflicts  
✅ **Maintenance**: Easier to locate bugs and add features  
✅ **CI/CD**: Can deploy features independently  

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Breaking changes during refactor | High | Comprehensive testing, gradual migration |
| Import path confusion | Medium | Clear documentation, update IDE config |
| Performance degradation | Low | Modular design doesn't impact performance |
| Backward API compatibility | Medium | Maintain same routes, just reorganize code |

---

## Antigravity IDE Refactoring Prompt (See Next Section)

Use the prompt below in Antigravity IDE for automated refactoring assistance.

