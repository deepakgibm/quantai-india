import pytest
import os
from datetime import datetime, timedelta
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

    # Inoculate database VCP data for HINDCOPPER
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Ensure HINDCOPPER exists in instrument_master
            cursor.execute("SELECT instrument_id FROM instrument_master WHERE symbol = 'HINDCOPPER'")
            inst = cursor.fetchone()
            if not inst:
                cursor.execute("""
                    INSERT INTO instrument_master (symbol, instrument_type, exchange, lot_size, tick_size, name)
                    VALUES ('HINDCOPPER', 'EQUITY', 'NSE', 1, 0.05, 'Hindustan Copper Limited')
                    RETURNING instrument_id
                """)
                inst_id = cursor.fetchone()[0]
            else:
                inst_id = inst[0]
                
            # Ensure stock candles exist for HINDCOPPER
            cursor.execute("SELECT COUNT(*) FROM stock_candle WHERE instrument_id = %s", (inst_id,))
            if cursor.fetchone()[0] == 0:
                for i in range(30):
                    ts = datetime.utcnow() - timedelta(days=i)
                    cursor.execute("""
                        INSERT INTO stock_candle (instrument_id, timeframe, candle_ts, open, high, low, close, volume)
                        VALUES (%s, 1440, %s, 150.0, 155.0, 148.0, 152.0, 100000)
                    """, (inst_id, ts))

            # Ensure VCP Score exists
            cursor.execute("SELECT COUNT(*) FROM vcp_scores WHERE symbol = 'HINDCOPPER'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO vcp_scores (symbol, current_price, distance_from_52w_high, vcp_score, num_contractions, latest_contraction_pct, volume_dry_up_pct, atr_contraction_pct, breakout_pivot, breakout_ready, category)
                    VALUES ('HINDCOPPER', 152.0, 5.0, 85.0, 3, 2.5, 45.0, 12.0, 155.0, true, 'Elite')
                """)
                
            # Ensure Trend Template Score exists
            cursor.execute("SELECT COUNT(*) FROM trend_template_scores WHERE symbol = 'HINDCOPPER'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO trend_template_scores (symbol, trend_template_score, price_above_sma50, price_above_sma150, price_above_sma200, sma50, sma150, sma200, distance_to_52w_high)
                    VALUES ('HINDCOPPER', 7.0, true, true, true, 145.0, 140.0, 135.0, 5.0)
                """)
                
            # Ensure RS Ranking exists
            cursor.execute("SELECT COUNT(*) FROM relative_strength_rankings WHERE symbol = 'HINDCOPPER'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO relative_strength_rankings (rank, symbol, rs_score, sector, market_cap)
                    VALUES (12, 'HINDCOPPER', 89.5, 'Metals', 15000000000.0)
                """)
                
            # Ensure Darvas Box exists
            cursor.execute("SELECT COUNT(*) FROM darvas_boxes WHERE symbol = 'HINDCOPPER'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO darvas_boxes (symbol, box_top, box_bottom, days_inside_box)
                    VALUES ('HINDCOPPER', 160.0, 145.0, 15)
                """)
                
            conn.commit()
            conn.commit()
            cursor.close()
            conn.close()
            print("DB: Inoculated VCP scanner mock data successfully.")
            
            # Clear Redis cache synchronously
            try:
                import redis
                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", 6379))
                redis_db = int(os.getenv("REDIS_DB", 0))
                r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
                r.delete("qai:scanner:institutional:results")
                r.delete("qai:scanner:institutional:dashboard")
                print("DB: Synchronously cleared Redis VCP scanner cache.")
            except Exception as cache_err:
                print("Cache clear error:", cache_err)
        except Exception as e:
            print("DB Inoculation error:", e)

    try:
        # Enable console log and pageerror listening
        page.on("pageerror", lambda err: print(f"[Browser JS Error] {getattr(err, 'message', err)}\nSTACK: {getattr(err, 'stack', 'No stack')}"))
        page.on("console", lambda msg: print(f"[Browser Console] {msg.text}"))

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

