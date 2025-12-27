# Backtest Enhancement API Testing Script
# =========================================
# Run this to verify all new APIs are working correctly

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Backtest Enhancement - API Testing Suite" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"

# Test 1: List all strategies
Write-Host "[Test 1] Fetching all strategies..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/backtest/strategies/list" -Method Get
    Write-Host "✓ Success: Found $($response.total_strategies) strategies" -ForegroundColor Green
    Write-Host "  Tier 1: $($response.tiers.tier_1) strategies" -ForegroundColor Gray
    Write-Host "  Tier 2: $($response.tiers.tier_2) strategies" -ForegroundColor Gray
    Write-Host "  Tier 3: $($response.tiers.tier_3) strategies" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 2: Filter by tier
Write-Host "[Test 2] Fetching Tier 2 strategies only..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/backtest/strategies/list?tier=tier_2" -Method Get
    Write-Host "✓ Success: Found $($response.total_strategies) Tier 2 strategies" -ForegroundColor Green
    foreach ($category in $response.categories) {
        Write-Host "  Category: $($category.category_name)" -ForegroundColor Gray
        foreach ($strategy in $category.strategies) {
            Write-Host "    - $($strategy.display_name)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 3: Filter implemented only
Write-Host "[Test 3] Fetching implemented strategies only..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/backtest/strategies/list?implemented_only=true" -Method Get
    Write-Host "✓ Success: Found $($response.total_strategies) implemented strategies" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 4: Get strategies by tier
Write-Host "[Test 4] Fetching strategies organized by tier..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/backtest/strategies/by-tier" -Method Get
    Write-Host "✓ Success: Tier organization retrieved" -ForegroundColor Green
    Write-Host "  Tier 1: $($response.tier_1.name)" -ForegroundColor Gray
    Write-Host "  Tier 2: $($response.tier_2.name)" -ForegroundColor Gray
    Write-Host "  Tier 3: $($response.tier_3.name)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 5: Get specific strategy details
Write-Host "[Test 5] Fetching details for 'macd_crossover' strategy..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/backtest/strategies/macd_crossover" -Method Get
    Write-Host "✓ Success: Strategy details retrieved" -ForegroundColor Green
    Write-Host "  Name: $($response.display_name)" -ForegroundColor Gray
    Write-Host "  Category: $($response.category)" -ForegroundColor Gray
    Write-Host "  Tier: $($response.tier)" -ForegroundColor Gray
    Write-Host "  Implemented: $($response.is_implemented)" -ForegroundColor Gray
    Write-Host "  Parameters: $($response.parameters.Keys.Count)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 6: Search strategies
Write-Host "[Test 6] Searching for 'MACD' strategies..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/backtest/strategies/search?query=macd&limit=10" -Method Get
    Write-Host "✓ Success: Found $($response.total_matches) matching strategies" -ForegroundColor Green
    foreach ($result in $response.results) {
        Write-Host "  - $($result.display_name) (score: $($result.relevance_score))" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 7: Verify symbol endpoint (existing)
Write-Host "[Test 7] Fetching available symbols for 1D timeframe..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/walk-forward/symbols?timeframe=1D" -Method Get
    Write-Host "✓ Success: Found $($response.symbols.Count) symbols" -ForegroundColor Green
    Write-Host "  Sample symbols: $($response.symbols[0..4] -join ', ')..." -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 8: Check API docs
Write-Host "[Test 8] Verifying API documentation..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/docs" -Method Get -ErrorAction SilentlyContinue
    Write-Host "✓ Success: API docs available at $baseUrl/docs" -ForegroundColor Green
} catch {
    Write-Host "⚠ Note: Visit $baseUrl/docs in browser for interactive API documentation" -ForegroundColor Yellow
}

Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Testing Complete!" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

Write-Host "Next Steps:" -ForegroundColor Magenta
Write-Host "1. Open frontend: http://localhost:3000" -ForegroundColor White
Write-Host "2. Navigate to Walk-Forward Backtest page" -ForegroundColor White
Write-Host "3. Verify new strategy selection panel loads" -ForegroundColor White
Write-Host "4. Test symbol search with typeahead" -ForegroundColor White
Write-Host "5. Select strategies and run backtest`n" -ForegroundColor White

Write-Host "API Documentation: $baseUrl/docs`n" -ForegroundColor Cyan
