@echo off
echo ================================================
echo  QuantAI India - Starting Full Stack Application
echo ================================================
echo.

echo [1/2] Starting FastAPI Backend...
echo.
start "QuantAI Backend" cmd /k "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Starting React Frontend...
echo.
start "QuantAI Frontend" cmd /k "npm run dev"

echo.
echo ================================================
echo   Application Started Successfully!
echo ================================================
echo.
echo  Frontend: http://localhost:5173
echo  Backend:  http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo.
echo  Press any key to exit this window...
pause >nul
