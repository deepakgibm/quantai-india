@echo off
echo Stopping all Python processes...
taskkill /F /IM python.exe
timeout /t 2

echo Creating demo user...
cd /d "c:\Users\Deepak Kumar\Downloads\quantai-india\backend"
python -c "import sqlite3; from passlib.context import CryptContext; pwd = CryptContext(schemes=['bcrypt'], deprecated='auto'); conn = sqlite3.connect('quantai.db'); c = conn.cursor(); c.execute('DELETE FROM users WHERE email=\"demo@example.com\"'); c.execute('INSERT INTO users (email, username, hashed_password, full_name, is_active, is_upstox_connected) VALUES (?, ?, ?, ?, ?, ?)', ('demo@example.com', 'demo', pwd.hash('demo123'), 'Demo User', 1, 0)); user_id = c.lastrowid; c.execute('INSERT OR REPLACE INTO user_settings (user_id, max_capital, max_risk_per_trade, auto_trade, notifications) VALUES (?, ?, ?, ?, ?)', (user_id, 1000000, 2.0, 0, 1)); conn.commit(); conn.close(); print('Demo user created')"
timeout /t 2

echo Starting backend...
start cmd /k "cd /d c:\Users\Deepak Kumar\Downloads\quantai-india\backend && python -m uvicorn main:app --reload --port 8000"

echo Starting frontend...
start cmd /k "cd /d c:\Users\Deepak Kumar\Downloads\quantai-india && npm run dev"

echo Starting weekly loader...
start cmd /k "cd /d c:\Users\Deepak Kumar\Downloads\quantai-india\backend && python run_weekly_load.py"

echo Starting Nifty100 loader...
start cmd /k "cd /d c:\Users\Deepak Kumar\Downloads\quantai-india && python backend/etl/nifty100_initial_loader.py"

echo.
echo All processes restarted!
echo.
echo Login with:
echo Email: demo@example.com
echo Password: demo123
