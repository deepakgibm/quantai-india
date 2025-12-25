@echo off
echo ========================================
echo EMERGENCY LOGIN FIX
echo ========================================
echo.
echo This will:
echo 1. Stop the backend server
echo 2. Create demo user
echo 3. Restart backend
echo.
pause

echo Stopping backend...
FOR /F "tokens=5" %%a IN ('netstat -aon ^| find ":8000" ^| find "LISTENING"') DO taskkill /F /PID %%a
timeout /t 3

echo Creating demo user...
cd /d "c:\Users\Deepak Kumar\Downloads\quantai-india\backend"
python -c "import sqlite3; import bcrypt; conn = sqlite3.connect('quantai.db'); c = conn.cursor(); c.execute('DELETE FROM user_settings WHERE user_id IN (SELECT id FROM users WHERE email=\"demo@example.com\")'); c.execute('DELETE FROM users WHERE email=\"demo@example.com\"'); hashed = bcrypt.hashpw(b'demo123', bcrypt.gensalt()).decode('utf-8'); c.execute('INSERT INTO users (email, username, hashed_password, full_name, is_active, is_upstox_connected, created_at) VALUES (?, ?, ?, ?, ?, ?, datetime(\"now\"))', ('demo@example.com', 'demo', hashed, 'Demo User', 1, 0)); user_id = c.lastrowid; c.execute('INSERT INTO user_settings (user_id, max_capital, max_risk_per_trade, auto_trade, notifications) VALUES (?, ?, ?, ?, ?)', (user_id, 1000000, 2.0, 0, 1)); conn.commit(); conn.close(); print('User created!')"
timeout /t 2

echo Starting backend...
start "Backend Server" cmd /k "cd /d c:\Users\Deepak Kumar\Downloads\quantai-india\backend && python -m uvicorn main:app --reload --port 8000"

timeout /t 5

echo.
echo ========================================
echo DONE! Now try logging in with:
echo Email: demo@example.com
echo Password: demo123
echo ========================================
pause
