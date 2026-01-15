# MASTER REFACTORING PROMPT FOR ANTIGRAVITY IDE

## 🎯 COMPREHENSIVE BACKEND API MODULARIZATION PROJECT

---

## PROJECT OVERVIEW

### Objective
Refactor 6 monolithic FastAPI router files (2,859+ lines, 70+ endpoints) into 43 modular, feature-based files while maintaining 100% API backward compatibility.

### Current State Problems
- **ai.py**: 977 lines, 27+ endpoints mixed together
- **scanner.py**: 735 lines, 10+ endpoints mixed together
- **analytics.py**: 390 lines with 3 separate concerns mixed
- **market.py**: 328 lines with 4 separate concerns mixed
- **trading.py**: 229 lines with 4 separate concerns mixed
- **upstox.py**: 200+ lines with 4 separate concerns mixed

### Target State
Transform into modular structure with clear separation of concerns:
- Each endpoint/feature in its own file
- Shared utilities in module-level `base.py`
- Main router aggregates sub-routers
- Average file size: 60-70 lines (vs 300-400 currently)

---

## PHASE 1: CRITICAL REFACTORING - ai.py (977 lines → 15 modules)

### Step 1.1: Create Directory Structure
```
Create: backend/routers/ai/
Files to create:
  ├── __init__.py (empty)
  ├── base.py
  ├── strategies.py
  ├── market_analysis.py
  ├── trend_finder.py
  ├── breakout_detector.py
  ├── momentum_scanner.py
  ├── mean_reversion.py
  ├── gap_scanner.py
  ├── relative_strength.py
  ├── vwap_scanner.py
  ├── sr_bounce.py
  ├── sentiment_analysis.py
  ├── prompt_engine.py
  ├── top_picks.py
  └── router.py
```

### Step 1.2: Extract Shared Code to base.py

**Instructions**:
1. Create `backend/routers/ai/base.py`
2. Move ALL imports from current ai.py to base.py:
   - FastAPI imports
   - Gemini API setup
   - Cache operations
   - Database imports
   - Authentication utilities
   - Schema models
   - Config/settings

3. Move shared functions:
   - `get_cached_ai_data(strategy_id: str)` 
   - `set_cached_ai_data(strategy_id: str, data: any)`
   - Any helper functions used by multiple endpoints
   - Gemini model initialization

4. Keep global state setup:
   ```python
   from fastapi import APIRouter, Depends
   import google.generativeai as genai
   from config import settings
   from services.memcached_client import get_cache
   from database import get_db, AsyncSessionLocal
   from utils.auth import get_current_user, get_optional_user
   from models import User
   from schemas import AIPromptRequest, AIPromptResponse, AICommandRequest, AICommandResponse
   import logging
   
   logger = logging.getLogger(__name__)
   
   # Gemini setup
   if settings.GEMINI_API_KEY:
       genai.configure(api_key=settings.GEMINI_API_KEY)
       model = genai.GenerativeModel("gemini-2.0-flash")
   else:
       model = None
   
   # Shared functions
   def get_cached_ai_data(strategy_id: str):
       cache = get_cache()
       if not cache.is_available():
           return None
       try:
           return cache.get(f"qai:ai:strategy:{strategy_id}")
       except Exception as e:
           logger.error(f"Cache get error: {e}")
           return None
   
   def set_cached_ai_data(strategy_id: str, data: any):
       cache = get_cache()
       if not cache.is_available():
           return
       try:
           cache.set(f"qai:ai:strategy:{strategy_id}", data, ttl=60)
       except Exception as e:
           logger.error(f"Cache set error: {e}")
   ```

### Step 1.3: Migrate Individual Endpoints

**strategies.py** - GET /api/ai/strategies
```
Source: ai.py lines containing get_ai_strategies()
Action: Copy entire function (including docstring)
Result: Single endpoint file (~50 lines)
```

**market_analysis.py** - GET /api/ai/market-analysis
```
Source: ai.py lines containing get_ai_market_analysis()
Action: Copy entire function
Result: Single endpoint file (~40 lines)
```

**trend_finder.py** - GET /api/ai/trend-finder
```
Source: ai.py lines containing get_ai_trend_finder()
Action: Copy entire function
Result: Single endpoint file (~45 lines)
```

**breakout_detector.py** - GET /api/ai/breakout-detector
```
Source: ai.py lines containing get_ai_breakout_detector()
Action: Copy entire function
Result: Single endpoint file (~50 lines)
```

**momentum_scanner.py** - GET /api/ai/momentum-scanner + GET /api/ai/momentum
```
Source: ai.py - momentum_scanner and momentum endpoints
Action: Copy both functions to same file
Result: Single file with 2 related endpoints (~60 lines)
```

**mean_reversion.py** - GET /api/ai/mean-reversion
```
Source: ai.py lines containing get_ai_mean_reversion()
Action: Copy entire function
Result: Single endpoint file (~50 lines)
```

**gap_scanner.py** - GET /api/ai/gap-scanner
```
Source: ai.py lines containing get_ai_gap_scanner()
Action: Copy entire function
Result: Single endpoint file (~45 lines)
```

**relative_strength.py** - GET /api/ai/relative-strength
```
Source: ai.py lines containing get_ai_relative_strength()
Action: Copy entire function
Result: Single endpoint file (~50 lines)
```

**vwap_scanner.py** - GET /api/ai/vwap-scanner + GET /api/ai/vwap
```
Source: ai.py - vwap_scanner and vwap endpoints
Action: Copy both functions
Result: Single file with 2 related endpoints (~55 lines)
```

**sr_bounce.py** - GET /api/ai/sr-bounce
```
Source: ai.py lines containing get_ai_sr_bounce()
Action: Copy entire function
Result: Single endpoint file (~50 lines)
```

**sentiment_analysis.py** - GET /api/ai/sentiment
```
Source: ai.py lines containing get_ai_sentiment()
Action: Copy entire function
Result: Single endpoint file (~45 lines)
```

**prompt_engine.py** - POST /api/ai/prompt, POST /api/ai/command
```
Source: ai.py - process_ai_prompt() and process_ai_command()
Action: Copy both functions to same file
Result: Single file with 2 related endpoints (~80 lines)
```

**top_picks.py** - GET /api/ai/top5-picks, GET /api/ai/top3-picks
```
Source: ai.py - top5_picks and top3_picks endpoints
Action: Copy both functions
Result: Single file with 2 related endpoints (~60 lines)
```

### Step 1.4: Create router.py for ai module

```python
from fastapi import APIRouter
from . import (
    strategies, market_analysis, trend_finder, breakout_detector,
    momentum_scanner, mean_reversion, gap_scanner, relative_strength,
    vwap_scanner, sr_bounce, sentiment_analysis, prompt_engine, top_picks
)

router = APIRouter(prefix="/api/ai", tags=["AI"])

# Include all sub-routers
router.include_router(strategies.router)
router.include_router(market_analysis.router)
router.include_router(trend_finder.router)
router.include_router(breakout_detector.router)
router.include_router(momentum_scanner.router)
router.include_router(mean_reversion.router)
router.include_router(gap_scanner.router)
router.include_router(relative_strength.router)
router.include_router(vwap_scanner.router)
router.include_router(sr_bounce.router)
router.include_router(sentiment_analysis.router)
router.include_router(prompt_engine.router)
router.include_router(top_picks.router)
```

### Step 1.5: Update main.py

**Change**:
```python
from routers import ai
...
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
```

**To**:
```python
from routers.ai import router as ai_router
...
app.include_router(ai_router)  # Router already has prefix
```

### Step 1.6: Validation

- [ ] All 27+ AI endpoints respond at original paths
- [ ] Response models match pre-refactor
- [ ] Cache operations functional
- [ ] Gemini API integration works
- [ ] Authentication still required where needed
- [ ] No circular imports
- [ ] All tests pass

---

## PHASE 2: CRITICAL REFACTORING - scanner.py (735 lines → 11 modules)

### Step 2.1: Create Directory Structure
```
Create: backend/routers/scanner/
Files to create:
  ├── __init__.py
  ├── base.py
  ├── strategies.py
  ├── reference_data.py
  ├── momentum.py
  ├── breakout.py
  ├── reversal.py
  ├── trendfinder.py
  ├── week52_breakout.py
  ├── presets.py
  ├── execution.py
  └── router.py
```

### Step 2.2: Extract Shared Code to base.py

**Instructions**:
1. Create `backend/routers/scanner/base.py`
2. Move from current scanner.py:
   - Global scanner components setup:
     ```python
     from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket
     from database import get_db, AsyncSessionLocal
     from models import User, ScannerPreset
     from utils.auth import get_current_user
     from services.memcached_client import get_cache
     import logging
     
     logger = logging.getLogger(__name__)
     
     # Global components
     StrategyRegistry = None
     ScannerEngine = None
     get_realtime_scanner_engine = None
     _scanner_available = False
     scanner = None
     
     try:
         from strategies import StrategyRegistry
         from core.scanner.scanner_engine import ScannerEngine
         from core.scanner.realtime_scanner_engine import get_realtime_scanner_engine
         _scanner_available = True
         if ScannerEngine is not None:
             scanner = ScannerEngine()
     except Exception as e:
         logger.warning(f"Scanner initialization failed: {e}")
     
     # Shared cache functions
     def get_cached_scanner_data(key: str):
         cache = get_cache()
         if not cache.is_available():
             return None
         try:
             return cache.get(key)
         except Exception as e:
             logger.error(f"Cache get error: {e}")
             return None
     
     def set_cached_scanner_data(key: str, data: any, ttl: int = 300):
         cache = get_cache()
         if not cache.is_available():
             return
         try:
             cache.set(key, data, ttl=ttl)
         except Exception as e:
             logger.error(f"Cache set error: {e}")
     ```

### Step 2.3: Migrate Endpoints

**strategies.py** - GET /api/scanner/strategies
```
Source: scanner.py get_strategies() endpoint
Copy endpoint function
Result: ~40 lines
```

**reference_data.py** - GET /api/scanner/indices, GET /api/scanner/timeframes
```
Source: scanner.py get_indices() and get_timeframes()
Copy both endpoint functions
Result: ~35 lines
```

**momentum.py** - GET /api/scanner/momentum, GET /api/scanner/momentum/status
```
Source: scanner.py get_momentum_scan() and get_momentum_status()
Copy both functions
Result: ~60 lines
```

**breakout.py** - GET /api/scanner/breakout
```
Source: scanner.py get_breakout_scan()
Copy function
Result: ~50 lines
```

**reversal.py** - GET /api/scanner/reversal
```
Source: scanner.py get_reversal_scan()
Copy function
Result: ~50 lines
```

**trendfinder.py** - GET /api/scanner/trendfinder
```
Source: scanner.py get_trendfinder_scan()
Copy function
Result: ~55 lines
```

**week52_breakout.py** - GET /api/scanner/week52-breakouts
```
Source: scanner.py get_week52_breakout_scan()
Copy function
Result: ~45 lines
```

**presets.py** - GET/POST/DELETE /api/scanner/presets/{preset_id}
```
Source: scanner.py preset management endpoints
Copy all preset functions:
  - get_presets()
  - create_preset()
  - delete_preset()
Result: ~70 lines
Dependencies: ScannerPreset model, database operations
```

**execution.py** - POST /api/scanner/run, GET /api/scanner/progress/{scan_id}
```
Source: scanner.py scan execution endpoints
Copy functions:
  - run_scan()
  - get_scan_progress()
Result: ~65 lines
Dependencies: BackgroundTasks, WebSocket
```

### Step 2.4: Create router.py

```python
from fastapi import APIRouter
from . import (
    strategies, reference_data, momentum, breakout, reversal,
    trendfinder, week52_breakout, presets, execution
)

router = APIRouter(prefix="/api/scanner", tags=["Scanner"])

router.include_router(strategies.router)
router.include_router(reference_data.router)
router.include_router(momentum.router)
router.include_router(breakout.router)
router.include_router(reversal.router)
router.include_router(trendfinder.router)
router.include_router(week52_breakout.router)
router.include_router(presets.router)
router.include_router(execution.router)
```

### Step 2.5: Update main.py

**Change**:
```python
from routers import scanner
...
app.include_router(scanner.router)
```

**To**:
```python
from routers.scanner import router as scanner_router
...
app.include_router(scanner_router)
```

### Step 2.6: Validation

- [ ] All 10+ scanner endpoints respond at original paths
- [ ] Preset database operations work
- [ ] Background scan tasks execute correctly
- [ ] WebSocket functionality intact
- [ ] Strategy registry loads properly
- [ ] Cache operations functional
- [ ] All tests pass

---

## PHASE 3: HIGH PRIORITY - analytics.py (390 lines → 9 modules)

### Step 3.1: Create Directory Structure
```
Create: backend/routers/analytics/
Files:
  ├── __init__.py
  ├── base.py
  ├── overview.py
  ├── momentum.py
  ├── volatility.py
  ├── correlation.py
  ├── support_resistance.py
  ├── query_engine.py
  ├── archive.py
  ├── indicators.py
  └── router.py
```

### Step 3.2: Extract to base.py

Move from analytics.py:
- DuckDB connection and setup
- Request/Response models
- Shared utility functions
- Database helpers

### Step 3.3: Migrate Endpoints

- **overview.py**: GET /api/analytics/overview
- **momentum.py**: GET /api/analytics/momentum/top
- **volatility.py**: GET /api/analytics/volatility/{symbol}
- **correlation.py**: POST /api/analytics/correlation
- **support_resistance.py**: GET /api/analytics/support-resistance/{symbol}
- **query_engine.py**: POST /api/analytics/query
- **archive.py**: All archive endpoints (list, stats, month, old, restore)
- **indicators.py**: POST /indicators/compute, GET /indicators/latest/{symbol}

### Step 3.4: Create router.py

Combine all sub-routers with proper prefix.

### Step 3.5: Update main.py

Update import and router registration.

### Step 3.6: Validation

- [ ] All 11+ analytics endpoints working
- [ ] DuckDB queries functional
- [ ] Archive operations work
- [ ] Indicator computation functional
- [ ] All tests pass

---

## PHASE 4: HIGH PRIORITY - market.py (328 lines → 7 modules)

### Step 4.1: Create Directory Structure
```
Create: backend/routers/market/
Files:
  ├── __init__.py
  ├── base.py
  ├── top_movers.py
  ├── nifty100_ranking.py
  ├── orchestrator.py
  ├── health.py
  ├── heatmap_data.py
  ├── sector_stocks.py
  └── router.py
```

### Step 4.2: Extract to base.py

Move from market.py:
- INDUSTRY_MAPPING constant
- SECTOR_MAP constant
- Shared utilities
- Common imports

### Step 4.3: Migrate Endpoints

- **top_movers.py**: GET /nifty100/top-movers, GET /top-movers (alias)
- **nifty100_ranking.py**: GET /nifty100/status
- **orchestrator.py**: GET /orchestrator/status
- **health.py**: GET /health
- **heatmap_data.py**: GET /heatmap
- **sector_stocks.py**: GET /sector-stocks/{sector_name}

### Step 4.4: Create router.py

Combine all routers.

### Step 4.5: Update main.py

Update imports and registration.

### Step 4.6: Validation

- [ ] All 6+ market endpoints working
- [ ] Upstox integration functional
- [ ] Health checks responsive
- [ ] All tests pass

---

## PHASE 5: MEDIUM PRIORITY - trading.py (229 lines → 5 modules)

### Step 5.1: Create Directory Structure
```
Create: backend/routers/trading/
Files:
  ├── __init__.py
  ├── base.py
  ├── dashboard.py
  ├── health.py
  ├── market_data.py
  ├── gainers_losers.py
  └── router.py
```

### Step 5.2: Extract & Migrate

Move shared code to base.py, then:
- **dashboard.py**: GET /dashboard
- **health.py**: GET /health
- **market_data.py**: GET /market-indices, GET /instruments
- **gainers_losers.py**: GET /top-gainers, GET /gainers-losers

### Step 5.3: Create router.py & Update main.py

### Step 5.4: Validation

- [ ] All 6 endpoints working
- [ ] Dashboard calculations correct
- [ ] Market data fetching works
- [ ] All tests pass

---

## PHASE 6: MEDIUM PRIORITY - upstox.py (200+ lines → 5 modules)

### Step 6.1: Create Directory Structure
```
Create: backend/routers/upstox/
Files:
  ├── __init__.py
  ├── base.py
  ├── auth.py
  ├── user.py
  ├── portfolio.py
  ├── quotes.py
  └── router.py
```

### Step 6.2: Extract & Migrate

- **auth.py**: GET /auth-url, POST /callback
- **user.py**: GET /user-profile, GET /status
- **portfolio.py**: GET /portfolio, GET /positions
- **quotes.py**: GET /market-quote/{symbol}

### Step 6.3: Create router.py & Update main.py

### Step 6.4: Validation

- [ ] All 7 endpoints working
- [ ] Upstox auth flow intact
- [ ] Portfolio data fetching works
- [ ] All tests pass

---

## PHASE 7: TESTING & VALIDATION

### Step 7.1: Unit Testing

**For each module, verify**:
- Endpoint responds at correct path
- Response schema matches original
- All dependencies injectable
- Error handling functional

**Commands**:
```bash
pytest backend/routers/ai/ -v
pytest backend/routers/scanner/ -v
pytest backend/routers/analytics/ -v
pytest backend/routers/market/ -v
pytest backend/routers/trading/ -v
pytest backend/routers/upstox/ -v
```

### Step 7.2: Integration Testing

**Verify**:
- main.py starts without errors
- All routers registered correctly
- No circular imports
- API responds to requests

**Commands**:
```bash
python -m py_compile backend/main.py
python -m py_compile backend/routers/*/router.py
```

### Step 7.3: API Endpoint Testing

**Test each endpoint**:
```bash
# AI endpoints
curl http://localhost:8000/api/ai/strategies
curl http://localhost:8000/api/ai/market-analysis
curl http://localhost:8000/api/ai/trend-finder

# Scanner endpoints
curl http://localhost:8000/api/scanner/strategies
curl http://localhost:8000/api/scanner/momentum

# Analytics endpoints
curl http://localhost:8000/api/analytics/overview

# Market endpoints
curl http://localhost:8000/api/market/nifty100/top-movers

# Trading endpoints
curl http://localhost:8000/api/trading/dashboard

# Upstox endpoints
curl http://localhost:8000/api/upstox/status
```

### Step 7.4: Code Quality

**Verify**:
- No unused imports
- Consistent naming
- Proper error handling
- Logging functional

**Commands**:
```bash
pylint backend/routers/ --disable=all --enable=unused-import
black backend/routers/ --check
```

### Step 7.5: Documentation

**Update**:
- API documentation
- README with new structure
- Module-level docstrings

---

## CRITICAL REQUIREMENTS

### API Backward Compatibility
✓ All endpoints must respond at original paths
✓ Response schemas must be identical
✓ Status codes must match
✓ Error messages must match

### Code Quality Standards
✓ No circular imports
✓ Average file size <100 lines
✓ Clear module responsibilities
✓ Proper error handling
✓ Type hints preserved

### Testing Requirements
✓ All existing tests pass
✓ 80%+ code coverage minimum
✓ No regressions
✓ Performance unaffected

### Git Workflow
✓ Create feature branch: `refactor/modularize-routers`
✓ Commit per phase
✓ Descriptive commit messages
✓ No squashing during development

---

## VALIDATION CHECKLIST

### After Each Phase
- [ ] All endpoints tested
- [ ] No broken imports
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Code reviewed

### Final Validation (Phase 7)
- [ ] All 70+ endpoints working
- [ ] Zero circular imports
- [ ] Zero code duplication
- [ ] >80% test coverage
- [ ] All quality checks pass
- [ ] Documentation complete
- [ ] Performance baseline met

---

## SUCCESS CRITERIA

### Quantitative
- **Lines per file**: Average <100 (from 350)
- **Cyclomatic complexity**: <10 per file (from 20+)
- **Code duplication**: 0% (from 20%)
- **Test coverage**: >80% (from 40%)
- **Endpoints working**: 100% (all 70+)

### Qualitative
- **Code organization**: Clear and logical
- **Maintainability**: High - easy to find and modify code
- **Scalability**: High - new features don't bloat files
- **Team collaboration**: High - minimal merge conflicts
- **Onboarding**: Fast - new devs understand structure quickly

---

## TROUBLESHOOTING GUIDE

### Issue: Circular Imports
**Cause**: Module importing from router.py
**Solution**: Structure as: base.py → modules → router.py
**Verify**: `python -c "import backend.routers.ai"`

### Issue: Missing Imports
**Cause**: Shared code not fully moved to base.py
**Solution**: Review import errors, move utility functions
**Verify**: All tests pass

### Issue: Endpoints Not Responding
**Cause**: Router not registered or prefix issues
**Solution**: Check main.py, verify include_router() calls
**Verify**: `curl` test each endpoint

### Issue: Database Errors
**Cause**: Session injection problems
**Solution**: Ensure `Depends(get_db)` in function signature
**Verify**: Database tests pass

### Issue: Authentication Failures
**Cause**: Auth dependency missing
**Solution**: Import auth functions from base.py
**Verify**: Protected endpoints require auth

---

## IMPLEMENTATION TIPS

### For Antigravity IDE
1. Process one phase at a time
2. Don't skip validation steps
3. Review generated code carefully
4. Test after each phase
5. Keep original files until Phase 7 complete

### For Developers
1. Create branches per phase
2. Commit frequently
3. Run tests often
4. Document changes
5. Ask for help if stuck

### For QA/Testing
1. Start simple with one module
2. Progress through all phases
3. Run integration tests
4. Verify API compatibility
5. Check performance

---

## DELIVERABLES SUMMARY

### Code
- ✓ 43 modular files (vs 6 monolithic)
- ✓ Shared base.py in each module
- ✓ Module router.py combining sub-routers
- ✓ Updated main.py with new imports
- ✓ Original files archived

### Tests
- ✓ All existing tests passing
- ✓ 80%+ code coverage
- ✓ No regressions
- ✓ Integration tests green

### Documentation
- ✓ API docs updated
- ✓ README revised
- ✓ Module docstrings added
- ✓ Architecture documented

---

## TIMELINE

```
Phase 1 (Critical):    90 minutes (ai.py + scanner.py)
Phase 2 (Critical):    Already counted above
Phase 3 (High):        90 minutes (analytics.py + market.py)
Phase 4 (High):        Already counted above
Phase 5 (Medium):      60 minutes (trading.py + upstox.py)
Phase 6 (Medium):      Already counted above
Phase 7 (Testing):     60 minutes (validation)
                       ___________
TOTAL:                5-6 hours

(With proper Antigravity IDE prompting and automation)
```

---

## ROLLBACK PLAN (If Issues Arise)

1. Keep original files until Phase 7 passes
2. Maintain git history for any commit
3. If critical issues:
   - `git revert` last commit
   - Revert to backup original files
   - Diagnose issue
   - Restart with fixes

4. Testing before full commit:
   - Test each phase independently
   - Don't proceed until phase passes all checks
   - Run full integration test before pushing

---

## AUTOMATION & EFFICIENCY

### What Antigravity IDE Will Handle
- File creation and structure
- Code migration and refactoring
- Import reorganization
- Router combination
- Basic syntax fixes

### What Requires Manual Review
- Verify endpoint functionality
- Check response schemas match
- Validate authentication flows
- Test error handling
- Review code organization

### Expected Productivity Gains
- **Manual refactoring**: 12-16 hours
- **With Antigravity IDE**: 4-6 hours
- **Savings**: 6-10 hours per cycle
- **Ongoing benefit**: 5-10x faster development

---

## NEXT STEPS

1. ✅ Review this master prompt
2. ✅ Approve refactoring approach
3. **Execute Phase 1** (ai.py refactoring)
4. **Execute Phase 2** (scanner.py refactoring)
5. **Execute Phase 3-6** (remaining modules)
6. **Execute Phase 7** (testing & validation)
7. **Deploy** (merge to main branch)
8. **Monitor** (watch for any issues)

---

## SUCCESS CONFIRMATION

After completing all phases, you will have:

✅ 43 focused, modular files (from 6 monolithic files)  
✅ Average 65 lines per file (from 350+ lines)  
✅ 100% API backward compatibility  
✅ 5-10x development productivity improvement  
✅ Easier feature development and maintenance  
✅ Better code organization and testing  
✅ Scalable for future growth  

**Estimated total effort: 5-6 hours with Antigravity IDE**

---

## READY TO BEGIN?

This master prompt contains everything needed to refactor your backend API into a modular, maintainable architecture.

**Start with Phase 1** and proceed sequentially through all phases.

**Expected outcome**: Production-ready, fully modularized API backend.

**Questions?** Refer to the troubleshooting section or individual phase requirements.

🚀 **Ready to execute this comprehensive refactoring!**

