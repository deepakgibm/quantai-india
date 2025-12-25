@echo off
cd /d c:\Users\Deepak Kumar\Downloads\quantai-india\backend
set PYTHONPATH=.
set PYTHONIOENCODING=utf-8
chcp 65001 >nul
echo ============================================================
echo NIFTY 500 INTRADAY LOADER - BACKGROUND JOB
echo Started: %date% %time%
echo ============================================================
python -c "import asyncio; from services.intraday_loader import IntradayDataLoader; loader = IntradayDataLoader(); asyncio.run(loader.load_full_dataset(years=3, resume=True))"
echo ============================================================
echo Completed: %date% %time%
echo ============================================================
