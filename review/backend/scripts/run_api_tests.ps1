# QuantAI India - Backend API Test Script (PowerShell)
# Tests all API endpoints and generates summary report

$BaseUrl = "http://localhost:8000"
$TimeoutSec = 30

# Test results collection
$results = @()

function Test-Endpoint {
    param(
        [string]$Method,
        [string]$Endpoint,
        [string]$Description,
        [string]$Module,
        [int]$ExpectedCode = 200,
        [hashtable]$Body = $null
    )
    
    $url = "$BaseUrl$Endpoint"
    $startTime = Get-Date
    
    try {
        if ($Method -eq "GET") {
            $response = Invoke-WebRequest -Uri $url -Method $Method -TimeoutSec $TimeoutSec -ErrorAction Stop
        } else {
            $jsonBody = $Body | ConvertTo-Json
            $response = Invoke-WebRequest -Uri $url -Method $Method -Body $jsonBody -ContentType "application/json" -TimeoutSec $TimeoutSec -ErrorAction Stop
        }
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMilliseconds
        
        $status = if ($response.StatusCode -eq $ExpectedCode) { "PASSED" } else { "FAILED" }
        
        $sampleLen = [math]::Min(300, $response.Content.Length)
        
        return @{
            Endpoint = $Endpoint
            Method = $Method
            Description = $Description
            Module = $Module
            Status = $status
            StatusCode = $response.StatusCode
            ExpectedCode = $ExpectedCode
            ResponseTimeMs = [math]::Round($duration)
            ResponseSample = $response.Content.Substring(0, $sampleLen)
            Error = ""
        }
    }
    catch {
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMilliseconds
        
        $errorMsg = $_.Exception.Message
        $statusCode = $null
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        
        return @{
            Endpoint = $Endpoint
            Method = $Method
            Description = $Description
            Module = $Module
            Status = "FAILED"
            StatusCode = $statusCode
            ExpectedCode = $ExpectedCode
            ResponseTimeMs = [math]::Round($duration)
            ResponseSample = ""
            Error = $errorMsg
        }
    }
}

$separator = "=" * 80
Write-Host $separator
Write-Host "QuantAI India - Comprehensive E2E API Testing"
Write-Host $separator
Write-Host "Base URL: $BaseUrl"
Write-Host ("Started: " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Write-Host ""

# Test all endpoints
Write-Host "Testing Core Endpoints..."
$results += Test-Endpoint -Method "GET" -Endpoint "/" -Description "Root endpoint" -Module "Core"
$results += Test-Endpoint -Method "GET" -Endpoint "/health" -Description "Health check" -Module "Core"

Write-Host "Testing Trading Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/trading/health" -Description "Trading health check" -Module "Trading"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/trading/market-indices" -Description "Market indices" -Module "Trading"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/trading/instruments" -Description "Trading instruments" -Module "Trading"

Write-Host "Testing Upstox Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/upstox/status" -Description "Upstox connection status" -Module "Upstox"

Write-Host "Testing Scanner Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/scanner/strategies" -Description "Scanner strategies" -Module "Scanner"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/scanner/indices" -Description "Available indices" -Module "Scanner"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/scanner/timeframes" -Description "Available timeframes" -Module "Scanner"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/scanner/momentum" -Description "Momentum scanner" -Module "Scanner"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/scanner/breakout" -Description "Breakout scanner" -Module "Scanner"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/scanner/reversal" -Description "Reversal scanner" -Module "Scanner"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/scanner/presets" -Description "Scanner presets" -Module "Scanner"

Write-Host "Testing AI Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/strategies" -Description "AI strategies list" -Module "AI"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/trend-finder" -Description "Trend Finder AI" -Module "AI"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/breakout-detector" -Description "Breakout Detector" -Module "AI"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/top5-picks" -Description "Top 5 stock picks" -Module "AI"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/momentum" -Description "Momentum scanner" -Module "AI"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/mean-reversion" -Description "Mean reversion scanner" -Module "AI"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/gap-scanner" -Description "Gap scanner" -Module "AI"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/relative-strength" -Description "Relative strength" -Module "AI"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/vwap" -Description "VWAP scanner" -Module "AI"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/sr-bounce" -Description "Support/Resistance bounce" -Module "AI"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/ai/market-analysis" -Description "Market analysis" -Module "AI"

Write-Host "Testing Quant Bot Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/quant/strategies" -Description "Quant strategies" -Module "Quant"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/quant/symbols" -Description "Available symbols" -Module "Quant"

Write-Host "Testing Walk-Forward Backtest Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/v1/walk-forward/strategies" -Description "WF strategies" -Module "WalkForward"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/v1/walk-forward/presets" -Description "WF presets" -Module "WalkForward"

Write-Host "Testing Experiment Lab Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/v1/experiment-lab/strategies" -Description "Lab strategies" -Module "ExperimentLab"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/v1/experiment-lab/symbols" -Description "Lab symbols" -Module "ExperimentLab"

Write-Host "Testing Backtest Strategies Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/v1/backtest/strategies/list" -Description "Backtest strategy list" -Module "BacktestStrategies"

Write-Host "Testing Market Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/market/orchestrator/status" -Description "Orchestrator status" -Module "Market"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/market/health" -Description "Market health" -Module "Market"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/market/top-movers" -Description "Top movers" -Module "Market"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/market/heatmap" -Description "Sector heatmap" -Module "Market"

Write-Host "Testing Heatmap Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/heatmap/sectors" -Description "Sector heatmap data" -Module "Heatmap"

Write-Host "Testing Engine Performance Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/engines/performance" -Description "Engine performance metrics" -Module "Engines"

Write-Host "Testing Analytics Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/analytics/overview" -Description "Analytics overview" -Module "Analytics"
$results += Test-Endpoint -Method "GET" -Endpoint "/api/analytics/momentum/top" -Description "Top momentum stocks" -Module "Analytics"

Write-Host "Testing Algorithms Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/algorithms" -Description "List algorithms" -Module "Algorithms"

Write-Host "Testing Orders Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/orders" -Description "List orders" -Module "Orders"

Write-Host "Testing Risk Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/risk/" -Description "Risk settings" -Module "Risk"

Write-Host "Testing Settings Module..."
$results += Test-Endpoint -Method "GET" -Endpoint "/api/settings" -Description "User settings" -Module "Settings"

Write-Host ""
Write-Host "All tests completed!"
Write-Host ""

# Generate report
$total = $results.Count
$passed = ($results | Where-Object { $_.Status -eq "PASSED" }).Count
$failed = ($results | Where-Object { $_.Status -eq "FAILED" }).Count
$successRate = if ($total -gt 0) { [math]::Round(($passed / $total) * 100, 1) } else { 0 }
$avgTime = if ($passed -gt 0) { [math]::Round(($results | Where-Object { $_.Status -eq "PASSED" } | Measure-Object -Property ResponseTimeMs -Average).Average) } else { 0 }

$longSep = "=" * 100
$shortSep = "-" * 62

$reportBuilder = New-Object System.Text.StringBuilder
[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine("  QUANTAI INDIA - COMPREHENSIVE E2E API TEST REPORT")
[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine(("Generated: " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')))
[void]$reportBuilder.AppendLine("Base URL: $BaseUrl")
[void]$reportBuilder.AppendLine("")
[void]$reportBuilder.AppendLine("+--------------------------------------------------+")
[void]$reportBuilder.AppendLine("|  OVERALL STATISTICS                              |")
[void]$reportBuilder.AppendLine("+--------------------------------------------------+")
[void]$reportBuilder.AppendLine(("|  Total Tests:        {0,6}                      |" -f $total))
[void]$reportBuilder.AppendLine(("|  Passed:             {0,6}                       |" -f $passed))
[void]$reportBuilder.AppendLine(("|  Failed:             {0,6}                       |" -f $failed))
[void]$reportBuilder.AppendLine(("|  Success Rate:       {0,5}%                      |" -f $successRate))
[void]$reportBuilder.AppendLine(("|  Avg Response Time:  {0,6}ms                    |" -f $avgTime))
[void]$reportBuilder.AppendLine("+--------------------------------------------------+")
[void]$reportBuilder.AppendLine("")
[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine("  MODULE-WISE BREAKDOWN")
[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine("")

$moduleStats = $results | Group-Object -Property Module | ForEach-Object {
    $modulePassed = ($_.Group | Where-Object { $_.Status -eq "PASSED" }).Count
    $moduleFailed = ($_.Group | Where-Object { $_.Status -eq "FAILED" }).Count
    $moduleTotal = $_.Count
    $moduleRate = if ($moduleTotal -gt 0) { [math]::Round(($modulePassed / $moduleTotal) * 100, 1) } else { 0 }
    [PSCustomObject]@{
        Module = $_.Name
        Total = $moduleTotal
        Passed = $modulePassed
        Failed = $moduleFailed
        Rate = $moduleRate
    }
}

[void]$reportBuilder.AppendLine(("{0,-20} {1,6} {2,8} {3,8} {4,10}" -f "Module", "Total", "Passed", "Failed", "Rate"))
[void]$reportBuilder.AppendLine($shortSep)
foreach ($stat in ($moduleStats | Sort-Object -Property Module)) {
    $icon = if ($stat.Failed -eq 0) { "[OK]" } else { "[FAIL]" }
    [void]$reportBuilder.AppendLine(("{0,-20} {1,6} {2,8} {3,8} {4,8}% {5}" -f $stat.Module, $stat.Total, $stat.Passed, $stat.Failed, $stat.Rate, $icon))
}

[void]$reportBuilder.AppendLine("")
[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine(("  PASSED TESTS ({0})" -f $passed))
[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine("")

foreach ($r in ($results | Where-Object { $_.Status -eq "PASSED" })) {
    [void]$reportBuilder.AppendLine(("[PASSED] {0} {1}" -f $r.Method, $r.Endpoint))
    [void]$reportBuilder.AppendLine(("  Module: {0}" -f $r.Module))
    [void]$reportBuilder.AppendLine(("  Description: {0}" -f $r.Description))
    [void]$reportBuilder.AppendLine(("  Status Code: {0} (Expected: {1})" -f $r.StatusCode, $r.ExpectedCode))
    [void]$reportBuilder.AppendLine(("  Response Time: {0}ms" -f $r.ResponseTimeMs))
    [void]$reportBuilder.AppendLine("")
}

if ($failed -gt 0) {
    [void]$reportBuilder.AppendLine($longSep)
    [void]$reportBuilder.AppendLine(("  FAILED TESTS ({0})" -f $failed))
    [void]$reportBuilder.AppendLine($longSep)
    [void]$reportBuilder.AppendLine("")
    
    foreach ($r in ($results | Where-Object { $_.Status -eq "FAILED" })) {
        [void]$reportBuilder.AppendLine(("[FAILED] {0} {1}" -f $r.Method, $r.Endpoint))
        [void]$reportBuilder.AppendLine(("  Module: {0}" -f $r.Module))
        [void]$reportBuilder.AppendLine(("  Description: {0}" -f $r.Description))
        [void]$reportBuilder.AppendLine(("  Expected Code: {0}" -f $r.ExpectedCode))
        [void]$reportBuilder.AppendLine(("  Actual Code: {0}" -f $r.StatusCode))
        $errLen = [math]::Min(200, $r.Error.Length)
        [void]$reportBuilder.AppendLine(("  Error: {0}" -f $r.Error.Substring(0, $errLen)))
        [void]$reportBuilder.AppendLine("")
    }
}

[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine("  PERFORMANCE ANALYSIS")
[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine("")

$slowest = $results | Where-Object { $_.Status -eq "PASSED" } | Sort-Object -Property ResponseTimeMs -Descending | Select-Object -First 10
[void]$reportBuilder.AppendLine("Top 10 Slowest Endpoints:")
[void]$reportBuilder.AppendLine(("-" * 60))
$i = 1
foreach ($r in $slowest) {
    [void]$reportBuilder.AppendLine(("  {0}. {1,-45} {2,7}ms" -f $i, $r.Endpoint, $r.ResponseTimeMs))
    $i++
}

[void]$reportBuilder.AppendLine("")
[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine("  RECOMMENDATIONS")
[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine("")

if ($failed -gt 0) {
    [void]$reportBuilder.AppendLine("Issues to Address:")
    foreach ($r in ($results | Where-Object { $_.Status -eq "FAILED" })) {
        $errLen = [math]::Min(80, $r.Error.Length)
        [void]$reportBuilder.AppendLine(("  - Fix {0}: {1}" -f $r.Endpoint, $r.Error.Substring(0, $errLen)))
    }
    [void]$reportBuilder.AppendLine("")
}

if ($successRate -ge 95) {
    [void]$reportBuilder.AppendLine(("Excellent! API is in great shape with {0}% success rate." -f $successRate))
} elseif ($successRate -ge 80) {
    [void]$reportBuilder.AppendLine("Good! API is mostly working but needs some attention.")
} else {
    [void]$reportBuilder.AppendLine("Critical! Many endpoints are failing. Immediate attention required.")
}

[void]$reportBuilder.AppendLine("")
[void]$reportBuilder.AppendLine($longSep)
[void]$reportBuilder.AppendLine("  END OF REPORT")
[void]$reportBuilder.AppendLine($longSep)

$report = $reportBuilder.ToString()

# Output report
Write-Host $report

# Save to file
$report | Out-File -FilePath "api_test_report.txt" -Encoding utf8
Write-Host ""
Write-Host "Report saved to: api_test_report.txt"
