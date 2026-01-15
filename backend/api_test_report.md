# API Test Summary

**Test Execution Date:** 2026-01-11T17:27:01Z

## Overview

| Metric | Value |
|--------|-------|
| Total APIs Tested | 9 |
| APIs Passed | 9 |
| APIs Failed | 0 |
| APIs Partially Passed | 0 |
| **Overall Pass Rate** | **100.0%** |

## Failure Breakdown

| Category | Count |
|----------|-------|
| *(No failures)* | 0 |

## Performance Metrics

- **Average Response Time:** 21.07 ms
- **P95 Response Time:** 45.17 ms
- **Slowest API:** `/api/v3/scanner/snapshots` (45.17 ms)

## Detailed Results

| Endpoint | Method | Test Type | Status | Code | Time (ms) |
|----------|--------|-----------|--------|------|-----------|
| `/health` | GET | happy_path |  | 200 | 26.44 |
| `/ready` | GET | happy_path |  | 200 | 3.81 |
| `/api/trading/market-indices` | GET | happy_path |  | 200 | 21.5 |
| `/api/market/nifty100/top-movers` | GET | happy_path |  | 200 | 17.97 |
| `/api/v3/scanner/snapshots` | GET | happy_path |  | 200 | 45.17 |
| `/api/v3/scanner/status` | GET | happy_path |  | 200 | 29.08 |
| `/api/nonexistent/endpoint` | GET | negative_404 |  | 404 | 6.05 |
| `/api/auth/login` | POST | negative_type |  | 422 | 25.8 |
| `/api/auth/signup` | POST | error_format |  | 422 | 13.77 |