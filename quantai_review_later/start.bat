@echo off
echo Installing backend dependencies...
pip install -r requirements.txt

echo.
echo Starting FastAPI backend server...
python main.py
