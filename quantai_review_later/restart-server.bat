@echo off
REM QuantAI India - Application Restart Script
REM Stops all running processes and restarts backend + frontend

echo ================================
echo QuantAI India - Server Restart
echo ================================
echo.

echo Step 1: Stopping all Python processes...
taskkill /F /IM python.exe 2>nul
if %errorlevel% equ 0 (
    echo   - Python processes stopped
) else (
    echo   - No Python processes found
)

echo.
echo Step 2: Stopping all Node processes...
taskkill /F /IM node.exe 2>nul
if %errorlevel% equ 0 (
    echo   - Node processes stopped
) else (
    echo   - No Node processes found
)

echo.
echo Step 3: Waiting for ports to free up...
timeout /t 3 /nobreak >nul

echo.
echo Step 4: Starting Backend (FastAPI on port 8000)...
cd /d "%~dp0backend"
start "QuantAI Backend" cmd /k "python -m uvicorn main:app --reload --port 8000"

echo.
echo Step 5: Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo.
echo Step 6: Starting Frontend (React on port 3000)...
cd /d "%~dp0"
start "QuantAI Frontend" cmd /k "npm run dev"

echo.
echo ================================
echo Server Restart Complete!
echo ================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo Health:   http://localhost:8000/health
echo.
echo Login Credentials:
echo   Email:    demo@example.com
echo   Password: testpass123
echo.
echo Press any key to close this window...
pause >nul
