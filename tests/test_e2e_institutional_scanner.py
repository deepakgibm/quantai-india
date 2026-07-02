import pytest
import os
from playwright.sync_api import Page, expect

# Test credentials matching standard E2E configuration
TEST_EMAIL = "test_auth@quantai.com"
TEST_PASSWORD = "ValidPassword123!"
SCREENSHOT_DIR = "tests/screenshots"

@pytest.mark.e2e
def test_institutional_scanner_e2e_wiring(page: Page):
    """
    Test the full user flow for the Institutional Pattern Scanner:
    1. Navigate to landing page and log in.
    2. Click on 'Institutional Scanner' sidebar item.
    3. Verify rendering of Dashboard stats cards with calculated market metrics.
    4. Verify the scanner tables and pattern tabs.
    5. Navigate to a stock detail page (e.g. HINDCOPPER).
    6. Verify detailed analysis panels, support/resistance, and competitor comparison card.
    """
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    try:
        # 1. Login Flow
        print("\n[Step 1] Navigating to http://127.0.0.1:3000")
        page.goto("http://127.0.0.1:3000")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "scanner_01_landing.png"))
        
        login_btn = page.get_by_role("button", name="Log In").first
        if login_btn.is_visible():
            login_btn.click()
            page.wait_for_timeout(1000)
            
        page.locator('input[type="email"]').wait_for(state="visible", timeout=10000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "scanner_02_login_page.png"))
        
        # Try to Sign up first to ensure Firebase has the user
        print("[Step 2] Navigating to Sign up page...")
        page.get_by_role("button", name="Sign up").click()
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "scanner_03_signup_page.png"))
        
        print("[Step 3] Attempting Sign up...")
        page.fill('input[placeholder="Arjun"]', "Test")
        page.fill('input[placeholder="Kumar"]', "User")
        page.locator('input[type="email"]').fill(TEST_EMAIL)
        
        passwords = page.locator('input[type="password"]')
        passwords.nth(0).fill(TEST_PASSWORD)
        passwords.nth(1).fill(TEST_PASSWORD)
        
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "scanner_04_signup_filled.png"))
        page.get_by_role("button", name="Create Account").click()
        page.wait_for_timeout(3000)
        
        # Check if we transitioned to dashboard or got an error
        error_msg = page.locator(".text-red-600").first
        if error_msg.is_visible():
            err_text = error_msg.inner_text()
            print(f" -> Signup returned: {err_text}")
            if "already" in err_text.lower() or "in-use" in err_text.lower():
                print(" -> User already exists. Switching back to Login...")
                page.get_by_role("button", name="Login").click()
                page.wait_for_timeout(1000)
                
                # Perform standard login
                page.locator('input[type="email"]').fill(TEST_EMAIL)
                page.locator('input[type="password"]').fill(TEST_PASSWORD)
                page.click('button[type="submit"]')
                page.wait_for_timeout(3000)
        
        # Wait for dashboard transition
        print("[Step 4] Waiting for main dashboard redirect...")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "scanner_05_after_auth_attempt.png"))
        
        dashboard_header = page.get_by_text("Institutional Trading Dashboard")
        expect(dashboard_header).to_be_visible(timeout=35000)
        print(" -> Dashboard loaded successfully.")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "scanner_06_dashboard.png"))

        # 2. Sidebar Navigation to Institutional Scanner
        print("[Step 5] Clicking 'Institutional Scanner' in sidebar...")
        sidebar_btn = page.get_by_role("button", name="Institutional Scanner VCP")
        expect(sidebar_btn).to_be_visible(timeout=10000)
        sidebar_btn.click()
        
        # 3. Verify Page Header & Dashboard Cards
        print("[Step 6] Verifying scanner page layout and opportunity widgets...")
        page.wait_for_timeout(2000)
        
        # Check main title
        scanner_title = page.get_by_text("Institutional VCP & Breakout Intelligence").first
        expect(scanner_title).to_be_visible(timeout=10000)
        print(" -> Page title 'Institutional VCP & Breakout Intelligence' is visible")
        
        # Check stats cards
        expect(page.get_by_text("Total Stocks Scanned")).to_be_visible(timeout=10000)
        expect(page.get_by_text("VCP Candidates")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Breakout Ready Stocks")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Fresh Breakouts")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Near 52W High Stocks")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Relative Strength Leaders")).to_be_visible(timeout=10000)
        print(" -> Opportunity Dashboard widgets successfully loaded.")
        
        # 4. Verify Scanner Tables and Tabs
        print("[Step 7] Checking pattern scanner tabs...")
        expect(page.get_by_role("button", name="VCP Scanner")).to_be_visible(timeout=10000)
        expect(page.get_by_role("button", name="Minervini Trend")).to_be_visible(timeout=10000)
        expect(page.get_by_role("button", name="RS Rankings")).to_be_visible(timeout=10000)
        expect(page.get_by_role("button", name="Breakouts")).to_be_visible(timeout=10000)
        print(" -> All pattern scanner tabs are present.")
        
        # Check that results exist in the table (e.g. check for HINDCOPPER)
        print("[Step 8] Checking for scanned symbols in the grid...")
        hindcopper_cell = page.get_by_text("HINDCOPPER").first
        expect(hindcopper_cell).to_be_visible(timeout=15000)
        print(" -> Scanned symbol 'HINDCOPPER' is visible in the grid.")
        
        # 5. Navigate to Stock Detail Page
        print("[Step 9] Clicking on 'HINDCOPPER' to open institutional details...")
        hindcopper_cell.click()
        
        # Verify stock detail page loaded
        print("[Step 10] Verifying detail page loading for HINDCOPPER...")
        expect(page.get_by_text("Institutional Detail")).to_be_visible(timeout=15000)
        expect(page.get_by_role("heading", name="HINDCOPPER")).to_be_visible(timeout=10000)
        print(" -> Stock detail page loaded for HINDCOPPER.")
        
        # 6. Verify detail sections
        print("[Step 11] Checking pattern tabs on detail page...")
        expect(page.get_by_role("button", name="Technical Patterns & Geometry")).to_be_visible(timeout=10000)
        expect(page.get_by_role("button", name="Technical Indicators & MA")).to_be_visible(timeout=10000)
        expect(page.get_by_role("button", name="Upstox News & Peer Comparison")).to_be_visible(timeout=10000)
        print(" -> Detail tabs are working.")
        
        # Click Peer Comparison tab and verify competitor listings
        print("[Step 12] Inspecting Competitor Comparison card...")
        page.get_by_role("button", name="Upstox News & Peer Comparison").click()
        page.wait_for_timeout(1000)
        
        competitor_visible = page.get_by_text("Hindalco Industries", exact=False).is_visible()
        empty_state_visible = page.get_by_text("No competitors fetched from Upstox API.").is_visible()
        
        assert competitor_visible or empty_state_visible, "Neither competitor list nor empty-state fallback was rendered."
        print(f" -> Competitor comparison verified. Data rendered: {competitor_visible}, Empty state: {empty_state_visible}")
        
        print("\nSuccess: End-to-End wiring and API-to-UI communication verified successfully!")
        
    except Exception as e:
        print(f"[E2E Scanner] ERROR encountered: {e}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "scanner_error.png"))
        raise

