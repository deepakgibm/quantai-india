"""
QuantAI Comprehensive API Tester
Production-grade Postman-style API validation with formal test summary.

Features:
- OpenAPI spec-driven API discovery
- Happy path and negative test cases
- Auth flow testing (JWT)
- Performance metrics (P95 latency, SLA breach)
- Formal markdown and JSON reports
"""

import requests
import json
import time
import statistics
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
MAX_RETRIES = 2
SLA_THRESHOLD_MS = 2000  # Flag APIs >2000ms

# Test user credentials for auth testing
TEST_USER = {
    "email": "apitest@quantai.local",
    "username": "apitester",
    "full_name": "API Test User",
    "password": "TestPass123!"
}

# =============================================================================
# Enums and Data Classes
# =============================================================================

class TestStatus(Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    SKIP = "SKIP"


class ErrorCategory(Enum):
    VALIDATION = "422_validation"
    ROUTING = "404_routing"
    AUTH = "401_403_auth"
    SERVER = "500_503_server"
    SCHEMA = "schema_mismatch"
    PERFORMANCE = "performance_sla"
    TIMEOUT = "timeout"


@dataclass
class ApiEndpoint:
    """Represents an API endpoint from OpenAPI spec."""
    path: str
    method: str
    operation_id: str
    tags: List[str]
    requires_auth: bool
    request_body_schema: Optional[Dict] = None
    parameters: List[Dict] = field(default_factory=list)
    expected_status: int = 200


@dataclass
class TestResult:
    """Result of a single API test."""
    endpoint: str
    method: str
    test_type: str  # happy_path, negative_missing_field, negative_auth, etc.
    status: TestStatus
    status_code: Optional[int]
    response_time_ms: float
    error_category: Optional[ErrorCategory] = None
    error_message: Optional[str] = None
    response_snippet: Optional[str] = None


@dataclass
class TestSummary:
    """Complete test summary report."""
    execution_date: str
    total_apis: int
    apis_passed: int
    apis_failed: int
    apis_partial: int
    pass_rate: float
    failure_breakdown: Dict[str, int]
    avg_response_time_ms: float
    p95_response_time_ms: float
    slowest_api: str
    slowest_time_ms: float
    high_risk_findings: List[str]
    recommendations: List[str]
    detailed_results: List[Dict]


# =============================================================================
# OpenAPI Parser
# =============================================================================

def parse_openapi_spec() -> List[ApiEndpoint]:
    """Parse OpenAPI spec to extract all endpoints."""
    endpoints = []
    
    try:
        # Try to fetch from live server
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=10)
        if response.status_code == 200:
            spec = response.json()
        else:
            # Fallback to local file
            with open("../openapi.json", "r") as f:
                spec = json.load(f)
    except Exception as e:
        print(f"  ⚠️ Could not load OpenAPI spec: {e}")
        # Use hardcoded critical endpoints
        return get_fallback_endpoints()
    
    paths = spec.get("paths", {})
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                # Check if auth required
                security = details.get("security", [])
                requires_auth = len(security) > 0
                
                # Check for request body
                request_body = details.get("requestBody", {})
                body_schema = None
                if request_body:
                    content = request_body.get("content", {})
                    json_content = content.get("application/json", {})
                    body_schema = json_content.get("schema", {})
                
                endpoint = ApiEndpoint(
                    path=path,
                    method=method.upper(),
                    operation_id=details.get("operationId", ""),
                    tags=details.get("tags", []),
                    requires_auth=requires_auth,
                    request_body_schema=body_schema,
                    parameters=details.get("parameters", [])
                )
                endpoints.append(endpoint)
    
    return endpoints


def get_fallback_endpoints() -> List[ApiEndpoint]:
    """Fallback endpoints if OpenAPI spec not available."""
    return [
        ApiEndpoint("/health", "GET", "health_check", ["Health"], False),
        ApiEndpoint("/ready", "GET", "readiness_check", ["Health"], False),
        ApiEndpoint("/api/auth/signup", "POST", "signup", ["Auth"], False),
        ApiEndpoint("/api/auth/login", "POST", "login", ["Auth"], False),
        ApiEndpoint("/api/trading/market-indices", "GET", "market_indices", ["Trading"], False),
        ApiEndpoint("/api/market/nifty100/top-movers", "GET", "top_movers", ["Market"], False),
        ApiEndpoint("/api/v3/scanner/snapshots", "GET", "snapshots", ["Scanner"], False),
        ApiEndpoint("/api/v3/scanner/status", "GET", "scanner_status", ["Scanner"], False),
        ApiEndpoint("/api/engines/test", "GET", "engines_test", ["Engines"], False),
    ]


# =============================================================================
# Authentication Helper
# =============================================================================

def get_auth_token() -> Tuple[Optional[str], Optional[str]]:
    """Get JWT token via signup/login flow."""
    
    # Try to signup
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/signup",
            json=TEST_USER,
            timeout=10
        )
        if response.status_code in [200, 201]:
            print("  ✓ Test user created")
    except:
        pass
    
    # Login to get token
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print(f"  ✓ Auth token obtained")
                return token, None
            return None, "No token in response"
        return None, f"Login failed: {response.status_code}"
    except Exception as e:
        return None, str(e)


# =============================================================================
# Test Execution Functions
# =============================================================================

def execute_request(
    method: str,
    path: str,
    headers: Optional[Dict] = None,
    body: Optional[Dict] = None,
    expected_status: int = 200
) -> TestResult:
    """Execute a single API request and return result."""
    
    url = f"{BASE_URL}{path}"
    result = TestResult(
        endpoint=path,
        method=method,
        test_type="request",
        status=TestStatus.FAIL,
        status_code=None,
        response_time_ms=0
    )
    
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=body or {}, timeout=TIMEOUT)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=body, timeout=TIMEOUT)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=TIMEOUT)
        else:
            response = requests.request(method, url, headers=headers, json=body, timeout=TIMEOUT)
        
        elapsed = (time.time() - start_time) * 1000
        result.response_time_ms = round(elapsed, 2)
        result.status_code = response.status_code
        
        # Capture response snippet for debugging
        try:
            resp_text = response.text[:200] if response.text else ""
            result.response_snippet = resp_text
        except:
            pass
        
        # Determine status
        if response.status_code == expected_status:
            result.status = TestStatus.PASS
        elif response.status_code == 422:
            result.error_category = ErrorCategory.VALIDATION
            result.error_message = "Validation error"
        elif response.status_code == 404:
            result.error_category = ErrorCategory.ROUTING
            result.error_message = "Not found"
        elif response.status_code in [401, 403]:
            result.error_category = ErrorCategory.AUTH
            result.error_message = "Auth required"
        elif response.status_code >= 500:
            result.error_category = ErrorCategory.SERVER
            result.error_message = "Server error"
        
        # Check SLA
        if elapsed > SLA_THRESHOLD_MS:
            result.error_category = ErrorCategory.PERFORMANCE
            result.status = TestStatus.PARTIAL
        
        return result
        
    except requests.exceptions.Timeout:
        result.error_category = ErrorCategory.TIMEOUT
        result.error_message = f"Timeout after {TIMEOUT}s"
        result.response_time_ms = TIMEOUT * 1000
        return result
    except requests.exceptions.ConnectionError:
        result.error_message = "Connection refused"
        return result
    except Exception as e:
        result.error_message = str(e)[:100]
        return result


def run_happy_path_tests(
    endpoints: List[ApiEndpoint],
    auth_token: Optional[str]
) -> List[TestResult]:
    """Run happy path tests for all endpoints."""
    
    results = []
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    
    for ep in endpoints:
        test_headers = headers.copy() if ep.requires_auth else {}
        
        result = execute_request(
            method=ep.method,
            path=ep.path,
            headers=test_headers,
            expected_status=200
        )
        result.test_type = "happy_path"
        
        # Handle auth-required endpoints without token
        if ep.requires_auth and not auth_token and result.status_code in [401, 403]:
            result.status = TestStatus.SKIP
            result.error_message = "Skipped - no auth token"
        
        results.append(result)
    
    return results


def run_negative_tests(
    endpoints: List[ApiEndpoint],
    auth_token: Optional[str]
) -> List[TestResult]:
    """Run negative tests - missing fields, invalid paths, auth errors."""
    
    results = []
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    
    # Test 1: Invalid path
    result = execute_request("GET", "/api/nonexistent/endpoint", expected_status=404)
    result.test_type = "negative_404"
    if result.status_code == 404:
        result.status = TestStatus.PASS
    results.append(result)
    
    # Test 2: Missing auth on protected endpoint
    protected_eps = [ep for ep in endpoints if ep.requires_auth][:3]
    for ep in protected_eps:
        result = execute_request(ep.method, ep.path, headers={}, expected_status=401)
        result.test_type = "negative_auth"
        # Accept both 401 (correct) and 403 as valid auth responses
        if result.status_code in [401, 403]:
            result.status = TestStatus.PASS
        results.append(result)
    
    # Test 3: Invalid request body on POST endpoints
    post_eps = [ep for ep in endpoints if ep.method == "POST" and ep.request_body_schema][:3]
    for ep in post_eps:
        # Send empty body when schema requires fields
        test_headers = headers.copy() if ep.requires_auth else {}
        result = execute_request(ep.method, ep.path, headers=test_headers, body={}, expected_status=422)
        result.test_type = "negative_validation"
        if result.status_code == 422:
            result.status = TestStatus.PASS
        results.append(result)
    
    # Test 4: Invalid data types
    result = execute_request(
        "POST",
        "/api/auth/login",
        body={"email": 12345, "password": None},  # Wrong types
        expected_status=422
    )
    result.test_type = "negative_type"
    if result.status_code == 422:
        result.status = TestStatus.PASS
    results.append(result)
    
    return results


def run_error_handling_tests(auth_token: Optional[str]) -> List[TestResult]:
    """Test error responses are properly formatted (no raw stack traces)."""
    
    results = []
    
    # Force validation error and check response format
    result = execute_request(
        "POST",
        "/api/auth/signup",
        body={"email": "not-an-email"},  # Invalid email
        expected_status=422
    )
    result.test_type = "error_format"
    
    if result.response_snippet:
        # Check if response is properly structured JSON
        try:
            resp = json.loads(result.response_snippet[:500] if len(result.response_snippet) > 500 else result.response_snippet)
            if "detail" in resp or "error" in resp or "message" in resp:
                result.status = TestStatus.PASS
            # Check for raw stack traces (bad)
            if "Traceback" in result.response_snippet or "File \"" in result.response_snippet:
                result.status = TestStatus.FAIL
                result.error_message = "Raw stack trace exposed"
        except:
            pass
    
    results.append(result)
    return results


# =============================================================================
# Report Generation
# =============================================================================

def generate_summary(results: List[TestResult]) -> TestSummary:
    """Generate test summary from results."""
    
    # Count by status
    passed = sum(1 for r in results if r.status == TestStatus.PASS)
    failed = sum(1 for r in results if r.status == TestStatus.FAIL)
    partial = sum(1 for r in results if r.status == TestStatus.PARTIAL)
    
    # Response times (excluding timeouts and skipped)
    times = [r.response_time_ms for r in results if r.response_time_ms > 0 and r.response_time_ms < TIMEOUT * 1000]
    
    avg_time = statistics.mean(times) if times else 0
    p95_time = sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else (times[0] if times else 0)
    
    # Find slowest
    slowest = max(results, key=lambda r: r.response_time_ms) if results else None
    
    # Failure breakdown
    breakdown = {}
    for cat in ErrorCategory:
        count = sum(1 for r in results if r.error_category == cat)
        if count > 0:
            breakdown[cat.value] = count
    
    # High risk findings
    high_risk = []
    server_errors = [r for r in results if r.error_category == ErrorCategory.SERVER]
    if server_errors:
        high_risk.append(f"🔴 {len(server_errors)} API(s) returned 500 errors")
    
    exposed_traces = [r for r in results if r.error_message and "stack trace" in r.error_message.lower()]
    if exposed_traces:
        high_risk.append("🔴 Raw stack traces exposed in error responses")
    
    missing_auth = [r for r in results if r.test_type == "negative_auth" and r.status != TestStatus.PASS]
    if missing_auth:
        high_risk.append(f"⚠️ {len(missing_auth)} protected endpoint(s) not returning 401")
    
    # Recommendations
    recommendations = []
    if breakdown.get(ErrorCategory.VALIDATION.value, 0) > 0:
        recommendations.append("Add stricter input validation with Pydantic models")
    if breakdown.get(ErrorCategory.PERFORMANCE.value, 0) > 0:
        recommendations.append("Optimize slow endpoints - consider caching or query optimization")
    if breakdown.get(ErrorCategory.SERVER.value, 0) > 0:
        recommendations.append("Implement proper exception handling to prevent 500 errors")
    
    total = len(results)
    
    return TestSummary(
        execution_date=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        total_apis=total,
        apis_passed=passed,
        apis_failed=failed,
        apis_partial=partial,
        pass_rate=round((passed / total * 100) if total > 0 else 0, 1),
        failure_breakdown=breakdown,
        avg_response_time_ms=round(avg_time, 2),
        p95_response_time_ms=round(p95_time, 2),
        slowest_api=slowest.endpoint if slowest else "N/A",
        slowest_time_ms=round(slowest.response_time_ms, 2) if slowest else 0,
        high_risk_findings=high_risk,
        recommendations=recommendations,
        detailed_results=[asdict(r) for r in results]
    )


def generate_markdown_report(summary: TestSummary) -> str:
    """Generate formal markdown test report."""
    
    lines = [
        "# API Test Summary",
        "",
        f"**Test Execution Date:** {summary.execution_date}",
        "",
        "## Overview",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total APIs Tested | {summary.total_apis} |",
        f"| APIs Passed | {summary.apis_passed} |",
        f"| APIs Failed | {summary.apis_failed} |",
        f"| APIs Partially Passed | {summary.apis_partial} |",
        f"| **Overall Pass Rate** | **{summary.pass_rate}%** |",
        "",
        "## Failure Breakdown",
        "",
        "| Category | Count |",
        "|----------|-------|",
    ]
    
    for cat, count in summary.failure_breakdown.items():
        lines.append(f"| {cat} | {count} |")
    
    if not summary.failure_breakdown:
        lines.append("| *(No failures)* | 0 |")
    
    lines.extend([
        "",
        "## Performance Metrics",
        "",
        f"- **Average Response Time:** {summary.avg_response_time_ms} ms",
        f"- **P95 Response Time:** {summary.p95_response_time_ms} ms",
        f"- **Slowest API:** `{summary.slowest_api}` ({summary.slowest_time_ms} ms)",
        "",
    ])
    
    if summary.high_risk_findings:
        lines.extend([
            "## ⚠️ High-Risk Findings",
            "",
        ])
        for finding in summary.high_risk_findings:
            lines.append(f"- {finding}")
        lines.append("")
    
    if summary.recommendations:
        lines.extend([
            "## 💡 Actionable Recommendations",
            "",
        ])
        for rec in summary.recommendations:
            lines.append(f"- {rec}")
        lines.append("")
    
    # Detailed results table
    lines.extend([
        "## Detailed Results",
        "",
        "| Endpoint | Method | Test Type | Status | Code | Time (ms) |",
        "|----------|--------|-----------|--------|------|-----------|",
    ])
    
    for r in summary.detailed_results[:50]:  # Limit to 50 rows
        status_emoji = {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠️", "SKIP": "⏭️"}.get(r['status'], "")
        lines.append(
            f"| `{r['endpoint'][:40]}` | {r['method']} | {r['test_type']} | {status_emoji} | {r['status_code'] or 'N/A'} | {r['response_time_ms']} |"
        )
    
    if len(summary.detailed_results) > 50:
        lines.append(f"| *...and {len(summary.detailed_results) - 50} more* | | | | | |")
    
    return "\n".join(lines)


# =============================================================================
# Main Test Runner
# =============================================================================

def run_full_test_suite():
    """Run complete API testing suite."""
    
    print("=" * 70)
    print("QuantAI Comprehensive API Tester")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print("=" * 70)
    
    all_results: List[TestResult] = []
    
    # ==========================================================================
    # Phase 1: API Discovery
    # ==========================================================================
    print("\n[Phase 1: API Discovery]")
    endpoints = parse_openapi_spec()
    print(f"  Discovered {len(endpoints)} API endpoints")
    
    # Categorize
    by_tag = {}
    for ep in endpoints:
        tag = ep.tags[0] if ep.tags else "Other"
        by_tag.setdefault(tag, []).append(ep)
    
    print(f"  Categories: {len(by_tag)}")
    for tag, eps in sorted(by_tag.items(), key=lambda x: -len(x[1]))[:5]:
        print(f"    • {tag}: {len(eps)} endpoints")
    
    # ==========================================================================
    # Phase 2: Authentication
    # ==========================================================================
    print("\n[Phase 2: Authentication]")
    auth_token, auth_error = get_auth_token()
    if auth_error:
        print(f"  ⚠️ Auth failed: {auth_error}")
    
    # ==========================================================================
    # Phase 3: Happy Path Tests
    # ==========================================================================
    print("\n[Phase 3: Happy Path Tests]")
    
    # Test subset of endpoints to avoid overwhelming the server
    critical_endpoints = [
        ep for ep in endpoints
        if any(t in str(ep.tags) for t in ["Health", "Market", "Scanner", "Trading", "AI"])
    ][:30]
    
    print(f"  Testing {len(critical_endpoints)} critical endpoints...")
    happy_results = run_happy_path_tests(critical_endpoints, auth_token)
    all_results.extend(happy_results)
    
    passed = sum(1 for r in happy_results if r.status == TestStatus.PASS)
    print(f"  ✓ {passed}/{len(happy_results)} passed")
    
    # ==========================================================================
    # Phase 4: Negative Tests
    # ==========================================================================
    print("\n[Phase 4: Negative Tests]")
    negative_results = run_negative_tests(endpoints, auth_token)
    all_results.extend(negative_results)
    
    passed = sum(1 for r in negative_results if r.status == TestStatus.PASS)
    print(f"  ✓ {passed}/{len(negative_results)} passed")
    
    # ==========================================================================
    # Phase 5: Error Handling Tests
    # ==========================================================================
    print("\n[Phase 5: Error Handling Tests]")
    error_results = run_error_handling_tests(auth_token)
    all_results.extend(error_results)
    
    passed = sum(1 for r in error_results if r.status == TestStatus.PASS)
    print(f"  ✓ {passed}/{len(error_results)} passed")
    
    # ==========================================================================
    # Phase 6: Generate Reports
    # ==========================================================================
    print("\n[Phase 6: Generating Reports]")
    
    summary = generate_summary(all_results)
    
    # Save JSON report
    json_path = "api_test_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        # Convert enum values to strings for JSON
        summary_dict = asdict(summary)
        for r in summary_dict["detailed_results"]:
            if isinstance(r.get("status"), str):
                r["status"] = r["status"]
            elif hasattr(r.get("status"), "value"):
                r["status"] = r["status"].value
            if r.get("error_category"):
                if hasattr(r["error_category"], "value"):
                    r["error_category"] = r["error_category"].value
        json.dump(summary_dict, f, indent=2, default=str)
    
    # Save Markdown report
    md_path = "api_test_report.md"
    md_content = generate_markdown_report(summary)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    # Print summary
    print("\n" + "=" * 70)
    print("API TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {summary.total_apis}")
    print(f"Passed: {summary.apis_passed} | Failed: {summary.apis_failed} | Partial: {summary.apis_partial}")
    print(f"Pass Rate: {summary.pass_rate}%")
    print(f"Avg Response Time: {summary.avg_response_time_ms} ms")
    print(f"P95 Response Time: {summary.p95_response_time_ms} ms")
    
    if summary.high_risk_findings:
        print("\n⚠️ HIGH-RISK FINDINGS:")
        for finding in summary.high_risk_findings:
            print(f"  {finding}")
    
    print(f"\nReports saved:")
    print(f"  • {md_path}")
    print(f"  • {json_path}")
    print("=" * 70)
    
    return summary


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    try:
        run_full_test_suite()
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
