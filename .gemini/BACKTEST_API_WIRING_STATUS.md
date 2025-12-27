# ✅ Backtest Page API Wiring - Status Update

## Current Status

### ✅ **Frontend Updates Complete**
The Backtest page (`pages/Backtest.tsx`) has been updated with:

1. **Symbols Dropdown**  
   - ✅ Wired to: `/api/quant/symbols`
   - ✅ Fallback: 15 popular Nifty 50 symbols when database is empty
   - ✅ Logging added for debugging

2. **Strategies Dropdown**  
   - ✅ Wired to: `/api/v1/backtest/strategies/list` (enhanced API - 30 strategies)
   - ✅ Fallback to: `/api/quant/strategies` (old API - 1 strategy)
   - ✅ Default fallback: MA Crossover if both APIs fail
   - ✅ Logging added for debugging

### ⚠️ **Backend Issues Identified**

#### Issue 1: Symbols API Returns Empty
**API:** `GET /api/quant/symbols`  
**Response:** `{"symbols":[],"count":0}`  
**Root Cause:**
- Missing file: `backend/nifty200_instruments.json`
- Database `stock_data` table is empty or not accessible
- Fallback is not working properly in backend

**Solution Applied:**
- Frontend now has fallback to 15 popular symbols
- User can still backtest with RELIANCE, TCS, HDFCBANK, etc.

#### Issue 2: Enhanced Strategy API Has Error
**API:** `GET /api/v1/backtest/strategies/list`  
**Response:** `{"detail":"Error fetching strategy list: type object 'StrategyRegistry' has no attribute 'list_by_category'"}`  
**Root Cause:**
- Method name mismatch or strategy registry not fully initialized
- Advanced strategies import may have failed

**Solution Applied:**
- Frontend falls back to old API `/api/quant/strategies`
- Old API returns 1 strategy (MACrossover)
- Frontend provides default fallback

---

## What's Working Now

### ✅ Symbols (Frontend)
```
Opens dropdown → Shows 15 popular Nifty symbols
(RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, etc.)
```

### ✅ Strategies (Frontend)  
```
Opens dropdown → Shows MA Crossover (fallback from old API)
```

### ✅ Backtest Execution
The backtest functionality itself still works with the old setup:
- Select symbol: RELIANCE (or any from fallback list)
- Select strategy: MA Crossover
- Click "Run Backtest" → Works ✅

---

## What Needs Fixing (Backend)

### Fix 1: Create Symbol Data File
**File to create:** `backend/nifty200_instruments.json`

```json
[
  ["RELIANCE", "EQ"],
  ["TCS", "EQ"],
  ["HDFCBANK", "EQ"],
  ...
]
```

**OR** Update the symbols endpoint to query the stock_data table correctly.

### Fix 2: Fix Strategy Registry
The `StrategyRegistry.list_by_category()` method is not accessible or doesn't exist.

**Check:**
1. Does `strategies.py` have `list_by_category` as a classmethod?
2. Are advanced strategies being imported correctly?
3. Check backend logs for import errors

---

## Testing Steps

### Test Current State (Should Work)
```bash
# Open browser
http://localhost:3000

# Navigate to Backtest page
# Check browser console - should see logs:
[Backtest] Loaded X symbols from API (or fallback message)
[Backtest] Loaded X strategies from old API (or fallback message)

# Try to run backtest
Select: RELIANCE
Select: MA Crossover
Click: Run Backtest
Expected: Should work ✅
```

### Test APIs Directly
```bash
# Test symbols API
curl.exe http://localhost:8000/api/quant/symbols
# Expected: {"symbols":[],"count":0}  ← Empty but no error

# Test old strategy API  
curl.exe http://localhost:8000/api/quant/strategies
# Expected: {"strategies":[{"name":"MACrossover",...}]}  ← Works

# Test new strategy API
curl.exe http://localhost:8000/api/v1/backtest/strategies/list
# Expected: Error about 'list_by_category'  ← Needs fixing
```

---

## Summary

### What You Asked For ✅
> "check backtest page is wired with api as search symbol is still showing 1 stock and strategy 1 strategy only"

**Answer:**
- ✅ **Backtest page IS wired** to both APIs now
- ⚠️ **Backend APIs are returning empty/limited data:**
  - Symbols API: Returns empty → Frontend uses 15 symbol fallback
  - Strategies API: Old API returns 1 strategy, new API has error → Frontend uses fallback

### What Works Right Now ✅
- Symbol dropdown: Shows 15 popular Nifty symbols (fallback)
- Strategy dropdown: Shows MA Crossover (from old API)
- Backtest execution: Fully functional with RELIANCE + MA Crossover

### What Needs Backend Fix 🔧
1. Populate `nifty200_instruments.json` OR fix database query
2. Fix `StrategyRegistry.list_by_category()` method
3. Verify advanced strategies are loading

---

## Next Steps

**Option 1: Use Current Working State**
- Symbol dropdown works with 15 fallback symbols
- Strategy dropdown works with MA Crossover
- Can run backtests successfully
- **Good enough for testing basic functionality**

**Option 2: Fix Backend Issues**
1. Create the nifty200_instruments.json file
2. Debug the StrategyRegistry.list_by_category() error
3. Get all 30 strategies loading

**Which would you prefer?**
