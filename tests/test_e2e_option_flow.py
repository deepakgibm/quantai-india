import pytest
from playwright.sync_api import Page, expect
import os

TEST_EMAIL = "test_auth@quantai.com"
TEST_PASSWORD = "ValidPassword123!"
SCREENSHOT_DIR = r"C:\Users\Deepak Kumar\.gemini\antigravity\brain\0976eb79-b652-4b91-9d17-f5f011016220\scratch"

@pytest.mark.e2e
def test_option_flow_e2e(page: Page):
    """
    End-to-End test for Option Flow Terminal:
    Handles Firebase signup if user doesn't exist, then verifies Option Flow Terminal.
    """
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    
    try:
        # 1. Navigate to landing and go to Login
        print("\n[E2E Option Flow] Navigating to landing page...")
        page.goto("http://localhost:3000")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_landing.png"))
        
        login_btn = page.get_by_role("button", name="Log In").first
        if login_btn.is_visible():
            login_btn.click()
            page.wait_for_timeout(1000)
            
        page.locator('input[type="email"]').wait_for(state="visible", timeout=10000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_login_page.png"))
        
        # Try to Sign up first to ensure Firebase has the user
        print("[E2E Option Flow] Navigating to Sign up page...")
        page.get_by_role("button", name="Sign up").click()
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_signup_page.png"))
        
        print("[E2E Option Flow] Attempting Sign up...")
        page.fill('input[placeholder="Arjun"]', "Test")
        page.fill('input[placeholder="Kumar"]', "User")
        page.locator('input[type="email"]').fill(TEST_EMAIL)
        
        passwords = page.locator('input[type="password"]')
        passwords.nth(0).fill(TEST_PASSWORD)
        passwords.nth(1).fill(TEST_PASSWORD)
        
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_signup_filled.png"))
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
        
        # 2. Wait for dashboard transition
        print("[E2E Option Flow] Waiting for dashboard loading...")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_after_auth_attempt.png"))
        
        dashboard_header = page.get_by_text("Institutional Trading Dashboard")
        expect(dashboard_header).to_be_visible(timeout=15000)
        print(" -> Dashboard loaded successfully.")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_dashboard.png"))
        
        # 3. Click 'Option Flow' sidebar link
        print("[E2E Option Flow] Clicking 'Option Flow' sidebar link...")
        page.get_by_role("button", name="Option Flow").click()
        page.wait_for_timeout(2000)
        
        # 4. Verify Option Flow Page loads
        print("[E2E Option Flow] Verifying Option Flow page loads...")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_option_flow_page.png"))
        
        expect(page.get_by_role("heading", name="Option Flow Terminal").or_(page.get_by_text("Option Flow", exact=True))).to_be_visible(timeout=10000)
        print(" -> Option Flow page is visible.")
        
        # 5. Check if the stale cache banner is displayed
        print("[E2E Option Flow] Verifying the stale cache warning banner...")
        stale_banner = page.get_by_text("Showing cached data from a previous session.")
        expect(stale_banner).to_be_visible(timeout=10000)
        print(" -> Stale cache warning banner is successfully displayed!")
        
        # 6. Verify Option metrics
        print("[E2E Option Flow] Verifying metric cards...")
        expect(page.get_by_text("Call Turnover")).to_be_visible(timeout=5000)
        expect(page.get_by_text("Put Turnover")).to_be_visible(timeout=5000)
        expect(page.get_by_text("Net Premium Flow")).to_be_visible(timeout=5000)
        expect(page.get_by_text("Put-Call Ratio (PCR)")).to_be_visible(timeout=5000)
        expect(page.get_by_text("Option Sentiment")).to_be_visible(timeout=5000)
        print(" -> All standard option flow metrics cards are visible!")
        
        print("[E2E Option Flow] Test Passed successfully!")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_test_passed.png"))
        
    except Exception as e:
        print(f"[E2E Option Flow] ERROR encountered: {e}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "error_screenshot.png"))
        raise
