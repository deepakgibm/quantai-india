# Antigravity IDE Refactoring Prompts for QuantAI Backend APIs

## PROMPT 1: Refactor ai.py (CRITICAL - 977 lines, 27+ endpoints)

```
TASK: Modularize FastAPI router file with 27+ AI-related endpoints

CONTEXT:
- Current file: backend/routers/ai.py (977 lines)
- Issue: Multiple disparate AI strategy endpoints mixed in one file
- Goal: Split into individual feature modules while maintaining API compatibility

DETAILED REQUIREMENTS:

1. CREATE NEW DIRECTORY STRUCTURE:
   Create backend/routers/ai/ directory with:
   - __init__.py (empty init file)
   - base.py (shared utilities and dependencies)
   - strategies.py (GET /api/ai/strategies endpoint)
   - market_analysis.py (GET /api/ai/market-analysis)
   - trend_finder.py (GET /api/ai/trend-finder)
   - breakout_detector.py (GET /api/ai/breakout-detector)
   - momentum_scanner.py (GET /api/ai/momentum-scanner + momentum)
   - mean_reversion.py (GET /api/ai/mean-reversion)
   - gap_scanner.py (GET /api/ai/gap-scanner)
   - relative_strength.py (GET /api/ai/relative-strength)
   - vwap_scanner.py (GET /api/ai/vwap-scanner + vwap)
   - sr_bounce.py (GET /api/ai/sr-bounce)
   - sentiment_analysis.py (GET /api/ai/sentiment)
   - prompt_engine.py (POST /api/ai/prompt + POST /api/ai/command)
   - top_picks.py (GET /api/ai/top5-picks + top3-picks)
   - router.py (main router combining all sub-routers)

2. EXTRACT SHARED CODE:
   - Move all imports from ai.py to base.py
   - Extract common functions like get_cached_ai_data(), set_cached_ai_data()
   - Create helper functions for Gemini API calls
   - Define common response models

3. MIGRATE ENDPOINTS:
   - FOR EACH endpoint function in ai.py:
     a) Identify which module it belongs to (based on functionality)
     b) Copy the entire function (including docstring and dependencies)
     c) Add to appropriate new file
     d) Fix imports to use base.py and relative imports
     e) Keep function names unchanged for backward compatibility

4. CREATE router.py IN ai/ DIRECTORY:
   ```python
   from fastapi import APIRouter
   from . import strategies, market_analysis, trend_finder, breakout_detector
   from . import momentum_scanner, mean_reversion, gap_scanner, relative_strength
   from . import vwap_scanner, sr_bounce, sentiment_analysis, prompt_engine, top_picks
   
   router = APIRouter(prefix="/api/ai", tags=["AI"])
   
   # Include all sub-routers
   router.include_router(strategies.router)
   router.include_router(market_analysis.router)
   router.include_router(trend_finder.router)
   ... (include all others)
   
   # Or simply re-export the routers as-is if they don't use prefix
   router = APIRouter()
   router.include_router(strategies.router, prefix="/api/ai")
   # etc
   ```

5. UPDATE main.py:
   - Change: from routers import ai
   - Change app.include_router() line to use new location
   - Old: app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
   - New: from routers.ai import router as ai_router
           app.include_router(ai_router, prefix="/api/ai", tags=["AI"])
   - OR: app.include_router(ai.router) if router already has correct prefix

6. VALIDATION:
   - Ensure no endpoints are lost
   - Verify all imports work
   - Test that API routes still respond at same paths
   - Check that response models are accessible
   - Verify Gemini API integration still works

7. OPTIONAL IMPROVEMENTS:
   - Add __all__ exports in each module
   - Add module-level docstrings
   - Create shared test file structure
   - Add logging specific to each module

DELIVERABLES:
- New backend/routers/ai/ directory with all 15 submodules
- Deprecated/archived original ai.py (don't delete, comment out)
- Updated main.py with correct imports
- All endpoints working at original API paths
- No external API changes
```

---

## PROMPT 2: Refactor scanner.py (CRITICAL - 735 lines, 10+ endpoints)

```
TASK: Modularize scanner FastAPI router with 10+ scanning strategy endpoints

CONTEXT:
- Current file: backend/routers/scanner.py (735 lines)
- Issue: Multiple scanner strategies + preset management mixed together
- Goal: Split into individual scanner type modules + preset management

DETAILED REQUIREMENTS:

1. CREATE NEW DIRECTORY STRUCTURE:
   Create backend/routers/scanner/ directory with:
   - __init__.py (empty init file)
   - base.py (shared scanner utilities)
   - strategies.py (GET /api/scanner/strategies)
   - reference_data.py (GET /api/scanner/indices, /timeframes)
   - momentum.py (GET /api/scanner/momentum, /momentum/status)
   - breakout.py (GET /api/scanner/breakout)
   - reversal.py (GET /api/scanner/reversal)
   - trendfinder.py (GET /api/scanner/trendfinder)
   - week52_breakout.py (GET /api/scanner/week52-breakouts)
   - presets.py (GET/POST/DELETE /api/scanner/presets)
   - execution.py (POST /api/scanner/run, GET /progress/{scan_id})
   - router.py (main router combining all)

2. EXTRACT SHARED CODE INTO base.py:
   - Global variables: StrategyRegistry, ScannerEngine, _scanner_available, scanner
   - Functions: get_cached_scanner_data(), set_cached_scanner_data()
   - Import statements and error handling setup
   - WebSocket connection management (if used)

3. MIGRATE ENDPOINTS:
   - FOR EACH endpoint in scanner.py:
     a) Identify primary responsibility (momentum, breakout, preset, etc.)
     b) Copy entire endpoint function
     c) Move to appropriate new file
     d) Update imports to use base.py
     e) Preserve function signatures exactly

4. PRESET MANAGEMENT (presets.py):
   - GET /api/scanner/presets
   - POST /api/scanner/presets
   - DELETE /api/scanner/presets/{preset_id}
   - Database operations using ScannerPreset model
   - Preserve User dependency injection

5. CREATE router.py:
   ```python
   from fastapi import APIRouter
   from . import strategies, reference_data, momentum, breakout, reversal
   from . import trendfinder, week52_breakout, presets, execution
   
   router = APIRouter(prefix="/api/scanner", tags=["Scanner"])
   
   router.include_router(strategies.router)
   router.include_router(reference_data.router)
   router.include_router(momentum.router)
   router.include_router(breakout.router)
   # ... include all others
   ```

6. UPDATE main.py:
   - Change: from routers import scanner
   - To: from routers.scanner import router as scanner_router
   - Update include_router call to use scanner_router

7. VALIDATION:
   - All 13+ endpoints accessible at original paths
   - Presets database operations work
   - Background tasks still run
   - Strategy registry loads correctly
   - Cache operations function properly

DELIVERABLES:
- New backend/routers/scanner/ directory with 11 submodules
- Original scanner.py archived/commented
- Updated main.py imports
- All endpoints at original API paths
```

---

## PROMPT 3: Refactor market.py (HIGH - 328 lines, 6+ endpoints)

```
TASK: Modularize market data FastAPI router

CONTEXT:
- Current file: backend/routers/market.py (328 lines)
- Issue: Mixing top movers, nifty100 ranking, heatmap, and orchestrator
- Goal: Separate by domain (pricing, rankings, heatmap, orchestrator)

DIRECTORY STRUCTURE:
backend/routers/market/
├── __init__.py
├── base.py (shared market utilities)
├── top_movers.py (GET /api/market/nifty100/top-movers + /top-movers alias)
├── nifty100_ranking.py (GET /api/market/nifty100/status)
├── orchestrator.py (GET /api/market/orchestrator/status)
├── health.py (GET /api/market/health)
├── heatmap_data.py (GET /api/market/heatmap)
├── sector_stocks.py (GET /api/market/sector-stocks/{sector_name})
└── router.py

REQUIREMENTS:
1. Extract shared code (INDUSTRY_MAPPING, SECTOR_MAP) to base.py
2. Preserve all 7 endpoints with original paths
3. Keep authentication requirements unchanged
4. Maintain Upstox client usage
5. Update main.py import

DELIVERABLES:
- New backend/routers/market/ directory
- All endpoints accessible at original routes
```

---

## PROMPT 4: Refactor analytics.py (HIGH - 390 lines, 11+ endpoints)

```
TASK: Modularize analytics FastAPI router with DuckDB integration

CONTEXT:
- Current file: backend/routers/analytics.py (390 lines)
- Issue: Mixing analytics queries, archive management, and indicators
- Goal: Separate by domain (overview, timeseries, archive, indicators)

DIRECTORY STRUCTURE:
backend/routers/analytics/
├── __init__.py
├── base.py (shared analytics utilities, DuckDB setup)
├── overview.py (GET /api/analytics/overview)
├── momentum.py (GET /api/analytics/momentum/top)
├── volatility.py (GET /api/analytics/volatility/{symbol})
├── correlation.py (POST /api/analytics/correlation)
├── support_resistance.py (GET /api/analytics/support-resistance/{symbol})
├── query_engine.py (POST /api/analytics/query)
├── archive.py (All archive endpoints: list, stats, month, old, restore)
├── indicators.py (POST /compute, GET /latest/{symbol})
└── router.py

REQUIREMENTS:
1. Extract DuckDB connection and query utilities to base.py
2. Extract Request/Response models to base.py
3. Preserve all 11+ endpoints
4. Maintain authentication dependencies
5. Keep background task functionality for archive operations

DELIVERABLES:
- New backend/routers/analytics/ directory
- All endpoints working at original paths
```

---

## PROMPT 5: Refactor trading.py (MEDIUM - 229 lines, 4-6 endpoints)

```
TASK: Modularize trading FastAPI router

CONTEXT:
- Current file: backend/routers/trading.py (229 lines)
- Issue: Mixing dashboard stats, health checks, market data, and gainers
- Goal: Separate by domain (dashboard, diagnostics, market data, gainers)

DIRECTORY STRUCTURE:
backend/routers/trading/
├── __init__.py
├── base.py (shared utilities)
├── dashboard.py (GET /api/trading/dashboard)
├── health.py (GET /api/trading/health)
├── market_data.py (GET /api/trading/market-indices, /instruments)
├── gainers_losers.py (GET /api/trading/top-gainers, /gainers-losers)
└── router.py

REQUIREMENTS:
1. Each module handles one concern
2. Preserve all 6 endpoints
3. Keep authentication for dashboard
4. No auth for health endpoints
5. Maintain Upstox integration

DELIVERABLES:
- New backend/routers/trading/ directory
- All endpoints at original paths
```

---

## PROMPT 6: Refactor upstox.py (MEDIUM - 7 endpoints)

```
TASK: Modularize Upstox integration router

CONTEXT:
- Current file: backend/routers/upstox.py
- Issue: Mixing auth, portfolio, positions, and quotes
- Goal: Separate by domain (auth, user data, portfolio, market data)

DIRECTORY STRUCTURE:
backend/routers/upstox/
├── __init__.py
├── base.py (Upstox client utilities)
├── auth.py (GET /auth-url, POST /callback)
├── user.py (GET /user-profile, /status)
├── portfolio.py (GET /portfolio, /positions)
├── quotes.py (GET /market-quote/{symbol})
└── router.py

REQUIREMENTS:
1. Preserve auth flow for Upstox callback
2. Maintain WebSocket manager setup
3. Keep market quote endpoint
4. Update main.py import

DELIVERABLES:
- New backend/routers/upstox/ directory
- All 7 endpoints working
```

---

## PROMPT 7: Final Validation & Testing

```
TASK: Validate and test all refactored routers

REQUIREMENTS:
1. Verify all endpoints respond at original URLs:
   - Run curl/Postman tests for every endpoint
   - Check response schemas unchanged
   - Validate authentication still works

2. Check main.py:
   - All import statements valid
   - All routers registered correctly
   - No circular imports
   - Server starts without errors

3. Testing:
   - Run existing unit tests
   - Check API documentation generation
   - Verify database operations
   - Validate cache operations
   - Test WebSocket connections if applicable

4. Code Quality:
   - No code duplication
   - All imports optimized
   - Module docstrings present
   - Logging still functional

5. Documentation:
   - Update API docs if changed
   - Update README with new structure
   - Create module-level documentation

DELIVERABLES:
- All tests passing
- No regressions
- Updated documentation
- Cleaned up old files
```

---

## Implementation Order (Priority)

1. **ai.py** → Most critical (977 lines, highest complexity)
2. **scanner.py** → Most critical (735 lines, high complexity)
3. **analytics.py** → High (390 lines, DuckDB integration)
4. **market.py** → High (328 lines, multiple concerns)
5. **trading.py** → Medium (229 lines)
6. **upstox.py** → Medium (7 endpoints)
7. **Final validation**

---

## Tips for Using These Prompts with Antigravity IDE

1. **Copy one prompt at a time** - Don't process all 7 simultaneously
2. **Wait for completion** before moving to next
3. **Review generated code** carefully before accepting
4. **Test each refactoring** before proceeding to next
5. **Keep git history** - Can rollback if needed
6. **Document changes** as you go

---

## Expected File Structure After Refactoring

```
backend/
├── routers/
│   ├── __init__.py
│   ├── ai/               (NEW - 15 modules)
│   ├── scanner/          (NEW - 11 modules)
│   ├── market/           (NEW - 7 modules)
│   ├── analytics/        (NEW - 9 modules)
│   ├── trading/          (NEW - 4 modules)
│   ├── upstox/           (NEW - 5 modules)
│   ├── auth.py           (unchanged - cohesive)
│   ├── risk.py           (unchanged - cohesive)
│   ├── settings.py       (unchanged - cohesive)
│   ├── orders.py         (unchanged - cohesive)
│   ├── algorithms.py     (unchanged - cohesive)
│   ├── heatmap.py        (consider merging with market/)
│   ├── agentic_bot.py    (unchanged - small, cohesive)
│   ├── engine_performance.py (unchanged)
│   ├── quant_bot.py      (OPTIONAL: split if grows)
│   ├── hp_scanner_api.py (OPTIONAL: merge with scanner/)
│   └── ai.py             (DEPRECATED - archive)
│   └── scanner.py        (DEPRECATED - archive)
│   └── market.py         (DEPRECATED - archive)
│   └── analytics.py      (DEPRECATED - archive)
│   └── trading.py        (DEPRECATED - archive)
│   └── upstox.py         (DEPRECATED - archive)
└── main.py               (UPDATED - new imports)
```

